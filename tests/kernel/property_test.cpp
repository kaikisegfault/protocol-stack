#include "../../src/v1/commitments.hpp"
#include "../../src/v1/execution.hpp"
#include "../../tools/protocol-vectors/vector_common.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <iostream>
#include <limits>
#include <utility>
#include <variant>

namespace pv = protocol_vectors;
namespace p = protocol::v1;

namespace {

constexpr std::size_t kScenarioCount = 9'000;
constexpr std::uint64_t kTotalSupply = 10'000'000;

class SplitMix64 {
 public:
  explicit SplitMix64(std::uint64_t state) : state_(state) {}

  std::uint64_t next() {
    auto value = (state_ += 0x9e3779b97f4a7c15ULL);
    value = (value ^ (value >> 30U)) * 0xbf58476d1ce4e5b9ULL;
    value = (value ^ (value >> 27U)) * 0x94d049bb133111ebULL;
    return value ^ (value >> 31U);
  }

 private:
  std::uint64_t state_;
};

template <typename Tagged>
Tagged tagged_value(SplitMix64& random, std::uint8_t discriminator) {
  p::Hash bytes{};
  bytes[0] = discriminator;
  for (std::size_t offset = 1; offset < bytes.size(); offset += 8) {
    const auto value = random.next();
    const auto remaining = bytes.size() - offset;
    const auto width = remaining < 8 ? remaining : 8;
    for (std::size_t index = 0; index < width; ++index) {
      bytes[offset + index] =
          static_cast<std::uint8_t>(value >> (index * 8U));
    }
  }
  return Tagged{bytes};
}

std::uint64_t conserved_supply(const p::State& state) {
  auto sum = state.fee_pool;
  for (const auto& [identifier, account] : state.accounts) {
    static_cast<void>(identifier);
    pv::require(
        account.balance <= std::numeric_limits<std::uint64_t>::max() - sum,
        "property supply addition overflow");
    sum += account.balance;
  }
  return sum;
}

struct Scenario {
  p::State state;
  p::Transfer transfer;
  p::TransferResult expected;
};

Scenario make_scenario(std::size_t index) {
  SplitMix64 random{0x6c65646765722d31ULL ^
                    static_cast<std::uint64_t>(index)};
  std::array<p::AccountId, 4> identifiers{
      tagged_value<p::AccountId>(random, 1),
      tagged_value<p::AccountId>(random, 2),
      tagged_value<p::AccountId>(random, 3),
      tagged_value<p::AccountId>(random, 4),
  };
  const auto absent = tagged_value<p::AccountId>(random, 8);
  const auto new_recipient = tagged_value<p::AccountId>(random, 9);
  const auto chain_id = tagged_value<p::ChainId>(random, 10);
  const auto transaction_id =
      tagged_value<p::TransactionId>(random, 11);
  const auto fixed_fee = 1 + random.next() % 10'000;
  const auto fee_pool = random.next() % 10'000;
  const auto first_balance = 1'000'000 + random.next() % 100'000;
  const auto second_balance = 1'000'000 + random.next() % 100'000;
  const auto third_balance = 1'000'000 + random.next() % 100'000;
  const auto fourth_balance =
      kTotalSupply - fee_pool - first_balance - second_balance -
      third_balance;
  const auto sender_nonce = random.next() % 10'000;
  const auto height = random.next() % 1'000'000;
  const auto block_height = height + 1;

  p::State state{
      p::Parameters{
          chain_id,
          kTotalSupply + 1'000'000,
          kTotalSupply,
          fixed_fee,
      },
      height,
      fee_pool,
      {
          {identifiers[0], p::Account{first_balance, sender_nonce}},
          {identifiers[1],
           p::Account{second_balance, random.next() % 10'000}},
          {identifiers[2],
           p::Account{third_balance, random.next() % 10'000}},
          {identifiers[3],
           p::Account{fourth_balance, random.next() % 10'000}},
      },
  };
  const auto success_kind = (index / 9) % 3;
  auto recipient = identifiers[1];
  if (success_kind == 1) recipient = identifiers[0];
  if (success_kind == 2) recipient = new_recipient;
  p::Transfer transfer{
      identifiers[0],
      transaction_id,
      sender_nonce + 1,
      recipient,
      1 + random.next() % 100'000,
      fixed_fee,
      block_height + random.next() % 100,
  };

  const auto expected =
      static_cast<p::TransferResult>(index % 9);
  switch (expected) {
    case p::TransferResult::success:
      break;
    case p::TransferResult::zero_amount:
      transfer.amount = 0;
      transfer.fee_limit = 0;
      transfer.valid_until = block_height - 1;
      transfer.sender_id = absent;
      break;
    case p::TransferResult::fee_limit_too_low:
      transfer.fee_limit = fixed_fee - 1;
      transfer.valid_until = block_height - 1;
      transfer.sender_id = absent;
      break;
    case p::TransferResult::expired:
      transfer.valid_until = block_height - 1;
      transfer.sender_id = absent;
      break;
    case p::TransferResult::sender_not_found:
      transfer.sender_id = absent;
      transfer.nonce = 0;
      transfer.amount = std::numeric_limits<std::uint64_t>::max();
      break;
    case p::TransferResult::nonce_exhausted:
      state.accounts.at(transfer.sender_id).nonce =
          std::numeric_limits<std::uint64_t>::max();
      transfer.nonce = 0;
      transfer.amount = std::numeric_limits<std::uint64_t>::max();
      break;
    case p::TransferResult::nonce_mismatch:
      transfer.nonce = sender_nonce + 2;
      transfer.amount = std::numeric_limits<std::uint64_t>::max();
      break;
    case p::TransferResult::debit_overflow:
      transfer.amount = std::numeric_limits<std::uint64_t>::max();
      break;
    case p::TransferResult::insufficient_balance:
      transfer.amount = first_balance;
      break;
  }
  return Scenario{std::move(state), transfer, expected};
}

void require_success_effects(const p::State& before,
                             const p::State& after,
                             const p::Transfer& transfer) {
  const auto fee = before.parameters.fixed_fee;
  const auto sender_before = before.accounts.at(transfer.sender_id);
  const auto sender_after = after.accounts.at(transfer.sender_id);
  auto expected = before;
  auto& expected_sender = expected.accounts.at(transfer.sender_id);
  expected.fee_pool += fee;
  expected_sender.nonce = transfer.nonce;
  pv::require(after.fee_pool == before.fee_pool + fee,
              "property fee routing");
  pv::require(sender_after.nonce == transfer.nonce,
              "property nonce advancement");
  if (transfer.sender_id == transfer.recipient) {
    expected_sender.balance -= fee;
    pv::require(sender_after.balance == sender_before.balance - fee,
                "property self-transfer balance");
    pv::require(after.accounts.size() == before.accounts.size(),
                "property self-transfer account count");
    pv::require(after == expected, "property exact self-transfer state");
    return;
  }

  expected_sender.balance -= transfer.amount + fee;
  const auto expected_recipient =
      expected.accounts.find(transfer.recipient);
  if (expected_recipient == expected.accounts.end()) {
    expected.accounts.emplace(
        transfer.recipient, p::Account{transfer.amount, 0});
  } else {
    expected_recipient->second.balance += transfer.amount;
  }
  pv::require(
      sender_after.balance ==
          sender_before.balance - transfer.amount - fee,
      "property sender debit");
  const auto recipient_before = before.accounts.find(transfer.recipient);
  const auto recipient_after = after.accounts.find(transfer.recipient);
  pv::require(recipient_after != after.accounts.end(),
              "property recipient exists");
  if (recipient_before == before.accounts.end()) {
    pv::require(
        recipient_after->second == p::Account{transfer.amount, 0},
        "property recipient creation");
    pv::require(after.accounts.size() == before.accounts.size() + 1,
                "property recipient creation count");
  } else {
    pv::require(
        recipient_after->second.balance ==
            recipient_before->second.balance + transfer.amount,
        "property recipient credit");
    pv::require(
        recipient_after->second.nonce == recipient_before->second.nonce,
        "property recipient nonce");
  }
  pv::require(after == expected, "property exact transfer state");
}

void verify_properties() {
  std::array<std::size_t, 9> coverage{};
  for (std::size_t index = 0; index < kScenarioCount; ++index) {
    auto scenario = make_scenario(index);
    const auto before = scenario.state;
    auto repeated_state = scenario.state;
    const auto execution = p::internal::execute_transfer(
        scenario.transfer, scenario.state, scenario.state.height + 1);
    const auto repeated = p::internal::execute_transfer(
        scenario.transfer, repeated_state, repeated_state.height + 1);
    pv::require(std::holds_alternative<p::Receipt>(execution),
                "property unexpected invariant failure");
    pv::require(execution == repeated && scenario.state == repeated_state,
                "property execution determinism");

    const auto& receipt = std::get<p::Receipt>(execution);
    pv::require(receipt.transaction_id == scenario.transfer.transaction_id,
                "property receipt transaction ID");
    pv::require(receipt.result == scenario.expected,
                "property result precedence");
    const auto result_index = static_cast<std::size_t>(receipt.result);
    pv::require(result_index < coverage.size(), "property result range");
    ++coverage[result_index];

    const auto encoded = p::internal::encode_receipt(
        receipt, scenario.state.parameters.fixed_fee);
    pv::require(encoded.has_value() && encoded->size() == 47,
                "property canonical receipt");
    if (receipt.result == p::TransferResult::success) {
      pv::require(
          receipt.fee_charged == before.parameters.fixed_fee,
          "property successful fee");
      require_success_effects(before, scenario.state, scenario.transfer);
    } else {
      pv::require(receipt.fee_charged == 0,
                  "property failed fee");
      pv::require(scenario.state == before,
                  "property failure atomicity");
    }
    pv::require(scenario.state.height == before.height,
                "property execution height");
    pv::require(conserved_supply(scenario.state) == kTotalSupply,
                "property supply conservation");
    pv::require(
        std::holds_alternative<p::StateRoot>(
            p::internal::state_root(scenario.state)),
        "property state commitment");
  }
  for (const auto count : coverage) {
    pv::require(count == kScenarioCount / coverage.size(),
                "property result coverage");
  }
}

}  // namespace

int main() {
  try {
    verify_properties();
    std::cout << "Kernel properties: passed " << kScenarioCount
              << " deterministic scenarios\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Kernel properties: failed: " << error.what() << '\n';
    return 1;
  }
}
