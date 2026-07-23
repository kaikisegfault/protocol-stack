#include "protocol/v1/admission.hpp"

#include "../../tools/protocol-vectors/vector_common.hpp"

#include <iostream>
#include <string>
#include <variant>

namespace pv = protocol_vectors;
namespace p = protocol::v1;

p::Hash hash_value(const pv::Bytes& bytes) {
  pv::require(bytes.size() == 32, "hash size");
  p::Hash result{};
  std::copy(bytes.begin(), bytes.end(), result.begin());
  return result;
}

void verify_admission_vectors(const pv::Values& values) {
  const auto chain_id =
      hash_value(pv::hex_decode(values.at("chain_id")));
  const auto raw_count = std::stoull(values.at("raw_count"));
  for (std::size_t index = 0; index < raw_count; ++index) {
    const auto key = "raw" + std::to_string(index);
    const auto raw = pv::hex_decode(values.at(key));
    const auto admission = p::admit_transfer(raw, chain_id);
    const auto expected = std::stoull(values.at(key + ".admission"));
    if (expected == 0) {
      pv::require(std::holds_alternative<p::Transfer>(admission),
                  "expected admitted transfer");
    } else {
      pv::require(
          std::holds_alternative<p::AdmissionError>(admission) &&
              static_cast<std::uint8_t>(
                  std::get<p::AdmissionError>(admission)) == expected,
          "admission error mismatch");
    }
  }
}

int main(int argc, char** argv) {
  try {
    pv::require(argc == 2, "usage: kernel_admission_test VECTOR_FILE");
    pv::require(sodium_init() >= 0, "libsodium initialization");
    verify_admission_vectors(pv::load_values(argv[1]));
    std::cout << "Kernel admission vectors: passed\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "Kernel admission vectors: failed: " << error.what() << '\n';
    return 1;
  }
}
