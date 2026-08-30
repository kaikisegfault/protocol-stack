// The payload builder, the entry lookup, and the shared refusal assertion.

#include "snapshot_v7_fixture.hpp"

#include "protocol/v1/crypto.hpp"

#include <algorithm>
#include <span>
#include <variant>

namespace snapshot_v7_tests {
namespace {

constexpr std::string_view kDigestDomain = "protocol-stack:storage:snapshot-v7";

void append(v7::Bytes& target, std::span<const std::uint8_t> bytes) {
  target.insert(target.end(), bytes.begin(), bytes.end());
}

void append_u16(v7::Bytes& target, std::uint16_t value) {
  target.push_back(static_cast<std::uint8_t>(value >> 8U));
  target.push_back(static_cast<std::uint8_t>(value));
}

void append_u32(v7::Bytes& target, std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    target.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

void append_u64(v7::Bytes& target, std::uint64_t value) {
  for (int shift = 56; shift >= 0; shift -= 8) {
    target.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

}  // namespace

v7::Bytes Payload::encode() const {
  v7::Bytes raw;
  append(raw, magic);
  append_u16(raw, version);
  append(raw, chain_id);
  append_u64(raw, height);
  append_u64(raw, supply_limit);
  append_u64(raw, total_supply);
  append_u64(raw, fee_pool);
  append_u64(raw, fixed_fee);
  append(raw, verifier_key);
  append_u64(raw, declared_account_count.value_or(
                      static_cast<std::uint64_t>(accounts.size())));
  append_u64(raw, declared_economy_count.value_or(
                      static_cast<std::uint64_t>(economy.size())));
  for (const auto& account : accounts) {
    append(raw, account.account_id);
    append_u64(raw, account.balance);
    append_u64(raw, account.nonce);
  }
  for (const auto& entry : economy) {
    append_u32(raw, static_cast<std::uint32_t>(entry.key.size()));
    append(raw, entry.key);
    append_u32(raw, static_cast<std::uint32_t>(entry.value.size()));
    append(raw, entry.value);
  }
  append(raw, state_root);
  append(raw, protocol::v1::hash(kDigestDomain, raw));
  return raw;
}

Payload payload_of(const v7::Ledger& ledger) {
  Payload payload;
  payload.chain_id = ledger.chain_id;
  payload.height = ledger.height;
  payload.supply_limit = ledger.supply_limit;
  payload.total_supply = ledger.total_supply;
  payload.fee_pool = ledger.fee_pool;
  payload.fixed_fee = ledger.fixed_fee;
  payload.verifier_key = ledger.verifier_key;
  payload.accounts = v7::account_entries(ledger);
  payload.economy = v7::economy_entries(ledger);
  std::sort(payload.economy.begin(), payload.economy.end(),
            [](const v7::EconomyEntry& left, const v7::EconomyEntry& right) {
              return left.key < right.key;
            });
  const auto root = v7::ledger_state_root(ledger);
  pv::require(root.has_value(), "the fixture ledger must commit a state root");
  payload.state_root = *root;
  return payload;
}

std::vector<v7::EconomyEntry>::iterator find_entry(Payload& payload,
                                                   v7::Entry kind) {
  const auto discriminator = static_cast<std::uint8_t>(kind);
  return std::find_if(payload.economy.begin(), payload.economy.end(),
                      [discriminator](const v7::EconomyEntry& entry) {
                        return !entry.key.empty() &&
                               entry.key.front() == discriminator;
                      });
}

v7::EconomyEntry& entry_of(Payload& payload, v7::Entry kind) {
  const auto found = find_entry(payload, kind);
  pv::require(found != payload.economy.end(),
              "the fixture carries an entry of kind " +
                  std::to_string(static_cast<unsigned>(kind)));
  return *found;
}

void reseal(Payload& payload) {
  v7::StateSummary summary;
  summary.chain_id = payload.chain_id;
  summary.height = payload.height;
  summary.supply_limit = payload.supply_limit;
  summary.total_supply = payload.total_supply;
  summary.fee_pool_balance = payload.fee_pool;
  const auto root = v7::state_root(summary, payload.accounts, payload.economy);
  pv::require(root.has_value(), "a resealed payload must commit a root");
  payload.state_root = *root;
}

void poke_u64(v7::Bytes& value, std::size_t offset, std::uint64_t number) {
  pv::require(offset + 8 <= value.size(), "the field is inside the value");
  for (std::size_t index = 0; index < 8; ++index) {
    value[offset + index] =
        static_cast<std::uint8_t>(number >> (56 - 8 * index));
  }
}

void poke_u32(v7::Bytes& value, std::size_t offset, std::uint32_t number) {
  pv::require(offset + 4 <= value.size(), "the field is inside the value");
  for (std::size_t index = 0; index < 4; ++index) {
    value[offset + index] =
        static_cast<std::uint8_t>(number >> (24 - 8 * index));
  }
}

std::string error_name(ps::SnapshotV7Error error) {
  switch (error) {
    case ps::SnapshotV7Error::malformed:
      return "malformed";
    case ps::SnapshotV7Error::unsupported_version:
      return "unsupported_version";
    case ps::SnapshotV7Error::size_overflow:
      return "size_overflow";
    case ps::SnapshotV7Error::digest_mismatch:
      return "digest_mismatch";
    case ps::SnapshotV7Error::immutable_parameters_mismatch:
      return "immutable_parameters_mismatch";
    case ps::SnapshotV7Error::invalid_state:
      return "invalid_state";
    case ps::SnapshotV7Error::state_root_mismatch:
      return "state_root_mismatch";
    case ps::SnapshotV7Error::payload_root_mismatch:
      return "payload_root_mismatch";
    case ps::SnapshotV7Error::not_conserved:
      return "not_conserved";
  }
  return "unknown";
}

void require_refusal(const Payload& payload,
                     const ps::SnapshotParametersV7& parameters,
                     ps::SnapshotV7Error expected, const std::string& subject) {
  const auto raw = payload.encode();
  const auto decoded = ps::decode_snapshot_v7(raw, parameters);
  pv::require(std::holds_alternative<ps::SnapshotV7Error>(decoded),
              subject + ": a restore accepted it");
  const auto actual = std::get<ps::SnapshotV7Error>(decoded);
  pv::require(actual == expected, subject + ": expected " + error_name(expected) +
                                      ", got " + error_name(actual));
}

}  // namespace snapshot_v7_tests
