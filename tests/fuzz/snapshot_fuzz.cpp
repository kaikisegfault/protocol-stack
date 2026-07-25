#include "protocol/storage/snapshot_v1.hpp"
#include "protocol/v1/ledger.hpp"

#include <cstddef>
#include <cstdint>
#include <span>
#include <utility>
#include <variant>

namespace ps = protocol::storage;
namespace pv1 = protocol::v1;

namespace {

void append_u16(pv1::Bytes& bytes, std::uint16_t value) {
  bytes.push_back(static_cast<std::uint8_t>(value >> 8U));
  bytes.push_back(static_cast<std::uint8_t>(value));
}

void append_u32(pv1::Bytes& bytes, std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    bytes.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

void append_u64(pv1::Bytes& bytes, std::uint64_t value) {
  for (int shift = 56; shift >= 0; shift -= 8) {
    bytes.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

pv1::Ledger fixture_ledger() {
  pv1::Bytes genesis{'P', 'S', 'G', 'N'};
  append_u16(genesis, 1);
  append_u32(genesis, 1);
  append_u64(genesis, 100);
  append_u64(genesis, 100);
  append_u64(genesis, 1);
  append_u64(genesis, 0);
  append_u32(genesis, 1);
  genesis.insert(genesis.end(), 31, 0);
  genesis.push_back(1);
  append_u64(genesis, 100);
  append_u64(genesis, 0);

  auto loaded = pv1::load_genesis(genesis);
  if (!std::holds_alternative<pv1::Ledger>(loaded.result)) {
    __builtin_trap();
  }
  return std::get<pv1::Ledger>(std::move(loaded.result));
}

const pv1::Ledger& valid_ledger() {
  static const auto ledger = fixture_ledger();
  return ledger;
}

const pv1::Bytes& valid_snapshot() {
  static const auto payload = [] {
    auto encoded = ps::encode_snapshot_v1(valid_ledger());
    if (!std::holds_alternative<ps::EncodedSnapshotV1>(encoded)) {
      __builtin_trap();
    }
    return std::get<ps::EncodedSnapshotV1>(
               std::move(encoded))
        .payload;
  }();
  return payload;
}

void require_valid_seed() {
  auto decoded = ps::decode_snapshot_v1(
      valid_snapshot(), valid_ledger().state().parameters);
  if (!std::holds_alternative<ps::DecodedSnapshotV1>(decoded) ||
      std::get<ps::DecodedSnapshotV1>(decoded).ledger.state() !=
          valid_ledger().state()) {
    __builtin_trap();
  }
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(
    const std::uint8_t* data,
    std::size_t size) {
  const auto& parameters = valid_ledger().state().parameters;
  (void)ps::decode_snapshot_v1(
      std::span<const std::uint8_t>(data, size), parameters);
  require_valid_seed();

  if (size != 0) {
    auto structured = valid_snapshot();
    const auto index = static_cast<std::size_t>(data[0]) %
                       structured.size();
    structured[index] ^= data[size - 1];
    (void)ps::decode_snapshot_v1(structured, parameters);
  }
  return 0;
}
