#include "protocol/storage/snapshot_v1.hpp"

#include "protocol/v1/crypto.hpp"

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <map>
#include <optional>
#include <span>
#include <utility>
#include <variant>

namespace protocol::storage {
namespace {

namespace pv1 = protocol::v1;

constexpr std::array<std::uint8_t, 4> kMagic{'P', 'S', 'S', 'N'};
constexpr std::uint16_t kVersion = 1;
constexpr std::size_t kPrefixSize = 86;
constexpr std::size_t kAccountSize = 48;
constexpr std::size_t kRootSize = 32;
constexpr std::size_t kDigestSize = 32;
constexpr std::size_t kFixedSize =
    kPrefixSize + kRootSize + kDigestSize;
constexpr char kDigestDomain[] =
    "protocol-stack:storage:snapshot-v1";

void append(
    pv1::Bytes& target,
    std::span<const std::uint8_t> bytes) {
  target.insert(target.end(), bytes.begin(), bytes.end());
}

void append_u16(pv1::Bytes& target, std::uint16_t value) {
  target.push_back(static_cast<std::uint8_t>(value >> 8U));
  target.push_back(static_cast<std::uint8_t>(value));
}

void append_u64(pv1::Bytes& target, std::uint64_t value) {
  for (int shift = 56; shift >= 0; shift -= 8) {
    target.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

std::uint16_t read_u16(
    std::span<const std::uint8_t> input,
    std::size_t offset) {
  return static_cast<std::uint16_t>(
      (static_cast<std::uint16_t>(input[offset]) << 8U) |
      input[offset + 1]);
}

std::uint64_t read_u64(
    std::span<const std::uint8_t> input,
    std::size_t offset) {
  std::uint64_t value = 0;
  for (std::size_t index = 0; index < 8; ++index) {
    value = (value << 8U) | input[offset + index];
  }
  return value;
}

template <typename Tagged>
Tagged read_tagged(
    std::span<const std::uint8_t> input,
    std::size_t offset) {
  pv1::Hash value{};
  std::copy_n(input.begin() + static_cast<std::ptrdiff_t>(offset),
              value.size(), value.begin());
  return Tagged{value};
}

template <typename Tagged>
std::span<const std::uint8_t> tagged_bytes(
    const Tagged& value) noexcept {
  return {value.data(), value.size()};
}

SnapshotV1Error restore_error(pv1::LedgerRestoreError error) {
  switch (error) {
    case pv1::LedgerRestoreError::invalid_state:
      return SnapshotV1Error::invalid_state;
    case pv1::LedgerRestoreError::immutable_parameters_mismatch:
      return SnapshotV1Error::immutable_parameters_mismatch;
    case pv1::LedgerRestoreError::state_root_mismatch:
      return SnapshotV1Error::state_root_mismatch;
  }
  return SnapshotV1Error::invalid_state;
}

}  // namespace

SnapshotV1EncodeResult encode_snapshot_v1(
    const pv1::Ledger& ledger) {
  const auto root_result = ledger.current_state_root();
  if (!std::holds_alternative<pv1::StateRoot>(root_result)) {
    return SnapshotV1Error::invalid_state;
  }
  const auto& state = ledger.state();
  const auto account_count = state.accounts.size();
  pv1::Bytes payload;
  if (payload.max_size() < kFixedSize ||
      account_count >
      (payload.max_size() - kFixedSize) / kAccountSize) {
    return SnapshotV1Error::size_overflow;
  }
  if constexpr (sizeof(std::size_t) > sizeof(std::uint64_t)) {
    if (account_count > std::numeric_limits<std::uint64_t>::max()) {
      return SnapshotV1Error::size_overflow;
    }
  }

  payload.reserve(kFixedSize + account_count * kAccountSize);
  append(payload, kMagic);
  append_u16(payload, kVersion);
  append(payload, tagged_bytes(state.parameters.chain_id));
  append_u64(payload, state.height);
  append_u64(payload, state.parameters.supply_limit);
  append_u64(payload, state.parameters.total_supply);
  append_u64(payload, state.parameters.fixed_fee);
  append_u64(payload, state.fee_pool);
  append_u64(payload, static_cast<std::uint64_t>(account_count));
  for (const auto& [account_id, account] : state.accounts) {
    append(payload, tagged_bytes(account_id));
    append_u64(payload, account.balance);
    append_u64(payload, account.nonce);
  }

  const auto state_root = std::get<pv1::StateRoot>(root_result);
  append(payload, tagged_bytes(state_root));
  const auto digest = pv1::hash(kDigestDomain, payload);
  append(payload, digest);
  return EncodedSnapshotV1{
      std::move(payload),
      state_root,
      digest,
  };
}

SnapshotV1DecodeResult decode_snapshot_v1(
    std::span<const std::uint8_t> payload,
    const pv1::Parameters& expected_parameters) {
  if (payload.size() < kFixedSize ||
      !std::equal(kMagic.begin(), kMagic.end(), payload.begin())) {
    return SnapshotV1Error::malformed;
  }
  if (read_u16(payload, 4) != kVersion) {
    return SnapshotV1Error::unsupported_version;
  }

  const auto encoded_count = read_u64(payload, 78);
  if (encoded_count >
      (std::numeric_limits<std::size_t>::max() - kFixedSize) /
          kAccountSize) {
    return SnapshotV1Error::size_overflow;
  }
  const auto account_count = static_cast<std::size_t>(encoded_count);
  const auto expected_size =
      kFixedSize + account_count * kAccountSize;
  if (payload.size() != expected_size) {
    return SnapshotV1Error::malformed;
  }

  pv1::Hash encoded_digest{};
  std::copy_n(
      payload.end() - static_cast<std::ptrdiff_t>(kDigestSize),
      encoded_digest.size(), encoded_digest.begin());
  const auto computed_digest = pv1::hash(
      kDigestDomain, payload.first(payload.size() - kDigestSize));
  if (computed_digest != encoded_digest) {
    return SnapshotV1Error::digest_mismatch;
  }

  const pv1::Parameters parameters{
      read_tagged<pv1::ChainId>(payload, 6),
      read_u64(payload, 46),
      read_u64(payload, 54),
      read_u64(payload, 62),
  };
  if (parameters != expected_parameters) {
    return SnapshotV1Error::immutable_parameters_mismatch;
  }

  std::map<pv1::AccountId, pv1::Account> accounts;
  std::optional<pv1::AccountId> previous_account_id;
  std::size_t offset = kPrefixSize;
  for (std::size_t index = 0; index < account_count; ++index) {
    const auto account_id =
        read_tagged<pv1::AccountId>(payload, offset);
    const auto balance = read_u64(payload, offset + 32);
    const auto nonce = read_u64(payload, offset + 40);
    if ((previous_account_id &&
         !(*previous_account_id < account_id)) ||
        !accounts
             .emplace(account_id, pv1::Account{balance, nonce})
             .second) {
      return SnapshotV1Error::invalid_state;
    }
    previous_account_id = account_id;
    offset += kAccountSize;
  }

  const auto state_root =
      read_tagged<pv1::StateRoot>(payload, offset);
  pv1::State state{
      parameters,
      read_u64(payload, 38),
      read_u64(payload, 70),
      std::move(accounts),
  };
  auto restored = pv1::restore_ledger(
      std::move(state), expected_parameters, state_root);
  if (std::holds_alternative<pv1::LedgerRestoreError>(
          restored.result)) {
    return restore_error(
        std::get<pv1::LedgerRestoreError>(restored.result));
  }
  return DecodedSnapshotV1{
      std::get<pv1::Ledger>(std::move(restored.result)),
      state_root,
      encoded_digest,
  };
}

}  // namespace protocol::storage
