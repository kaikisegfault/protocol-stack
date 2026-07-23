#include "protocol/v1/ledger.hpp"

#include <charconv>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <variant>
#include <vector>

namespace {

namespace pv1 = protocol::v1;

constexpr std::size_t kMaximumScenarios = 100'000;
constexpr std::size_t kMaximumBlocksPerScenario = 64;
constexpr std::size_t kMaximumInputsPerBlock = 65'535;
constexpr std::size_t kMaximumEncodedObjectBytes = 1'048'576;

void require(bool condition, std::string_view message) {
  if (!condition) {
    throw std::runtime_error(std::string(message));
  }
}

std::string read_token(std::string_view name) {
  std::string token;
  require(static_cast<bool>(std::cin >> token),
          std::string("missing ") + std::string(name));
  return token;
}

std::uint64_t parse_u64(std::string_view value, std::string_view name) {
  std::uint64_t parsed = 0;
  const auto result =
      std::from_chars(value.data(), value.data() + value.size(), parsed);
  require(result.ec == std::errc{} &&
              result.ptr == value.data() + value.size(),
          std::string("invalid ") + std::string(name));
  return parsed;
}

std::size_t parse_count(std::string_view value, std::size_t maximum,
                        std::string_view name) {
  const auto parsed = parse_u64(value, name);
  require(parsed <= maximum, std::string(name) + " exceeds test bound");
  require(parsed <= std::numeric_limits<std::size_t>::max(),
          std::string(name) + " exceeds host size");
  return static_cast<std::size_t>(parsed);
}

std::uint8_t nibble(char value) {
  if (value >= '0' && value <= '9') {
    return static_cast<std::uint8_t>(value - '0');
  }
  if (value >= 'a' && value <= 'f') {
    return static_cast<std::uint8_t>(value - 'a' + 10);
  }
  throw std::runtime_error("invalid lowercase hexadecimal");
}

pv1::Bytes decode_hex(std::string_view encoded) {
  if (encoded == "-") {
    return {};
  }
  require(encoded.size() % 2 == 0, "odd hexadecimal length");
  require(encoded.size() / 2 <= kMaximumEncodedObjectBytes,
          "encoded object exceeds test bound");
  pv1::Bytes decoded;
  decoded.reserve(encoded.size() / 2);
  for (std::size_t offset = 0; offset < encoded.size(); offset += 2) {
    decoded.push_back(static_cast<std::uint8_t>(
        (nibble(encoded[offset]) << 4U) | nibble(encoded[offset + 1])));
  }
  return decoded;
}

template <typename ByteRange>
std::string encode_hex(const ByteRange& bytes) {
  constexpr char kHex[] = "0123456789abcdef";
  std::string encoded;
  encoded.reserve(bytes.size() * 2);
  for (const auto byte : bytes) {
    const auto value = static_cast<std::uint8_t>(byte);
    encoded.push_back(kHex[value >> 4U]);
    encoded.push_back(kHex[value & 0x0FU]);
  }
  return encoded;
}

template <typename Range, typename Encoder>
void write_list(const Range& values, Encoder encode) {
  if (values.empty()) {
    std::cout << '-';
    return;
  }
  bool first = true;
  for (const auto& value : values) {
    if (!first) {
      std::cout << ',';
    }
    first = false;
    std::cout << encode(value);
  }
}

void write_accounts(const pv1::State& state) {
  if (state.accounts.empty()) {
    std::cout << '-';
    return;
  }
  bool first = true;
  for (const auto& [identifier, account] : state.accounts) {
    if (!first) {
      std::cout << ',';
    }
    first = false;
    std::cout << encode_hex(identifier) << ':' << account.balance << ':'
              << account.nonce;
  }
}

void write_transcript(std::uint64_t scenario, std::size_t block_index,
                      const pv1::BlockCommit& commit,
                      const pv1::State& state) {
  require(commit.admissions.size() <= kMaximumInputsPerBlock,
          "invalid admission transcript");
  require(commit.transaction_ids.size() == commit.receipts.size() &&
              commit.receipts.size() == commit.encoded_receipts.size(),
          "misaligned admitted transcript");

  std::cout << "D\t" << scenario << '\t' << block_index << '\t'
            << commit.height << '\t';
  write_list(commit.admissions, [](const auto& admission) {
    return admission ? std::to_string(static_cast<unsigned>(*admission))
                     : std::string("0");
  });
  std::cout << '\t';
  write_list(commit.transaction_ids,
             [](const auto& identifier) { return encode_hex(identifier); });
  std::cout << '\t';
  write_list(commit.encoded_receipts,
             [](const auto& receipt) { return encode_hex(receipt); });
  std::cout << '\t';
  write_list(commit.receipts, [](const auto& receipt) {
    return encode_hex(receipt.transaction_id) + ":" +
           std::to_string(static_cast<unsigned>(receipt.result)) + ":" +
           std::to_string(receipt.fee_charged);
  });
  std::cout << '\t' << encode_hex(commit.previous_state_root) << '\t'
            << encode_hex(commit.transaction_root) << '\t'
            << encode_hex(commit.resulting_state_root) << '\t'
            << encode_hex(commit.header) << '\t'
            << encode_hex(commit.block_id) << '\t'
            << encode_hex(state.parameters.chain_id) << '\t'
            << state.parameters.supply_limit << '\t'
            << state.parameters.total_supply << '\t'
            << state.parameters.fixed_fee << '\t' << state.height << '\t'
            << state.fee_pool << '\t';
  write_accounts(state);
  std::cout << '\n';
}

void run_scenario() {
  require(read_token("scenario marker") == "S", "expected scenario marker");
  const auto scenario = parse_u64(read_token("scenario ID"), "scenario ID");
  auto genesis = decode_hex(read_token("genesis"));
  const auto block_count =
      parse_count(read_token("block count"), kMaximumBlocksPerScenario,
                  "block count");

  auto loaded = pv1::load_genesis(genesis);
  require(std::holds_alternative<pv1::Ledger>(loaded.result),
          "generated genesis rejected");
  std::optional<pv1::Ledger> ledger;
  ledger.emplace(std::get<pv1::Ledger>(std::move(loaded.result)));

  for (std::size_t block_index = 0; block_index < block_count; ++block_index) {
    require(read_token("block marker") == "B", "expected block marker");
    const auto height = parse_u64(read_token("block height"), "block height");
    const auto raw_count =
        parse_count(read_token("raw input count"), kMaximumInputsPerBlock,
                    "raw input count");
    std::vector<pv1::Bytes> raw_transactions;
    raw_transactions.reserve(raw_count);
    for (std::size_t index = 0; index < raw_count; ++index) {
      raw_transactions.push_back(decode_hex(read_token("raw transaction")));
    }

    auto applied = ledger->apply_block(height, raw_transactions);
    require(std::holds_alternative<pv1::BlockCommit>(applied),
            "generated block rejected");
    const auto& commit = std::get<pv1::BlockCommit>(applied);
    auto current_root = ledger->current_state_root();
    require(std::holds_alternative<pv1::StateRoot>(current_root) &&
                std::get<pv1::StateRoot>(current_root) ==
                    commit.resulting_state_root,
            "public current state root disagrees with block commit");
    write_transcript(scenario, block_index, commit, ledger->state());
  }
}

}  // namespace

int main() {
  try {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    require(read_token("protocol magic") == "PSDIFF1",
            "unsupported differential protocol");
    const auto scenario_count =
        parse_count(read_token("scenario count"), kMaximumScenarios,
                    "scenario count");
    for (std::size_t index = 0; index < scenario_count; ++index) {
      run_scenario();
    }
    std::string trailing;
    require(!(std::cin >> trailing), "trailing differential request");
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "kernel differential runner: failed: " << error.what()
              << '\n';
    return 1;
  }
}
