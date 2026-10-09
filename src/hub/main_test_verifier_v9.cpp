// `protocol-hub-test-verifier-v9`: the test HUB verifier as one command
// (ADR 0099).
//
//   key      <verifier-seed>
//   register <verifier-seed> <chain-id> <secret> <first-signer> <valid-until>
//   approve  <verifier-seed> <secret> <unsigned-transaction> <acting-escrow>
//
// Every argument is hex except the height. It prints `key=value` lines. A
// refusal prints `refusal=<name>` and exits 3, and a malformed argument exits 2.
// It reads no clock, no file, and no network, so two runs on one input print
// the same bytes.

#include "protocol/hub/verifier_v9.hpp"

#include <algorithm>
#include <charconv>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <optional>
#include <span>
#include <sstream>
#include <string>
#include <string_view>
#include <vector>

namespace hub = protocol::hub;
namespace v9 = protocol::v9;

namespace {

constexpr int kUsage = 2;
constexpr int kRefused = 3;

int digit(char character) {
  if (character >= '0' && character <= '9') return character - '0';
  if (character >= 'a' && character <= 'f') return character - 'a' + 10;
  if (character >= 'A' && character <= 'F') return character - 'A' + 10;
  return -1;
}

std::optional<hub::Bytes> hex(std::string_view text) {
  if (text.size() % 2 != 0) return std::nullopt;
  hub::Bytes bytes;
  bytes.reserve(text.size() / 2);
  for (std::size_t index = 0; index < text.size(); index += 2) {
    const int high = digit(text[index]);
    const int low = digit(text[index + 1]);
    if (high < 0 || low < 0) return std::nullopt;
    bytes.push_back(static_cast<std::uint8_t>(high * 16 + low));
  }
  return bytes;
}

std::optional<hub::Octets32> octets32(std::string_view text) {
  const auto bytes = hex(text);
  if (!bytes || bytes->size() != 32) return std::nullopt;
  hub::Octets32 value{};
  std::copy(bytes->begin(), bytes->end(), value.begin());
  return value;
}

std::optional<std::uint64_t> height(std::string_view text) {
  std::uint64_t value = 0;
  const auto* end = text.data() + text.size();
  const auto [last, error] = std::from_chars(text.data(), end, value);
  if (text.empty() || error != std::errc{} || last != end) return std::nullopt;
  return value;
}

std::string uppercase_hex(std::span<const std::uint8_t> bytes) {
  std::ostringstream output;
  output << std::hex << std::uppercase << std::setfill('0');
  for (const auto octet : bytes) output << std::setw(2) << static_cast<int>(octet);
  return output.str();
}

int usage(std::string_view reason) {
  std::cerr << "protocol-hub-test-verifier-v9: " << reason << '\n'
            << "usage: protocol-hub-test-verifier-v9 key <verifier-seed>\n"
            << "       protocol-hub-test-verifier-v9 register <verifier-seed> "
               "<chain-id> <secret> <first-signer> <valid-until>\n"
            << "       protocol-hub-test-verifier-v9 approve <verifier-seed> "
               "<secret> <unsigned-transaction> <acting-escrow>\n";
  return kUsage;
}

// The transaction a person approves, decoded by the kernel's own admission
// shape check. It is handed over unsigned, so 64 zero octets stand where the
// signature will go.
std::optional<v9::Envelope> unsigned_transaction(std::string_view text) {
  auto raw = hex(text);
  if (!raw) return std::nullopt;
  raw->insert(raw->end(), v9::kSignatureBytes, 0);
  const auto decoded = v9::decode_signed(*raw);
  if (!decoded) return std::nullopt;
  return decoded->envelope;
}

int print(const hub::Decision& decision) {
  std::cout << "hub_identity_hash="
            << uppercase_hex(decision.identity.hub_identity_hash) << '\n'
            << "hub_public_key=" << uppercase_hex(decision.identity.hub_public_key)
            << '\n';
  if (!decision.approved()) {
    std::cout << "refusal=" << hub::refusal_name(*decision.refusal) << '\n';
    return kRefused;
  }
  if (!decision.hub_signature.empty()) {
    std::cout << "hub_signature=" << uppercase_hex(decision.hub_signature) << '\n';
  }
  if (!decision.signed_transaction.empty()) {
    std::cout << "signed_transaction="
              << uppercase_hex(decision.signed_transaction) << '\n';
  }
  return 0;
}

int run(const std::vector<std::string_view>& arguments) {
  if (arguments.size() < 2) return usage("missing a command or a verifier seed");
  const auto seed = octets32(arguments[1]);
  if (!seed) return usage("the verifier seed is not 32 octets of hex");
  const hub::TestVerifierV9 verifier(*seed);
  const auto command = arguments[0];

  if (command == "key" && arguments.size() == 2) {
    std::cout << "verifier_public_key=" << uppercase_hex(verifier.registration_key())
              << '\n';
    return 0;
  }
  if (command == "register" && arguments.size() == 6) {
    const auto chain_id = octets32(arguments[2]);
    const auto secret = octets32(arguments[3]);
    const auto first_signer = octets32(arguments[4]);
    const auto valid_until = height(arguments[5]);
    if (!chain_id || !secret || !first_signer || !valid_until) {
      return usage("a registration argument is malformed");
    }
    hub::RegistrationRequest request;
    request.chain_id = *chain_id;
    request.capture.secret = *secret;
    request.first_signer_public_key = *first_signer;
    request.valid_until_height = *valid_until;
    return print(verifier.register_person(request));
  }
  if (command == "approve" && arguments.size() == 5) {
    const auto secret = octets32(arguments[2]);
    const auto transaction = unsigned_transaction(arguments[3]);
    const auto acting_escrow = octets32(arguments[4]);
    if (!secret || !transaction || !acting_escrow) {
      return usage("an approval argument is malformed");
    }
    hub::ApprovalRequest request;
    request.capture.secret = *secret;
    request.transaction = *transaction;
    request.acting_escrow_id = *acting_escrow;
    return print(verifier.approve(request));
  }
  return usage("unknown command or wrong argument count");
}

}  // namespace

int main(int argc, char** argv) {
  try {
    return run(std::vector<std::string_view>(argv + 1, argv + argc));
  } catch (const std::exception& error) {
    std::cerr << "protocol-hub-test-verifier-v9: " << error.what() << '\n';
    return 1;
  }
}
