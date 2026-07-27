#include "protocol/application/application_v1.hpp"
#include "protocol/storage/sqlite_ledger.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <sodium.h>

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <variant>
#include <vector>

namespace pa = protocol::application;
namespace ps = protocol::storage;
namespace p = protocol::v1;
namespace pv = protocol_vectors;

namespace {

constexpr std::uint8_t kAppState[] = {
    '"', 'p', 'r', 'o', 't', 'o', 'c', 'o', 'l', '-',
    's', 't', 'a', 'c', 'k', '-', 'v', '1', '"',
};

static_assert(pa::application_code(p::AdmissionError::malformed_transaction) ==
              1);
static_assert(pa::application_code(p::AdmissionError::wrong_chain) == 2);
static_assert(pa::application_code(p::AdmissionError::invalid_signature) == 3);
static_assert(pa::application_code(p::TransferResult::success) == 0);
static_assert(pa::application_code(p::TransferResult::zero_amount) == 257);
static_assert(
    pa::application_code(p::TransferResult::fee_limit_too_low) == 258);
static_assert(pa::application_code(p::TransferResult::expired) == 259);
static_assert(pa::application_code(p::TransferResult::sender_not_found) == 260);
static_assert(pa::application_code(p::TransferResult::nonce_exhausted) == 261);
static_assert(pa::application_code(p::TransferResult::nonce_mismatch) == 262);
static_assert(pa::application_code(p::TransferResult::debit_overflow) == 263);
static_assert(
    pa::application_code(p::TransferResult::insufficient_balance) == 264);

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
Tagged tagged_hash(const pv::Bytes& bytes) {
  pv::require(bytes.size() == 32, "tagged hash size");
  p::Hash raw{};
  std::copy(bytes.begin(), bytes.end(), raw.begin());
  return Tagged{raw};
}

std::vector<p::Bytes> raw_transactions(const pv::Values& values) {
  const auto count = std::stoull(values.at("raw_count"));
  std::vector<p::Bytes> result;
  result.reserve(count);
  for (std::size_t index = 0; index < count; ++index) {
    result.push_back(
        pv::hex_decode(values.at("raw" + std::to_string(index))));
  }
  return result;
}

p::Bytes genesis_bytes(const pv::Values& values) {
  return pv::hex_decode(values.at("genesis"));
}

ps::SQLiteLedger take_ledger(
    ps::SQLiteLedgerResult result,
    std::string_view message) {
  pv::require(std::holds_alternative<ps::SQLiteLedger>(result.result),
              message);
  return std::get<ps::SQLiteLedger>(std::move(result.result));
}

pa::ApplicationV1 take_application(
    pa::ApplicationV1Result result,
    std::string_view message) {
  pv::require(
      std::holds_alternative<pa::ApplicationV1>(result.result), message);
  return std::get<pa::ApplicationV1>(std::move(result.result));
}

pa::ApplicationV1 create_application(
    const std::filesystem::path& path,
    const p::Bytes& genesis) {
  return take_application(
      pa::make_application_v1(take_ledger(
          ps::create_sqlite_ledger(path, genesis),
          "create SQLite ledger")),
      "create application");
}

pa::ApplicationV1 open_application(
    const std::filesystem::path& path,
    const p::Bytes& genesis) {
  return take_application(
      pa::make_application_v1(take_ledger(
          ps::open_sqlite_ledger(path, genesis),
          "open SQLite ledger")),
      "open application");
}

template <typename Expected, typename Result>
Expected take(Result result, std::string_view message) {
  pv::require(std::holds_alternative<Expected>(result), message);
  return std::get<Expected>(std::move(result));
}

template <typename Result>
void require_error(
    Result result,
    pa::ApplicationError expected,
    std::string_view message) {
  pv::require(
      std::holds_alternative<pa::ApplicationError>(result) &&
          std::get<pa::ApplicationError>(result) == expected,
      message);
}

void initialize(
    pa::ApplicationV1& application,
    const p::ChainId& chain_id) {
  pv::require(
      std::holds_alternative<std::monostate>(
          application.init_chain(chain_id, 1, kAppState)),
      "valid InitChain rejected");
}

void verify_result_mapping(
    const pv::Values& values,
    const std::vector<p::Bytes>& transactions,
    const pa::FinalizedBlock& finalized) {
  pv::require(
      finalized.state_root ==
          tagged_hash<p::StateRoot>(
              pv::hex_decode(values.at("resulting_state_root"))),
      "finalized state root");
  pv::require(
      finalized.transaction_results.size() == transactions.size(),
      "raw-aligned application results");

  std::size_t admitted_index = 0;
  for (std::size_t raw_index = 0; raw_index < transactions.size();
       ++raw_index) {
    const auto raw_key = "raw" + std::to_string(raw_index);
    const auto admission =
        std::stoul(values.at(raw_key + ".admission"));
    const auto& result = finalized.transaction_results[raw_index];
    if (admission != 0) {
      pv::require(result.code == admission && result.data.empty(),
                  "admission result mapping");
      continue;
    }

    const auto receipt = pv::hex_decode(
        values.at("receipt" + std::to_string(admitted_index)));
    const auto execution = static_cast<p::TransferResult>(receipt[38]);
    pv::require(
        result.code == pa::application_code(execution) &&
            result.data == receipt,
        "execution result mapping");
    ++admitted_index;
  }
  pv::require(
      admitted_index == std::stoull(values.at("admitted_count")),
      "admitted result count");
}

void verify_lifecycle(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  DatabaseFiles files(prefix.string() + "-lifecycle.db");
  const auto genesis = genesis_bytes(values);
  const auto chain_id = tagged_hash<p::ChainId>(
      pv::hex_decode(values.at("chain_id")));
  const auto initial_root = tagged_hash<p::StateRoot>(
      pv::hex_decode(values.at("previous_state_root")));
  const auto transactions = raw_transactions(values);

  auto application = create_application(files.path(), genesis);
  const auto initial = take<pa::ApplicationInfo>(
      application.info(), "initial Info");
  pv::require(
      initial == pa::ApplicationInfo{
                     pa::kApplicationProtocolVersion, 0, initial_root},
      "initial Info fields");
  require_error(
      application.check_transaction(transactions.front()),
      pa::ApplicationError::sequence_failure,
      "CheckTx before InitChain");
  initialize(application, chain_id);
  initialize(application, chain_id);

  for (std::size_t index = 0; index < transactions.size(); ++index) {
    const auto checked = take<pa::TransactionResult>(
        application.check_transaction(transactions[index]),
        "CheckTx result");
    const auto admission = std::stoul(
        values.at(
            "raw" + std::to_string(index) + ".admission"));
    pv::require(
        checked == pa::TransactionResult{
                       static_cast<std::uint32_t>(admission), {}},
        "CheckTx admission mapping");
  }
  require_error(
      application.check_transaction(
          p::Bytes(pa::kMaximumTransactionBytes + 1)),
      pa::ApplicationError::invalid_request,
      "oversized CheckTx accepted");
  pv::require(
      take<pa::TransactionResult>(
          application.check_transaction(
              p::Bytes(pa::kMaximumTransactionBytes)),
          "maximum CheckTx")
              .code ==
          pa::application_code(
              p::AdmissionError::malformed_transaction),
      "maximum CheckTx did not reach admission");

  const auto prepared = take<pa::PreparedProposal>(
      application.prepare_proposal(400, transactions),
      "PrepareProposal");
  pv::require(
      prepared.transactions ==
          std::vector<p::Bytes>(
              transactions.begin(), transactions.begin() + 2),
      "PrepareProposal exact prefix");
  std::vector<p::Bytes> stopped{
      transactions.front(),
      p::Bytes(pa::kMaximumTransactionBytes + 1),
      transactions[1],
  };
  pv::require(
      take<pa::PreparedProposal>(
          application.prepare_proposal(
              static_cast<std::int64_t>(pa::kMaximumBlockBytes),
              stopped),
          "bounded PrepareProposal")
              .transactions ==
          std::vector<p::Bytes>{transactions.front()},
      "PrepareProposal did not stop at oversized input");
  require_error(
      application.prepare_proposal(-1, transactions),
      pa::ApplicationError::invalid_request,
      "negative proposal budget accepted");

  pv::require(
      take<bool>(
          application.process_proposal(1, transactions),
          "valid ProcessProposal"),
      "valid proposal rejected");
  pv::require(
      !take<bool>(
          application.process_proposal(2, transactions),
          "wrong-height ProcessProposal"),
      "wrong proposal height accepted");
  pv::require(
      !take<bool>(
          application.process_proposal(1, stopped),
          "oversized ProcessProposal"),
      "oversized proposal accepted");

  const auto finalized = take<pa::FinalizedBlock>(
      application.finalize_block(1, transactions),
      "FinalizeBlock");
  verify_result_mapping(values, transactions, finalized);
  pv::require(
      take<pa::ApplicationInfo>(
          application.info(), "staged Info")
              .height == 0,
      "FinalizeBlock changed durable height");
  pv::require(
      take<pa::FinalizedBlock>(
          application.finalize_block(1, transactions),
          "repeated FinalizeBlock") == finalized,
      "repeated FinalizeBlock changed response");

  const auto committed = take<pa::CommittedHead>(
      application.commit(), "Commit");
  pv::require(
      committed ==
          pa::CommittedHead{1, finalized.state_root},
      "Commit head");
  pv::require(
      take<pa::ApplicationInfo>(
          application.info(), "committed Info") ==
          pa::ApplicationInfo{
              pa::kApplicationProtocolVersion, 1,
              finalized.state_root},
      "committed Info fields");
  require_error(
      application.commit(), pa::ApplicationError::sequence_failure,
      "duplicate Commit accepted");
}

void verify_restart_replay(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  DatabaseFiles files(prefix.string() + "-restart.db");
  const auto genesis = genesis_bytes(values);
  const auto chain_id = tagged_hash<p::ChainId>(
      pv::hex_decode(values.at("chain_id")));
  const auto transactions = raw_transactions(values);
  pa::FinalizedBlock preview;

  {
    auto application = create_application(files.path(), genesis);
    initialize(application, chain_id);
    preview = take<pa::FinalizedBlock>(
        application.finalize_block(1, transactions),
        "pre-crash FinalizeBlock");
  }
  {
    auto application = open_application(files.path(), genesis);
    pv::require(
        take<pa::ApplicationInfo>(
            application.info(), "old-head Info")
                .height == 0,
        "preview survived restart");
    initialize(application, chain_id);
    pv::require(
        take<pa::FinalizedBlock>(
            application.finalize_block(1, transactions),
            "replayed FinalizeBlock") == preview,
        "replayed FinalizeBlock changed");
    (void)take<pa::CommittedHead>(
        application.commit(), "replayed Commit");
  }
  {
    auto application = open_application(files.path(), genesis);
    pv::require(
        take<pa::ApplicationInfo>(
            application.info(), "new-head Info")
                .height == 1,
        "durable Commit lost on restart");
    pv::require(
        take<bool>(
            application.process_proposal(2, {}),
            "continued ProcessProposal"),
        "continued empty proposal rejected");
    const auto empty = take<pa::FinalizedBlock>(
        application.finalize_block(2, {}),
        "continued FinalizeBlock");
    pv::require(empty.transaction_results.empty(),
                "empty block produced transaction results");
    pv::require(
        take<pa::CommittedHead>(
            application.commit(), "continued Commit")
                .height == 2,
        "continued height");
  }
}

void verify_resource_boundaries(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  const auto genesis = genesis_bytes(values);
  const auto chain_id = tagged_hash<p::ChainId>(
      pv::hex_decode(values.at("chain_id")));

  {
    DatabaseFiles files(prefix.string() + "-maximum-count.db");
    auto application = create_application(files.path(), genesis);
    initialize(application, chain_id);
    const std::vector<p::Bytes> maximum(pa::kMaximumBlockInputs);
    pv::require(
        take<bool>(
            application.process_proposal(1, maximum),
            "maximum-count ProcessProposal"),
        "maximum-count proposal rejected");
    const auto finalized = take<pa::FinalizedBlock>(
        application.finalize_block(1, maximum),
        "maximum-count FinalizeBlock");
    pv::require(
        finalized.transaction_results.size() == maximum.size() &&
            std::all_of(
                finalized.transaction_results.begin(),
                finalized.transaction_results.end(),
                [](const auto& result) {
                  return result.code ==
                             pa::application_code(
                                 p::AdmissionError::
                                     malformed_transaction) &&
                         result.data.empty();
                }),
        "maximum-count result mapping");
    (void)take<pa::CommittedHead>(
        application.commit(), "maximum-count Commit");
  }
  {
    DatabaseFiles files(prefix.string() + "-maximum-bytes.db");
    auto application = create_application(files.path(), genesis);
    initialize(application, chain_id);
    const std::vector<p::Bytes> maximum(
        pa::kMaximumBlockBytes / pa::kMaximumTransactionBytes,
        p::Bytes(pa::kMaximumTransactionBytes));
    pv::require(
        take<bool>(
            application.process_proposal(1, maximum),
            "maximum-bytes ProcessProposal"),
        "maximum-byte proposal rejected");
    const auto finalized = take<pa::FinalizedBlock>(
        application.finalize_block(1, maximum),
        "maximum-bytes FinalizeBlock");
    pv::require(
        finalized.transaction_results.size() == maximum.size(),
        "maximum-byte result count");
    (void)take<pa::CommittedHead>(
        application.commit(), "maximum-bytes Commit");
  }
  {
    DatabaseFiles files(prefix.string() + "-excess-bytes.db");
    auto application = create_application(files.path(), genesis);
    initialize(application, chain_id);
    std::vector<p::Bytes> excess(
        pa::kMaximumBlockBytes / pa::kMaximumTransactionBytes,
        p::Bytes(pa::kMaximumTransactionBytes));
    excess.push_back(p::Bytes{0});
    pv::require(
        !take<bool>(
            application.process_proposal(1, excess),
            "excess-byte ProcessProposal"),
        "excess-byte proposal accepted");
    require_error(
        application.finalize_block(1, excess),
        pa::ApplicationError::invalid_request,
        "excess-byte FinalizeBlock accepted");
  }
}

void verify_fatal_sequences(
    const pv::Values& values,
    const std::filesystem::path& prefix) {
  const auto genesis = genesis_bytes(values);
  const auto chain_id = tagged_hash<p::ChainId>(
      pv::hex_decode(values.at("chain_id")));
  const auto transactions = raw_transactions(values);

  {
    DatabaseFiles files(prefix.string() + "-bad-init.db");
    auto application = create_application(files.path(), genesis);
    auto wrong_chain = chain_id;
    *wrong_chain.begin() ^= 1U;
    require_error(
        application.init_chain(wrong_chain, 1, kAppState),
        pa::ApplicationError::invalid_request,
        "wrong InitChain accepted");
    require_error(
        application.info(), pa::ApplicationError::sequence_failure,
        "fatal InitChain did not terminate instance");
  }
  {
    DatabaseFiles files(prefix.string() + "-missing-stage.db");
    auto application = create_application(files.path(), genesis);
    initialize(application, chain_id);
    require_error(
        application.commit(), pa::ApplicationError::sequence_failure,
        "Commit without stage accepted");
  }
  {
    DatabaseFiles files(prefix.string() + "-conflict.db");
    auto application = create_application(files.path(), genesis);
    initialize(application, chain_id);
    (void)take<pa::FinalizedBlock>(
        application.finalize_block(1, transactions),
        "conflict baseline FinalizeBlock");
    auto conflict = transactions;
    conflict.pop_back();
    require_error(
        application.finalize_block(1, conflict),
        pa::ApplicationError::sequence_failure,
        "conflicting FinalizeBlock accepted");
  }
  {
    DatabaseFiles files(prefix.string() + "-wrong-height.db");
    auto application = create_application(files.path(), genesis);
    initialize(application, chain_id);
    require_error(
        application.finalize_block(2, {}),
        pa::ApplicationError::kernel_failure,
        "wrong FinalizeBlock height accepted");
  }
  {
    DatabaseFiles files(prefix.string() + "-too-many.db");
    auto application = create_application(files.path(), genesis);
    initialize(application, chain_id);
    const std::vector<p::Bytes> too_many(
        pa::kMaximumBlockInputs + 1);
    require_error(
        application.finalize_block(1, too_many),
        pa::ApplicationError::invalid_request,
        "oversized FinalizeBlock count accepted");
  }
}

}  // namespace

int main(int argc, char** argv) {
  try {
    if (argc != 3) {
      throw std::runtime_error(
          "usage: application_v1_test <ledger-vectors> <database-prefix>");
    }
    pv::require(sodium_init() >= 0, "libsodium initialization");
    const auto values = pv::load_values(argv[1]);
    const std::filesystem::path prefix(argv[2]);
    verify_lifecycle(values, prefix);
    verify_restart_replay(values, prefix);
    verify_resource_boundaries(values, prefix);
    verify_fatal_sequences(values, prefix);
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Application v1 tests: failed: "
              << error.what() << '\n';
    return 1;
  }
}
