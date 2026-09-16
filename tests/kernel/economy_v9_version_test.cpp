// The version-nine identity, the block header, genesis, and the result-code
// space, checked against the recorded vectors.
//
// **Three of the four subjects here are the compatibility boundary**, so almost
// every check is a comparison between two derived artifacts rather than an
// assertion about one. A label is a string and a string proves nothing on its
// own: what the vectors fix is that the digest version nine derives differs from
// the digest each predecessor derives over the same inputs, and each of the
// eight non-collisions is required separately because distinct labels are
// strings rather than a chain.
//
// Two figures are pinned against the files that accepted them rather than
// re-recorded under a version-nine name: version eight's 142-octet genesis
// prefix and its 146-octet header. Comparing them against the live version-eight
// kernel as well is what would catch a port that drifted in both directions at
// once.

#include "economy_v9_fixture.hpp"

#include "protocol/v8/economy.hpp"
#include "protocol/v8/ledger.hpp"

#include <algorithm>
#include <string>

namespace economy_v9_fixture {
namespace {

namespace v8 = protocol::v8;

// The fixture's roots, chosen to be distinguishable in a hex dump. Nothing
// derives them: the header is a byte layout, and what the vectors fix about it
// is where each field sits.
const v9::Hash kPreviousRoot = repeated(0xA0);
const v9::Hash kTransactionRoot = repeated(0xB0);
const v9::Hash kResultingRoot = repeated(0xC0);

v9::Bytes fixture_header(std::uint64_t timestamp) {
  const auto header =
      v9::block_header(ascending(0), kHeaderHeight, timestamp, kPreviousRoot,
                       kTransactionRoot, kResultingRoot, kHeaderTransactionCount);
  pv::require(header.has_value(), "the fixture header must encode");
  return *header;
}

void verify_identity(const pv::Values& values) {
  pv::require(expect_text(values, "identity.chain_id_label") == v9::kChainIdLabel,
              "the chain identity label is version nine's");
  pv::require(
      expect_text(values, "identity.state_root_label") == v9::kStateRootLabel,
      "the state root label is version nine's");
  pv::require(expect_text(values, "identity.economy_tree_prefix") ==
                  v9::kEconomyTreePrefix,
              "the economy tree prefix is version nine's");
  pv::require(expect_text(values, "identity.block_id_label") == v9::kBlockIdLabel,
              "the block identifier label is version nine's");

  pv::require(expect_number(values, "identity.genesis_schema_version") ==
                  v9::kGenesisSchemaVersion,
              "the genesis schema version is 9");
  pv::require(expect_number(values, "identity.state_root_schema_version") ==
                  v9::kStateRootSchemaVersion,
              "the state root schema version is 9");
  pv::require(expect_number(values, "identity.block_header_schema_version") ==
                  v9::kBlockHeaderSchemaVersion,
              "the block header schema version is 9");
  pv::require(
      expect_number(values, "identity.receipt_version") == v9::kReceiptVersion,
      "the receipt version is 9");

  // The inherited labels. Each names an artifact version nine does not change,
  // so each keeps the version that accepted it.
  pv::require(expect_text(values, "identity.carried_label.sign") == v9::kSignLabel,
              "the signing label is version one's");
  pv::require(expect_text(values, "identity.carried_label.transaction_id") ==
                  v9::kTransactionIdLabel,
              "the transaction identifier label is version one's");
  pv::require(
      expect_text(values, "identity.carried_label.challenge") == v9::kChallengeLabel,
      "the challenge label is version eight's");
  pv::require(
      expect_text(values, "identity.carried_label.dispute") == v9::kDisputeLabel,
      "the dispute label is version eight's");

  // **The mint-confirmation label is derived rather than declared**, because
  // this codec exposes no constant for it: the message builder is the only
  // statement of it, so the check reads the label out of a message the kernel
  // actually produced. A constant compared to itself would establish nothing
  // about the bytes a HUB signs.
  const auto recorded = expect_text(values, "identity.carried_label.mint_confirm");
  const auto message = v9::mint_message(ascending(0), repeated(0x31), 22, 7,
                                        repeated(0x9C), 4321);
  pv::require(!message.empty(), "the mint message must encode");
  pv::require(message[0] == static_cast<std::uint8_t>(recorded.size()),
              "the mint message opens with its length-prefixed domain label");
  pv::require(std::equal(recorded.begin(), recorded.end(), message.begin() + 1),
              "the mint message's label is the recorded one");
  expect_true(values, "identity.carried_label.mint_confirm_is_version_six");
  pv::require(recorded.rfind("protocol-stack:v6:", 0) == 0,
              "the mint confirmation label is version six's");
}

void verify_header(const pv::Values& values) {
  pv::require(expect_size(values, "header.bytes") == v9::kBlockHeaderBytes,
              "the header is 154 octets");
  pv::require(
      expect_size(values, "header.timestamp_offset") == v9::kBlockTimestampOffset,
      "the timestamp is inserted after the height");
  pv::require(expect_size(values, "header.grew_by") == v9::kTimestampBytes,
              "the header grew by one u64");

  // Pinned against the live version-eight kernel rather than against a figure
  // this file restates, so a port that moved both would fail here.
  pv::require(expect_size(values, "header.version_eight_bytes") ==
                  v8::kBlockHeaderBytes,
              "version eight's header is 146 octets");
  pv::require(v9::kBlockHeaderBytes == v8::kBlockHeaderBytes + v9::kTimestampBytes,
              "the growth is exactly the inserted field");

  const auto header = fixture_header(kGenesisMillis);
  pv::require(hex(header) == expect_text(values, "header.bytes_encoded"),
              "the encoded header is the recorded one");
  pv::require(expect_size(values, "header.encoded_length") == header.size(),
              "the encoded header is its declared width");
  // Read back out of the encoded bytes rather than compared to the input, so the
  // offset is checked against the encoding and not against the constant beside
  // it.
  pv::require(pv::read_u64(pv::Bytes(header.begin(), header.end()),
                           v9::kBlockTimestampOffset) == kGenesisMillis,
              "the timestamp sits at its recorded offset");
  expect_true(values, "header.timestamp_field");

  const auto identifier = v9::block_id(header);
  pv::require(identifier.has_value(), "a whole header has an identifier");
  pv::require(hex(*identifier) == expect_text(values, "header.block_id"),
              "the block identifier is the recorded one");

  // A version-nine header is 154 octets and version one's is 146, so no earlier
  // identifier can be taken over these bytes at all. The comparison is made
  // anyway, because a label is a string and the non-collision is about digests.
  const auto predecessor = v9::predecessor_block_id(header);
  pv::require(predecessor.has_value(), "the comparison needs both digests");
  pv::require(*predecessor != *identifier,
              "no version-one block identifier collides with version nine's");
  expect_true(values, "header.block_id_differs_from_version_ones");

  pv::require(!v9::block_id(std::span<const std::uint8_t>(header.data(),
                                                          header.size() - 1)),
              "an identifier is taken over a whole header or not at all");
  pv::require(!v9::block_header(ascending(0), kHeaderHeight,
                                v9::kMaxTimestampMillis + 1, kPreviousRoot,
                                kTransactionRoot, kResultingRoot,
                                kHeaderTransactionCount),
              "a header carrying a timestamp outside the range is refused");
  expect_true(values, "header.refuses_a_timestamp_outside_the_range");
}

void verify_genesis(const pv::Values& values, const pv::Values& carried_eight,
                    const pv::Values& manifest) {
  // The manifest digest is a founder-directed figure, so it is read from the
  // accepted manifest file rather than restated here.
  const auto digest = from_hex(manifest.at("manifest_digest"));
  const auto genesis = fixture_genesis(digest);

  pv::require(expect_size(values, "genesis.prefix_bytes") == v9::kGenesisPrefixBytes,
              "the genesis prefix is 150 octets");
  pv::require(expect_size(values, "genesis.timestamp_offset") == 10,
              "the genesis timestamp follows the network identifier");
  // Two sources for version eight's prefix: the file that accepted it and the
  // kernel still compiling it.
  pv::require(expect_size(values, "genesis.version_eight_prefix_bytes") ==
                  std::stoull(carried_eight.at("genesis.prefix_bytes")),
              "version eight's prefix is the one its own file recorded");
  pv::require(expect_size(values, "genesis.version_eight_prefix_bytes") ==
                  v8::kGenesisPrefixBytes,
              "version eight's prefix is the one its kernel still uses");
  pv::require(v9::kGenesisPrefixBytes ==
                  v8::kGenesisPrefixBytes + v9::kGenesisTimestampBytes,
              "the prefix grew by exactly the inserted field");

  pv::require(
      expect_size(values, "genesis.max_accounts") == v9::kMaxGenesisAccounts,
      "the account bound is 21,842");
  pv::require(v9::kMaxGenesisAccounts ==
                  std::stoull(carried_eight.at("genesis.max_accounts")),
              "the wider prefix leaves the account bound where it was");
  expect_true(values, "genesis.max_accounts_unchanged_from_version_eight");
  pv::require(expect_size(values, "genesis.economy_entry_count") ==
                  v9::kGenesisEconomyEntries,
              "genesis writes sixteen economy entries");

  const auto encoded = v9::encode_genesis(genesis);
  pv::require(encoded.has_value(), "the fixture genesis must encode");
  pv::require(hex(*encoded) == expect_text(values, "genesis.bytes"),
              "the encoded genesis is the recorded one");
  pv::require(expect_size(values, "genesis.encoded_bytes") == encoded->size(),
              "the encoded genesis is its declared width");
  pv::require(expect_number(values, "genesis.timestamp_field") == kGenesisMillis,
              "the recorded genesis carries the fixture's timestamp");
  pv::require(pv::read_u64(pv::Bytes(encoded->begin(), encoded->end()), 10) ==
                  kGenesisMillis,
              "the genesis timestamp sits at its recorded offset");

  // The round trip is the whole validity rule: a decoded genesis is returned
  // only when re-encoding it reproduces the input octet for octet.
  const auto decoded = v9::decode_genesis(*encoded);
  pv::require(decoded.has_value(), "the encoded genesis must decode");
  pv::require(decoded->genesis_timestamp == kGenesisMillis,
              "the decoder reads the timestamp back");

  const auto identity = v9::chain_id(genesis);
  pv::require(identity.has_value(), "the fixture genesis has an identity");
  pv::require(hex(*identity) == expect_text(values, "genesis.chain_id"),
              "the chain identity is the recorded one");

  const auto month = v9::month_index(kGenesisMillis);
  pv::require(month.has_value(), "the genesis timestamp has a month");
  pv::require(expect_number(values, "genesis.month") == *month,
              "the genesis month is the recorded one");

  for (std::uint16_t version = 2; version <= 8; ++version) {
    const auto predecessor = v9::predecessor_chain_id(genesis, version);
    pv::require(predecessor.has_value(),
                "each predecessor identity must be derivable");
    pv::require(*predecessor != *identity,
                "no predecessor chain identity collides with version nine's");
    expect_true(values,
                "genesis.chain_id_differs_from_v" + std::to_string(version));
  }
  // The comparison is against the identity version eight's own file recorded,
  // rather than only against one this kernel derived: both ends of the range are
  // pinned to an accepted artifact.
  const auto version_eight = v9::predecessor_chain_id(genesis, 8);
  pv::require(hex(*version_eight) != carried_eight.at("genesis.chain_id"),
              "version eight's recorded identity is over its own 142 octets, "
              "which these 150 are not");

  auto above_range = genesis;
  above_range.genesis_timestamp = v9::kMaxTimestampMillis + 1;
  pv::require(!v9::encode_genesis(above_range),
              "a genesis timestamp above the range is malformed");
  pv::require(!v9::chain_id(above_range),
              "a malformed genesis has no chain identity");
  expect_true(values, "genesis.refuses_a_timestamp_above_the_range");

  // `genesis.refuses_a_timestamp_below_the_range` is deliberately not consulted:
  // see the unrepresentable set in the coverage guard.

  const auto entries = genesis_economy(*month);
  pv::require(expect_size(values, "genesis.entry_count") == entries.size(),
              "the fixture writes the recorded number of entries");

  const auto find = [&entries](const v9::Bytes& key) {
    const auto found = std::find_if(
        entries.begin(), entries.end(),
        [&key](const v9::EconomyEntry& entry) { return entry.key == key; });
    pv::require(found != entries.end(), "genesis writes the entry");
    return found->value;
  };
  pv::require(hex(find(v9::settlement_cursor_key())) ==
                  expect_text(values, "genesis.cursor_value"),
              "the cursor starts at the genesis month");
  pv::require(hex(find(v9::window_month_key(0))) ==
                  expect_text(values, "genesis.window_zero_month_value"),
              "window zero's month is the genesis month");
  pv::require(hex(find(v9::unreferred_pool_key())) ==
                  expect_text(values, "genesis.pool_value"),
              "the pool starts with all three quantities zero");

  // The thirteen entries version nine does not touch are version eight's, byte
  // for byte, under keys whose discriminators did not move. The comparison is
  // against the version-eight kernel's own encoders rather than against a
  // restatement of them.
  std::size_t carried = 0;
  for (const auto& entry : entries) {
    const auto kind = entry.key.front();
    if (kind == static_cast<std::uint8_t>(v9::Entry::unreferred_pool) ||
        kind == static_cast<std::uint8_t>(v9::Entry::window_month) ||
        kind == static_cast<std::uint8_t>(v9::Entry::settlement_cursor)) {
      continue;
    }
    ++carried;
    v8::Bytes expected_value;
    v8::Bytes expected_key;
    if (kind == static_cast<std::uint8_t>(v9::Entry::channel)) {
      expected_key = v8::channel_key(entry.key.at(1));
      expected_value = v8::channel_value(0, 0);
    } else if (kind == static_cast<std::uint8_t>(v9::Entry::recovery_pool)) {
      expected_key = v8::recovery_pool_key();
      expected_value = v8::recovery_pool_value({});
    } else if (kind == static_cast<std::uint8_t>(v9::Entry::verifier_key)) {
      expected_key = v8::verifier_key_key();
      expected_value = v8::verifier_key_value(kVerifierKey);
    } else {
      pv::require(kind == static_cast<std::uint8_t>(v9::Entry::verified_user_counter),
                  "no other carried entry kind appears at genesis");
      expected_key = v8::verified_user_counter_key();
      expected_value = v8::verified_user_counter_value(0);
    }
    pv::require(entry.key == expected_key && entry.value == expected_value,
                "a carried genesis entry is version eight's unchanged");
  }
  pv::require(carried == 13, "thirteen genesis entries are carried");
  expect_true(values, "genesis.thirteen_entries_are_version_eights_unchanged");
}

// The state root, its eight non-collisions, and the field that makes it a new
// root rather than a relabelled one.
//
// **The far end of the range is pinned to an accepted artifact.** Version
// eight's own file records the root of an empty state under its chain identity,
// and this kernel's predecessor construction must reproduce it exactly. Without
// that pin, a construction that wrote version nine's schema version into all
// eight preimages would still satisfy every inequality below, because the eight
// labels would still differ from each other — which is the defect the
// version-eight port found by mutation and recorded.
void verify_roots(const pv::Values& values, const pv::Values& carried_eight,
                  const pv::Values& manifest) {
  const auto supply_limit = std::stoull(manifest.at("denomination.maximum_supply_atomic"));
  const auto digest = from_hex(manifest.at("manifest_digest"));
  const auto genesis = fixture_genesis(digest);
  const auto identity = v9::chain_id(genesis);
  pv::require(identity.has_value(), "the fixture genesis has an identity");

  v9::StateSummary summary;
  summary.chain_id = *identity;
  summary.height = kRootHeight;
  summary.timestamp = kGenesisMillis;
  summary.supply_limit = supply_limit;

  const auto mine = v9::state_root(summary, {}, {});
  pv::require(mine.has_value(), "an empty state has a root");
  pv::require(hex(*mine) == expect_text(values, "root.version_nine"),
              "the version-nine root is the recorded one");

  for (std::uint16_t version = 1; version <= 8; ++version) {
    const auto earlier = v9::predecessor_state_root(version, summary, {}, {});
    pv::require(earlier.has_value(), "each predecessor root is derivable");
    pv::require(hex(*earlier) ==
                    expect_text(values, "root.v" + std::to_string(version)),
                "the predecessor root is the recorded one");
    pv::require(*earlier != *mine,
                "no predecessor root collides with version nine's");
    expect_true(values, "root.differs_from_v" + std::to_string(version));
  }
  pv::require(!v9::predecessor_state_root(9, summary, {}, {}),
              "version nine is not its own predecessor");

  // Version eight's accepted root, reproduced under its own chain identity.
  v9::StateSummary version_eight = summary;
  version_eight.chain_id = from_hex(carried_eight.at("genesis.chain_id"));
  const auto reproduced = v9::predecessor_state_root(8, version_eight, {}, {});
  pv::require(reproduced.has_value(), "the pinned root is derivable");
  pv::require(hex(*reproduced) == carried_eight.at("root.version_eight"),
              "this kernel reproduces version eight's own recorded root");
  expect_true(values, "root.version_eight_reproduces_its_accepted_root");

  // Two states differing in nothing but the timestamp. Without this the root
  // could ignore the field entirely and every check above would still pass,
  // because they all hold one timestamp.
  auto later = summary;
  later.timestamp = kGenesisMillis + 1;
  const auto moved = v9::state_root(later, {}, {});
  pv::require(moved.has_value(), "the later state has a root");
  pv::require(hex(*moved) == expect_text(values, "root.one_milli_later"),
              "the root one millisecond later is the recorded one");
  pv::require(*moved != *mine, "the root commits to the timestamp");
  expect_true(values, "root.the_timestamp_is_in_the_preimage");

  // `state_root` is *defined* through the frame, so the fast path a run of quiet
  // heights takes cannot drift from the root it stands in for. Checked rather
  // than asserted, at two timestamps, because a frame that dropped the field
  // would agree at one.
  const auto frame = v9::state_root_frame(summary, {}, {});
  pv::require(frame.has_value(), "the frame is derivable");
  const auto through_frame =
      v9::state_root_from_frame(*frame, summary.height, summary.timestamp);
  const auto through_frame_later =
      v9::state_root_from_frame(*frame, later.height, later.timestamp);
  pv::require(through_frame.has_value() && *through_frame == *mine,
              "the frame reaches the root it stands in for");
  pv::require(through_frame_later.has_value() && *through_frame_later == *moved,
              "the frame moves with the timestamp");
  pv::require(!v9::state_root_from_frame(*frame, summary.height,
                                         v9::kMaxTimestampMillis + 1),
              "no root is taken over a timestamp C1 would refuse");
  auto out_of_range = summary;
  out_of_range.timestamp = v9::kMaxTimestampMillis + 1;
  pv::require(!v9::state_root(out_of_range, {}, {}),
              "and the ordinary path refuses it too");
}

void verify_codes(const pv::Values& values, const pv::Values& carried_eight) {
  pv::require(expect_number(values, "codes.count") == v9::kResultCodeCount,
              "the result code space is 45");
  // Version eight's own file does not record the count, so the comparison is
  // against the kernel that still compiles it: version nine adds none, and the
  // claim is about two implementations rather than two copies of one number.
  pv::require(v9::kResultCodeCount == v8::kResultCodeCount,
              "version nine adds no result code");
  expect_true(values, "codes.unchanged_from_version_eight");
  for (std::uint8_t code = 0; code < v9::kResultCodeCount; ++code) {
    const auto here = v9::result_code_name(code);
    const auto there = v8::result_code_name(code);
    pv::require(here.has_value() && there.has_value() && *here == *there,
                "every code keeps its exact version-eight meaning");
  }
  pv::require(!v9::result_code_name(v9::kResultCodeCount),
              "the space is contiguous and ends where it says");
  (void)carried_eight;

  // Kind 22's nine refusals, each already assigned by an accepted version. The
  // vectors fix the number, and this requires the kernel's own table to give
  // that number the recorded name — a check against the ladder rather than
  // against the list beside it.
  const auto named = [&values](const std::string& key, std::string_view name) {
    const auto code = static_cast<std::uint8_t>(expect_number(values, key));
    const auto found = v9::result_code_name(code);
    pv::require(found.has_value() && *found == name,
                "code " + std::to_string(code) + " is " + std::string(name));
  };
  named("codes.kind22.cycle_range", "CYCLE_RANGE");
  named("codes.kind22.seat_not_purchased", "SEAT_NOT_PURCHASED");
  named("codes.kind22.seat_not_activated", "SEAT_NOT_ACTIVATED");
  named("codes.kind22.unauthorized", "UNAUTHORIZED");
  named("codes.kind22.escrow_not_found", "ESCROW_NOT_FOUND");
  named("codes.kind22.escrow_not_owned", "ESCROW_NOT_OWNED");
  named("codes.kind22.nothing_to_mint", "NOTHING_TO_MINT");
  named("codes.kind22.biometric_required", "BIOMETRIC_REQUIRED");
  named("codes.kind22.channel_cap", "CHANNEL_CAP");

  // **None of the five timestamp conditions is a result code**, and that is
  // checked against the two spaces rather than asserted: every condition name
  // this kernel can report is required to be absent from the result table.
  const auto recorded = expect_text(values, "codes.timestamp_conditions");
  std::size_t present = 0;
  for (std::uint8_t ordinal = 1; ordinal < v9::kTimestampConditionCount;
       ++ordinal) {
    const auto name =
        v9::timestamp_condition_name(static_cast<v9::TimestampCondition>(ordinal));
    pv::require(!name.empty(), "every condition has a name");
    pv::require(recorded.find(name) != std::string::npos,
                "the recorded tuple names " + std::string(name));
    ++present;
    for (std::uint8_t code = 0; code < v9::kResultCodeCount; ++code) {
      pv::require(v9::result_code_name(code) != name,
                  "a timestamp condition is not a result code");
    }
  }
  pv::require(present == 5, "the five conditions are all reached");
  expect_true(values, "codes.no_timestamp_condition_is_a_result_code");
}

}  // namespace

void verify_accounts_tree(const pv::Values& primitives) {
  const auto accounts = accepted_accounts(primitives);
  pv::require(hex(v9::accounts_root(accounts)) ==
                  primitives.at("state.accounts_tree_root"),
              "the ported tree reproduces the accepted M1 accounts tree root");
  pv::require(hex(v9::accounts_root({})) == primitives.at("state.empty_tree_root"),
              "the ported tree reproduces the accepted M1 empty tree root");
}

void verify_version(const pv::Values& values, const pv::Values& carried_eight,
                    const pv::Values& manifest, const pv::Values& primitives) {
  verify_identity(values);
  verify_header(values);
  verify_genesis(values, carried_eight, manifest);
  verify_roots(values, carried_eight, manifest);
  verify_codes(values, carried_eight);
  (void)primitives;
}

}  // namespace economy_v9_fixture
