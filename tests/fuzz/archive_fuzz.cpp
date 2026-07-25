#include "protocol/storage/archive_v1.hpp"
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

pv1::Bytes fixture_genesis() {
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
  return genesis;
}

const pv1::Bytes& valid_archive() {
  static const auto payload = [] {
    const auto genesis = fixture_genesis();
    auto loaded = pv1::load_genesis(genesis);
    if (!std::holds_alternative<pv1::Ledger>(loaded.result)) {
      __builtin_trap();
    }
    const auto& ledger = std::get<pv1::Ledger>(loaded.result);
    auto snapshot = ps::encode_snapshot_v1(ledger);
    if (!std::holds_alternative<ps::EncodedSnapshotV1>(snapshot)) {
      __builtin_trap();
    }
    auto archive = ps::encode_archive_v1(ps::ArchiveV1Data{
        genesis,
        {},
        std::get<ps::EncodedSnapshotV1>(snapshot).payload,
    });
    if (!std::holds_alternative<ps::EncodedArchiveV1>(archive)) {
      __builtin_trap();
    }
    return std::get<ps::EncodedArchiveV1>(
               std::move(archive))
        .payload;
  }();
  return payload;
}

void require_valid_seed() {
  if (!std::holds_alternative<ps::DecodedArchiveV1>(
          ps::decode_archive_v1(valid_archive()))) {
    __builtin_trap();
  }
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(
    const std::uint8_t* data,
    std::size_t size) {
  (void)ps::decode_archive_v1(
      std::span<const std::uint8_t>(data, size));
  require_valid_seed();
  if (size != 0) {
    auto structured = valid_archive();
    const auto index = static_cast<std::size_t>(data[0]) %
                       structured.size();
    structured[index] ^= data[size - 1];
    (void)ps::decode_archive_v1(structured);
  }
  return 0;
}
