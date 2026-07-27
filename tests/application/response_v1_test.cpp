#include "protocol/application/dispatcher_v1.hpp"
#include "protocol/application/response_v1.hpp"
#include "protocol/storage/sqlite_ledger.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <algorithm>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <iostream>
#include <string_view>
#include <utility>
#include <variant>

namespace pa = protocol::application;
namespace ps = protocol::storage;
namespace p = protocol::v1;
namespace pv = protocol_vectors;

namespace {

constexpr std::uint8_t kAppState[] = {
    '"', 'p', 'r', 'o', 't', 'o', 'c', 'o', 'l', '-',
    's', 't', 'a', 'c', 'k', '-', 'v', '1', '"',
};

class DatabaseFiles {
 public:
  explicit DatabaseFiles(std::filesystem::path path)
      : path_(std::move(path)) {
    remove();
  }
  ~DatabaseFiles() { remove(); }
  const std::filesystem::path& path() const noexcept { return path_; }

 private:
  void remove() noexcept {
    std::error_code ignored;
    std::filesystem::remove(path_, ignored);
    std::filesystem::remove(path_.string() + "-journal", ignored);
    std::filesystem::remove(path_.string() + "-wal", ignored);
    std::filesystem::remove(path_.string() + "-shm", ignored);
  }
  std::filesystem::path path_;
};

template <typename Tagged>
Tagged tagged_hash(const p::Bytes& bytes) {
  pv::require(bytes.size() == 32, "tagged hash size");
  p::Hash raw{};
  std::copy(bytes.begin(), bytes.end(), raw.begin());
  return Tagged{raw};
}

template <typename Expected, typename Result>
Expected take(Result result, std::string_view message) {
  pv::require(std::holds_alternative<Expected>(result), message);
  return std::get<Expected>(std::move(result));
}

std::uint16_t read_u16(
    const p::Bytes& bytes, std::size_t offset) {
  pv::require(offset + 2 <= bytes.size(), "truncated u16");
  return static_cast<std::uint16_t>(
      (static_cast<std::uint16_t>(bytes[offset]) << 8U) |
      bytes[offset + 1]);
}

std::uint32_t read_u32(
    const p::Bytes& bytes, std::size_t offset) {
  pv::require(offset + 4 <= bytes.size(), "truncated u32");
  std::uint32_t value = 0;
  for (std::size_t index = 0; index < 4; ++index) {
    value = (value << 8U) | bytes[offset + index];
  }
  return value;
}

std::uint64_t read_u64(
    const p::Bytes& bytes, std::size_t offset) {
  return pv::read_u64(bytes, offset);
}

p::Bytes response_payload(
    pa::EncodedFrameResult encoded,
    pa::MessageKind kind,
    std::uint64_t request_id) {
  auto bytes = take<p::Bytes>(std::move(encoded), "encode response");
  auto frame = take<pa::Frame>(
      pa::decode_frame(bytes), "decode response frame");
  pv::require(
      frame.header.direction == pa::WireDirection::response &&
          frame.header.kind == kind &&
          frame.header.request_id == request_id,
      "response envelope");
  return frame.payload;
}

void require_success_prefix(const p::Bytes& payload) {
  pv::require(
      read_u16(payload, 0) == 0 && read_u32(payload, 2) == 0,
      "success response prefix");
}

pa::ApplicationV1 make_application(
    const std::filesystem::path& path,
    const p::Bytes& genesis) {
  auto ledger = ps::create_sqlite_ledger(path, genesis);
  pv::require(
      std::holds_alternative<ps::SQLiteLedger>(ledger.result),
      "create response test ledger");
  auto application = pa::make_application_v1(
      std::get<ps::SQLiteLedger>(std::move(ledger.result)));
  pv::require(
      std::holds_alternative<pa::ApplicationV1>(
          application.result),
      "create response test application");
  return std::get<pa::ApplicationV1>(
      std::move(application.result));
}

void verify_response_encoding(const p::StateRoot& root) {
  const auto info = response_payload(
      pa::encode_success_response(
          pa::MessageKind::info, 0x0102030405060708ULL,
          pa::SuccessResponse{pa::ApplicationInfo{1, 2, root}}),
      pa::MessageKind::info, 0x0102030405060708ULL);
  require_success_prefix(info);
  pv::require(
      info.size() == 54 && read_u64(info, 6) == 1 &&
          read_u64(info, 14) == 2 &&
          std::equal(root.begin(), root.end(), info.begin() + 22),
      "frozen Info response fields");

  const auto error = response_payload(
      pa::encode_error_response(
          pa::MessageKind::commit, 9,
          pa::ApplicationError::sequence_failure),
      pa::MessageKind::commit, 9);
  pv::require(
      error == p::Bytes({0, 3, 0, 0, 0, 0}),
      "frozen error response");

  auto mismatch = pa::encode_success_response(
      pa::MessageKind::commit, 1,
      pa::SuccessResponse{pa::ApplicationInfo{1, 0, root}});
  pv::require(
      std::holds_alternative<pa::WireError>(mismatch) &&
          std::get<pa::WireError>(mismatch) ==
              pa::WireError::invalid_payload,
      "response kind mismatch accepted");

  auto invalid_result = pa::encode_success_response(
      pa::MessageKind::finalize_block, 2,
      pa::SuccessResponse{
          pa::FinalizedBlock{
              root, {pa::TransactionResult{0, {}}}}});
  pv::require(
      std::holds_alternative<pa::WireError>(invalid_result) &&
          std::get<pa::WireError>(invalid_result) ==
              pa::WireError::invalid_payload,
      "invalid FinalizeBlock code/data accepted");

  const auto process = response_payload(
      pa::encode_success_response(
          pa::MessageKind::process_proposal, 2,
          pa::SuccessResponse{true}),
      pa::MessageKind::process_proposal, 2);
  pv::require(
      process == p::Bytes({0, 0, 0, 0, 0, 0, 1}),
      "frozen ProcessProposal response");
}

void verify_dispatch(
    const pv::Values& values,
    const std::filesystem::path& database_path) {
  DatabaseFiles files(database_path);
  const auto genesis = pv::hex_decode(values.at("genesis"));
  const auto chain_id = tagged_hash<p::ChainId>(
      pv::hex_decode(values.at("chain_id")));
  const auto initial_root = tagged_hash<p::StateRoot>(
      pv::hex_decode(values.at("previous_state_root")));
  auto application = make_application(files.path(), genesis);

  const auto info = response_payload(
      pa::dispatch_request(
          application,
          pa::DecodedRequest{
              pa::MessageKind::info, 1, pa::EmptyRequest{}}),
      pa::MessageKind::info, 1);
  require_success_prefix(info);
  pv::require(
      read_u64(info, 14) == 0 &&
          std::equal(
              initial_root.begin(), initial_root.end(),
              info.begin() + 22),
      "initial Info dispatch");

  const auto invalid = response_payload(
      pa::dispatch_request(
          application,
          pa::DecodedRequest{
              pa::MessageKind::info, 2,
              pa::BlockRequest{1, {}}}),
      pa::MessageKind::info, 2);
  pv::require(read_u16(invalid, 0) == 1, "invalid payload status");

  const auto initialized = response_payload(
      pa::dispatch_request(
          application,
          pa::DecodedRequest{
              pa::MessageKind::init_chain, 3,
              pa::InitChainRequest{
                  chain_id, 1,
                  p::Bytes(
                      std::begin(kAppState), std::end(kAppState))}}),
      pa::MessageKind::init_chain, 3);
  require_success_prefix(initialized);
  pv::require(
      initialized.size() == 38 &&
          std::equal(
              initial_root.begin(), initial_root.end(),
              initialized.begin() + 6),
      "InitChain root dispatch");

  const auto checked = response_payload(
      pa::dispatch_request(
          application,
          pa::DecodedRequest{
              pa::MessageKind::check_transaction, 4,
              pa::CheckTransactionRequest{{0}}}),
      pa::MessageKind::check_transaction, 4);
  require_success_prefix(checked);
  pv::require(read_u32(checked, 6) == 1, "CheckTx code dispatch");

  const auto prepared = response_payload(
      pa::dispatch_request(
          application,
          pa::DecodedRequest{
              pa::MessageKind::prepare_proposal, 5,
              pa::PrepareProposalRequest{0, {{0}}}}),
      pa::MessageKind::prepare_proposal, 5);
  require_success_prefix(prepared);
  pv::require(read_u32(prepared, 6) == 0, "PrepareProposal dispatch");

  const auto processed = response_payload(
      pa::dispatch_request(
          application,
          pa::DecodedRequest{
              pa::MessageKind::process_proposal, 6,
              pa::BlockRequest{1, {}}}),
      pa::MessageKind::process_proposal, 6);
  require_success_prefix(processed);
  pv::require(processed.at(6) == 1, "ProcessProposal dispatch");

  const auto finalized = response_payload(
      pa::dispatch_request(
          application,
          pa::DecodedRequest{
              pa::MessageKind::finalize_block, 7,
              pa::BlockRequest{1, {}}}),
      pa::MessageKind::finalize_block, 7);
  require_success_prefix(finalized);
  pv::require(
      finalized.size() == 42 && read_u32(finalized, 38) == 0,
      "FinalizeBlock dispatch");
  p::Hash finalized_raw{};
  std::copy(
      finalized.begin() + 6, finalized.begin() + 38,
      finalized_raw.begin());
  const p::StateRoot finalized_root{finalized_raw};

  const auto staged_info = response_payload(
      pa::dispatch_request(
          application,
          pa::DecodedRequest{
              pa::MessageKind::info, 8, pa::EmptyRequest{}}),
      pa::MessageKind::info, 8);
  pv::require(
      read_u64(staged_info, 14) == 0,
      "staged Info exposed candidate");

  const auto committed = response_payload(
      pa::dispatch_request(
          application,
          pa::DecodedRequest{
              pa::MessageKind::commit, 9, pa::EmptyRequest{}}),
      pa::MessageKind::commit, 9);
  require_success_prefix(committed);
  pv::require(
      committed.size() == 46 && read_u64(committed, 6) == 1 &&
          std::equal(
              finalized_root.begin(), finalized_root.end(),
              committed.begin() + 14),
      "Commit dispatch");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 3) {
      throw std::runtime_error(
          "usage: response_v1_test <ledger-vectors> <database>");
    }
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const auto root = tagged_hash<p::StateRoot>(
        pv::hex_decode(values.at("previous_state_root")));
    verify_response_encoding(root);
    verify_dispatch(values, argv[2]);
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Application response v1 tests: failed: "
              << error.what() << '\n';
    return 1;
  }
}
