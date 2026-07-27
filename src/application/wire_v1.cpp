#include "protocol/application/wire_v1.hpp"

#include "protocol/application/application_v1.hpp"

#include <algorithm>
#include <bit>
#include <iterator>
#include <limits>
#include <optional>
#include <utility>

namespace protocol::application {
namespace {

using protocol::v1::Bytes;

constexpr std::uint8_t kMagic[] = {'P', 'S', 'A', 'P'};
constexpr std::uint16_t kWireVersion = 1;
constexpr std::size_t kMaximumAppStateBytes = 4'096;

std::uint16_t read_u16(std::span<const std::uint8_t> bytes) noexcept {
  return static_cast<std::uint16_t>(
      (static_cast<std::uint16_t>(bytes[0]) << 8U) | bytes[1]);
}

std::uint32_t read_u32(std::span<const std::uint8_t> bytes) noexcept {
  std::uint32_t value = 0;
  for (const auto byte : bytes) value = (value << 8U) | byte;
  return value;
}

std::uint64_t read_u64(std::span<const std::uint8_t> bytes) noexcept {
  std::uint64_t value = 0;
  for (const auto byte : bytes) value = (value << 8U) | byte;
  return value;
}

void append_u16(Bytes& output, std::uint16_t value) {
  output.push_back(static_cast<std::uint8_t>(value >> 8U));
  output.push_back(static_cast<std::uint8_t>(value));
}

void append_u32(Bytes& output, std::uint32_t value) {
  for (int shift = 24; shift >= 0; shift -= 8) {
    output.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

void append_u64(Bytes& output, std::uint64_t value) {
  for (int shift = 56; shift >= 0; shift -= 8) {
    output.push_back(static_cast<std::uint8_t>(value >> shift));
  }
}

bool valid_kind(std::uint8_t raw) noexcept {
  return raw >= static_cast<std::uint8_t>(MessageKind::info) &&
         raw <= static_cast<std::uint8_t>(MessageKind::commit);
}

class Reader {
 public:
  explicit Reader(std::span<const std::uint8_t> bytes) : bytes_(bytes) {}

  std::optional<std::uint32_t> u32() noexcept {
    const auto value = take(4);
    if (!value) return std::nullopt;
    return read_u32(*value);
  }

  std::optional<std::uint64_t> u64() noexcept {
    const auto value = take(8);
    if (!value) return std::nullopt;
    return read_u64(*value);
  }

  std::optional<std::int64_t> i64() noexcept {
    const auto value = u64();
    if (!value) return std::nullopt;
    return std::bit_cast<std::int64_t>(*value);
  }

  std::optional<std::span<const std::uint8_t>> take(
      std::size_t count) noexcept {
    if (count > bytes_.size() - offset_) return std::nullopt;
    const auto result = bytes_.subspan(offset_, count);
    offset_ += count;
    return result;
  }

  std::variant<Bytes, WireError> blob(std::size_t maximum) {
    const auto length = u32();
    if (!length) return WireError::invalid_payload;
    if (*length > maximum) return WireError::resource_limit;
    const auto value = take(*length);
    if (!value) return WireError::invalid_payload;
    return Bytes(value->begin(), value->end());
  }

  bool finished() const noexcept { return offset_ == bytes_.size(); }

 private:
  std::span<const std::uint8_t> bytes_;
  std::size_t offset_{0};
};

std::variant<std::vector<Bytes>, WireError> read_transactions(
    Reader& reader) {
  const auto count = reader.u32();
  if (!count) return WireError::invalid_payload;
  if (*count > kMaximumBlockInputs) return WireError::resource_limit;

  std::vector<Bytes> transactions;
  transactions.reserve(*count);
  std::size_t total = 0;
  for (std::uint32_t index = 0; index < *count; ++index) {
    auto transaction = reader.blob(kMaximumTransactionBytes);
    if (std::holds_alternative<WireError>(transaction)) {
      return std::get<WireError>(transaction);
    }
    auto bytes = std::get<Bytes>(std::move(transaction));
    if (bytes.size() > kMaximumBlockBytes - total) {
      return WireError::resource_limit;
    }
    total += bytes.size();
    transactions.push_back(std::move(bytes));
  }
  return transactions;
}

RequestResult decode_payload(const Frame& frame) {
  Reader reader(frame.payload);
  RequestPayload payload;
  switch (frame.header.kind) {
    case MessageKind::info:
    case MessageKind::commit:
      payload = EmptyRequest{};
      break;
    case MessageKind::init_chain: {
      const auto raw_chain = reader.take(32);
      const auto height = reader.u64();
      auto app_state = reader.blob(kMaximumAppStateBytes);
      if (!raw_chain || !height ||
          std::holds_alternative<WireError>(app_state)) {
        return std::holds_alternative<WireError>(app_state)
                   ? std::get<WireError>(app_state)
                   : WireError::invalid_payload;
      }
      protocol::v1::Hash chain{};
      std::copy(raw_chain->begin(), raw_chain->end(), chain.begin());
      payload = InitChainRequest{
          protocol::v1::ChainId{chain}, *height,
          std::get<Bytes>(std::move(app_state))};
      break;
    }
    case MessageKind::check_transaction: {
      auto transaction = reader.blob(kMaximumTransactionBytes);
      if (std::holds_alternative<WireError>(transaction)) {
        return std::get<WireError>(transaction);
      }
      payload = CheckTransactionRequest{
          std::get<Bytes>(std::move(transaction))};
      break;
    }
    case MessageKind::prepare_proposal: {
      const auto maximum = reader.i64();
      auto transactions = read_transactions(reader);
      if (!maximum ||
          std::holds_alternative<WireError>(transactions)) {
        return std::holds_alternative<WireError>(transactions)
                   ? std::get<WireError>(transactions)
                   : WireError::invalid_payload;
      }
      payload = PrepareProposalRequest{
          *maximum,
          std::get<std::vector<Bytes>>(std::move(transactions))};
      break;
    }
    case MessageKind::process_proposal:
    case MessageKind::finalize_block: {
      const auto height = reader.u64();
      auto transactions = read_transactions(reader);
      if (!height ||
          std::holds_alternative<WireError>(transactions)) {
        return std::holds_alternative<WireError>(transactions)
                   ? std::get<WireError>(transactions)
                   : WireError::invalid_payload;
      }
      payload = BlockRequest{
          *height,
          std::get<std::vector<Bytes>>(std::move(transactions))};
      break;
    }
  }
  if (!reader.finished()) return WireError::invalid_payload;
  return DecodedRequest{
      frame.header.kind, frame.header.request_id, std::move(payload)};
}

}  // namespace

HeaderResult decode_frame_header(
    std::span<const std::uint8_t> header) noexcept {
  if (header.size() != kWireHeaderSize ||
      !std::equal(std::begin(kMagic), std::end(kMagic), header.begin())) {
    return WireError::invalid_frame;
  }
  if (read_u16(header.subspan(4, 2)) != kWireVersion) {
    return WireError::unsupported_version;
  }
  if (header[6] > static_cast<std::uint8_t>(WireDirection::response)) {
    return WireError::invalid_direction;
  }
  if (!valid_kind(header[7])) return WireError::unknown_kind;
  const auto request_id = read_u64(header.subspan(8, 8));
  if (request_id == 0) return WireError::invalid_request_id;
  const auto payload_size = read_u32(header.subspan(16, 4));
  if (payload_size > kMaximumWirePayload) {
    return WireError::resource_limit;
  }
  return FrameHeader{
      static_cast<WireDirection>(header[6]),
      static_cast<MessageKind>(header[7]),
      request_id,
      payload_size,
  };
}

FrameResult decode_frame(std::span<const std::uint8_t> bytes) {
  if (bytes.size() < kWireHeaderSize) return WireError::invalid_frame;
  auto decoded = decode_frame_header(bytes.first(kWireHeaderSize));
  if (!std::holds_alternative<FrameHeader>(decoded)) {
    return std::get<WireError>(decoded);
  }
  const auto header = std::get<FrameHeader>(decoded);
  if (bytes.size() != kWireHeaderSize + header.payload_size) {
    return WireError::invalid_frame;
  }
  return Frame{
      header,
      Bytes(bytes.begin() + kWireHeaderSize, bytes.end()),
  };
}

RequestResult decode_request_frame(
    std::span<const std::uint8_t> bytes) {
  auto decoded = decode_frame(bytes);
  if (!std::holds_alternative<Frame>(decoded)) {
    return std::get<WireError>(decoded);
  }
  auto frame = std::get<Frame>(std::move(decoded));
  if (frame.header.direction != WireDirection::request) {
    return WireError::invalid_direction;
  }
  return decode_payload(frame);
}

EncodedFrameResult encode_frame(const Frame& frame) {
  const auto raw_direction =
      static_cast<std::uint8_t>(frame.header.direction);
  const auto raw_kind = static_cast<std::uint8_t>(frame.header.kind);
  if (raw_direction >
          static_cast<std::uint8_t>(WireDirection::response) ||
      !valid_kind(raw_kind) || frame.header.request_id == 0 ||
      frame.header.payload_size != frame.payload.size()) {
    return WireError::invalid_frame;
  }
  if (frame.payload.size() > kMaximumWirePayload ||
      frame.payload.size() >
          std::numeric_limits<std::uint32_t>::max()) {
    return WireError::resource_limit;
  }

  Bytes encoded;
  encoded.reserve(kWireHeaderSize + frame.payload.size());
  encoded.insert(encoded.end(), std::begin(kMagic), std::end(kMagic));
  append_u16(encoded, kWireVersion);
  encoded.push_back(raw_direction);
  encoded.push_back(raw_kind);
  append_u64(encoded, frame.header.request_id);
  append_u32(
      encoded, static_cast<std::uint32_t>(frame.payload.size()));
  encoded.insert(
      encoded.end(), frame.payload.begin(), frame.payload.end());
  return encoded;
}

}  // namespace protocol::application
