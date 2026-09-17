// The payload builder, the entry lookup, and the shared refusal assertion.

#include "snapshot_v9_fixture.hpp"

#include "protocol/v1/crypto.hpp"

#include <algorithm>
#include <span>
#include <variant>

namespace snapshot_v9_tests {
namespace {

constexpr std::string_view kDigestDomain = "protocol-stack:storage:snapshot-v9";

void append(v9::Bytes& target, std::span<const std::uint8_t> bytes) {
  target.insert(target.end(), bytes.begin(), bytes.end());
}

void append_u16(v9::Bytes& target, std::uint16_t value) {
  target.push_back(static_cast<std::uint8_t>(value >> 8U));
  target.push_back(static_cast<std::uint8_t>(value));
}

void append_u32(v9::Bytes& target, std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    target.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

void append_u64(v9::Bytes& target, std::uint64_t value) {
  for (int shift = 56; shift >= 0; shift -= 8) {
    target.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

}  // namespace

v9::Bytes Payload::encode() const {
  v9::Bytes raw;
  append(raw, magic);
  append_u16(raw, version);
  append(raw, chain_id);
  append_u64(raw, height);
  append_u64(raw, timestamp);
  append_u64(raw, supply_limit);
  append_u64(raw, total_supply);
  append_u64(raw, fee_pool);
  append_u64(raw, fixed_fee);
  append(raw, verifier_key);
  append(raw, dispute_authority_key);
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

Payload payload_of(const v9::Ledger& ledger) {
  Payload payload;
  payload.chain_id = ledger.chain_id;
  payload.height = ledger.height;
  payload.timestamp = ledger.timestamp;
  payload.supply_limit = ledger.supply_limit;
  payload.total_supply = ledger.total_supply;
  payload.fee_pool = ledger.fee_pool;
  payload.fixed_fee = ledger.fixed_fee;
  payload.verifier_key = ledger.verifier_key;
  payload.dispute_authority_key = ledger.dispute_authority_key;
  payload.accounts = v9::account_entries(ledger);
  payload.economy = v9::economy_entries(ledger);
  std::sort(payload.economy.begin(), payload.economy.end(),
            [](const v9::EconomyEntry& left, const v9::EconomyEntry& right) {
              return left.key < right.key;
            });
  const auto root = v9::ledger_state_root(ledger);
  pv::require(root.has_value(), "the fixture ledger must commit a state root");
  payload.state_root = *root;
  return payload;
}

std::vector<v9::EconomyEntry>::iterator find_entry(Payload& payload,
                                                   v9::Entry kind) {
  const auto discriminator = static_cast<std::uint8_t>(kind);
  return std::find_if(payload.economy.begin(), payload.economy.end(),
                      [discriminator](const v9::EconomyEntry& entry) {
                        return !entry.key.empty() &&
                               entry.key.front() == discriminator;
                      });
}

v9::EconomyEntry& entry_of(Payload& payload, v9::Entry kind) {
  const auto found = find_entry(payload, kind);
  pv::require(found != payload.economy.end(),
              "the fixture carries an entry of kind " +
                  std::to_string(static_cast<unsigned>(kind)));
  return *found;
}

v9::EconomyEntry& last_of(Payload& payload, v9::Entry kind) {
  const auto discriminator = static_cast<std::uint8_t>(kind);
  v9::EconomyEntry* found = nullptr;
  for (auto& entry : payload.economy) {
    if (!entry.key.empty() && entry.key.front() == discriminator) found = &entry;
  }
  pv::require(found != nullptr, "the fixture carries an entry of kind " +
                                    std::to_string(static_cast<unsigned>(kind)));
  return *found;
}

void erase_kind(Payload& payload, v9::Entry kind) {
  const auto discriminator = static_cast<std::uint8_t>(kind);
  const auto removed = std::remove_if(
      payload.economy.begin(), payload.economy.end(),
      [discriminator](const v9::EconomyEntry& entry) {
        return !entry.key.empty() && entry.key.front() == discriminator;
      });
  pv::require(removed != payload.economy.end(),
              "the fixture carried an entry of kind " +
                  std::to_string(static_cast<unsigned>(kind)) + " to remove");
  payload.economy.erase(removed, payload.economy.end());
}

void reseal(Payload& payload) {
  v9::StateSummary summary;
  summary.chain_id = payload.chain_id;
  summary.height = payload.height;
  summary.timestamp = payload.timestamp;
  summary.supply_limit = payload.supply_limit;
  summary.total_supply = payload.total_supply;
  summary.fee_pool_balance = payload.fee_pool;
  const auto root = v9::state_root(summary, payload.accounts, payload.economy);
  pv::require(root.has_value(), "a resealed payload must commit a root");
  payload.state_root = *root;
}

void poke_u64(v9::Bytes& value, std::size_t offset, std::uint64_t number) {
  pv::require(offset + 8 <= value.size(), "the field is inside the value");
  for (std::size_t index = 0; index < 8; ++index) {
    value[offset + index] =
        static_cast<std::uint8_t>(number >> (56 - 8 * index));
  }
}

void poke_u32(v9::Bytes& value, std::size_t offset, std::uint32_t number) {
  pv::require(offset + 4 <= value.size(), "the field is inside the value");
  for (std::size_t index = 0; index < 4; ++index) {
    value[offset + index] =
        static_cast<std::uint8_t>(number >> (24 - 8 * index));
  }
}

std::string error_name(ps::SnapshotV9Error error) {
  switch (error) {
    case ps::SnapshotV9Error::malformed:
      return "malformed";
    case ps::SnapshotV9Error::unsupported_version:
      return "unsupported_version";
    case ps::SnapshotV9Error::size_overflow:
      return "size_overflow";
    case ps::SnapshotV9Error::digest_mismatch:
      return "digest_mismatch";
    case ps::SnapshotV9Error::immutable_parameters_mismatch:
      return "immutable_parameters_mismatch";
    case ps::SnapshotV9Error::invalid_state:
      return "invalid_state";
    case ps::SnapshotV9Error::state_root_mismatch:
      return "state_root_mismatch";
    case ps::SnapshotV9Error::payload_root_mismatch:
      return "payload_root_mismatch";
    case ps::SnapshotV9Error::not_conserved:
      return "not_conserved";
  }
  return "unknown";
}

void require_refusal(const Payload& payload,
                     const ps::SnapshotParametersV9& parameters,
                     ps::SnapshotV9Error expected, const std::string& subject) {
  const auto raw = payload.encode();
  const auto decoded = ps::decode_snapshot_v9(raw, parameters);
  pv::require(std::holds_alternative<ps::SnapshotV9Error>(decoded),
              subject + ": a restore accepted it");
  const auto actual = std::get<ps::SnapshotV9Error>(decoded);
  pv::require(actual == expected, subject + ": expected " + error_name(expected) +
                                      ", got " + error_name(actual));
}

}  // namespace snapshot_v9_tests
