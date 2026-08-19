// The inherited constructions, the genesis, the compatibility boundary, the
// three derived execution rules, the founder-directed tables, and determinism.
//
// Four checks here reach a *third* source rather than a second opinion of the
// execution vectors, and each is a construction version six inherits or a figure
// it is told: the ordered transaction tree and the accepted transfer against
// `protocol-primitives-v1.txt`, the block header and block identifier against
// `ledger-transition-v1.txt`, the ten channel caps and five base-permission legs
// against `founder-economy-manifest-v2.txt`, and the referral leg against
// `economy-transition-v3.txt`. Without those, a restated construction that had
// drifted would agree only with itself.

#include "economy_v6_execution_fixture.hpp"

#include "protocol/v1/crypto.hpp"

namespace economy_v6_execution {
namespace {

Hash to_hash(const Bytes& bytes) {
  pv::require(bytes.size() == 32, "expected a 32-octet value");
  Hash value{};
  std::copy(bytes.begin(), bytes.end(), value.begin());
  return value;
}

void check_constructions(const pv::Values& values, const pv::Values& primitives,
                         const pv::Values& ledger_vectors) {
  agree(values, "construction.transaction_tree_prefix",
        std::string(v6::kTransactionTreePrefix));
  std::vector<Hash> items;
  for (int index = 0; index < 3; ++index) {
    items.push_back(to_hash(
        pv::hex_decode(expect_text(primitives, "tx.item" + std::to_string(index)))));
  }
  const auto derived_root = v6::transaction_root(items);
  agree(values, "construction.transaction_root_over_the_accepted_items",
        hex(derived_root));
  pv::require(hex(derived_root) == expect_text(primitives, "tx.root"),
              "the transaction tree must reproduce the accepted root");
  expect_true(values, "construction.transaction_root_reproduces_the_accepted_vector");

  const auto empty_root = v6::transaction_root({});
  agree(values, "construction.empty_transaction_root", hex(empty_root));
  pv::require(hex(empty_root) == expect_text(primitives, "tx.empty_root"),
              "the empty transaction tree must reproduce the accepted root");
  expect_true(values, "construction.empty_transaction_root_reproduces_the_accepted_vector");

  // The accepted version-one header, field for field out of the recorded bytes,
  // so a restatement that had drifted fails against the file that fixes it.
  const auto recorded = pv::hex_decode(expect_text(ledger_vectors, "block_header"));
  pv::require(recorded.size() == v6::kBlockHeaderBytes,
              "the accepted header is 146 octets");
  Octets32 chain_id{};
  std::copy(recorded.begin() + 6, recorded.begin() + 38, chain_id.begin());
  std::uint64_t height = 0;
  for (std::size_t index = 38; index < 46; ++index) {
    height = (height << 8U) | recorded[index];
  }
  std::uint32_t count = 0;
  for (std::size_t index = 142; index < 146; ++index) {
    count = (count << 8U) | recorded[index];
  }
  const auto header = v6::block_header(
      chain_id, height,
      to_hash(pv::hex_decode(expect_text(ledger_vectors, "previous_state_root"))),
      to_hash(pv::hex_decode(expect_text(ledger_vectors, "transaction_root"))),
      to_hash(pv::hex_decode(expect_text(ledger_vectors, "resulting_state_root"))),
      count);
  pv::require(header.has_value(), "the accepted fields must encode a header");
  agree(values, "construction.block_header_over_the_accepted_fields", hex(*header));
  pv::require(*header == recorded, "the header must reproduce the accepted bytes");
  expect_true(values, "construction.block_header_reproduces_the_accepted_version_one_header");
  const auto block_id = protocol::v1::hash(v6::kBlockIdLabel, *header);
  pv::require(hex(block_id) == expect_text(ledger_vectors, "block_id"),
              "the block identifier must reproduce the accepted value");
  expect_true(values, "construction.block_id_reproduces_the_accepted_version_one_block_id");
  agree(values, "construction.block_header_bytes", v6::kBlockHeaderBytes);
  agree(values, "construction.block_header_schema_version",
        static_cast<std::uint64_t>(v6::kBlockHeaderSchemaVersion));
}

void check_genesis(const pv::Values& values) {
  const auto genesis = trace_genesis();
  const auto encoded = v6::encode_genesis(genesis);
  pv::require(encoded.has_value(), "the trace genesis must encode");
  agree(values, "genesis.bytes", hex(*encoded));
  const auto identity = v6::chain_id(genesis);
  pv::require(identity.has_value(), "the trace genesis must have a chain identity");
  agree(values, "genesis.chain_id", hex(*identity));
  agree(values, "genesis.fixed_fee", genesis.fixed_transfer_fee);

  const auto daily = v6::verified_user_daily_atomic();
  pv::require(daily.has_value(), "the verified-user rate must divide exactly");
  agree(values, "genesis.entry_airdrop_atomic", *daily);
  agree(values, "genesis.economy_entries",
        v6::economy_entries(open_trace_ledger()).size());
  // Version two derived that a conforming chain must permit a zero fee, because
  // a zero allocation and a nonzero fee leave nobody able to pay for the first
  // transaction. Registration is fee-exempt and pays the airdrop, so version six
  // is the first contract under which a nonzero fee is reachable from genesis.
  pv::require(genesis.fixed_transfer_fee > 0 && genesis.total_supply == 0 &&
                  genesis.account_count == 0 && *daily > genesis.fixed_transfer_fee,
              "a nonzero fixed fee must be reachable from a version-six genesis");
  expect_true(values, "genesis.a_nonzero_fixed_fee_is_reachable_from_a_version_six_genesis");
}

// The founder-directed figures the kernel carries, each against the accepted
// file that fixes it rather than against the kernel's own table.
void check_tables(const pv::Values& manifest, const pv::Values& version_three) {
  static constexpr std::array<const char*, 10> kChannelNames{
      "founder_operator",
      "venture_escrow",
      "community_grants_escrow",
      "developer_incentives_escrow",
      "system_creator_issuance_royalty",
      "liquidity_mining",
      "impermanent_loss_protection",
      "founder_referral",
      "hub_verified_user_incentives",
      "initial_mystery_box_incentives",
  };
  pv::require(expect_number(manifest, "channels.count") == kChannelNames.size(),
              "the manifest records ten channels");
  for (std::uint8_t index = 0; index < kChannelNames.size(); ++index) {
    const auto key = "channel" + std::to_string(index);
    pv::require(expect_text(manifest, key + ".id") == kChannelNames[index],
                "channel " + std::to_string(index) + " has the recorded identifier");
    pv::require(v6::channel_cap(index) == expect_number(manifest, key + ".cap"),
                "channel " + std::to_string(index) + " carries the recorded cap");
    const auto leg_key = std::string("base_permission.") + kChannelNames[index];
    const auto recorded =
        manifest.count(leg_key) == 0 ? 0 : expect_number(manifest, leg_key);
    pv::require(v6::base_permission_leg(index) == recorded,
                "channel " + std::to_string(index) + " carries the recorded leg");
  }
  pv::require(v6::channel_cap(v6::kVerifiedUserChannel) ==
                  v6::kVerifiedUserChannelCapAtomic,
              "the verified-user cap is the one the codec already declared");
  pv::require(v6::kReferralLegAtomic == expect_number(version_three, "referral.leg_atomic"),
              "the referral leg is the recorded version-three figure");
}

// The escrow with the `u64` maximum balance is stamped rather than reached: no
// conserved chain holds it, and that is the point. Even given a balance nothing
// can exceed, `amount + fee` still does not fit, so the code that reports it must
// be returned before the balance comparison or it is returned never.
std::string overflowing_debit_result() {
  v6::Ledger ledger;
  ledger.supply_limit = kSupplyLimit;
  ledger.fixed_fee = kFixedFee;
  const auto escrow = v6::escrow_id(kAliceIdentity, 0);
  v6::HubIdentityRecord identity;
  identity.hub_public_key = kAliceKey;
  ledger.registry.identities[kAliceIdentity] = identity;
  v6::EscrowRecord record;
  record.owner_hub_identity = kAliceIdentity;
  record.signer_count = 1;
  ledger.registry.escrows[escrow] = record;
  ledger.registry.signers[v6::signer_id(kAliceSignerKey)] = escrow;
  ledger.registry.accounts[escrow] = v6::Account{~std::uint64_t{0}, 0};

  v6::Envelope envelope;
  envelope.kind = static_cast<std::uint8_t>(v6::Kind::native_transfer);
  envelope.scheme = v6::kSchemeSigner;
  envelope.authority_public_key = kAliceSignerKey;
  envelope.nonce = 1;
  v6::Body body;
  body.recipient_escrow_id = escrow;
  body.amount_atomic = ~std::uint64_t{0};
  envelope.body = v6::encode_body(envelope.kind, body);
  envelope.fee_limit = kFixedFee;
  envelope.valid_until_height = 1;

  const auto outcome = v6::execute(ledger, envelope, Signatures{}.verifier());
  pv::require(outcome.has_value(), "an overflowing debit is a result, not a failure");
  const auto name = v6::result_code_name(static_cast<std::uint8_t>(outcome->result));
  pv::require(name.has_value(), "the result is inside the code space");
  return std::string(*name);
}

void check_derived_rules(const pv::Values& values) {
  // 1. `DEBIT_OVERFLOW` is returned at envelope check 8. Under the literal
  //    "envelope checks, then the kind's own conditions" order it would be
  //    unreachable, because no balance can reach the amount an overflowing debit
  //    needs — and the specification lists exactly three unreachable frozen
  //    codes and does not list this one.
  const auto overflow_amount = ~std::uint64_t{0} - kFixedFee + 1;
  agree(values, "derived.overflow_amount_atomic", overflow_amount);
  pv::require(overflow_amount > kSupplyLimit,
              "an overflowing debit exceeds any reachable balance");
  expect_true(values, "derived.an_overflowing_debit_exceeds_any_reachable_balance");
  agree(values, "derived.overflowing_debit_result", overflowing_debit_result());
  pv::require(overflowing_debit_result() == "DEBIT_OVERFLOW",
              "an overflowing debit is refused at envelope check eight");
  expect_true(values, "derived.debit_overflow_is_returned_at_envelope_check_eight");

  // 2. The zero-confirmation-field rule cannot be an admission rule and cannot
  //    return the code the specification names.
  for (std::uint8_t code = 0; code < v6::kResultCodeCount; ++code) {
    const auto name = v6::result_code_name(code);
    pv::require(name.has_value() && *name != "MALFORMED_TRANSACTION",
                "the result code space has no MALFORMED_TRANSACTION");
  }
  expect_true(values, "derived.the_result_code_space_has_no_malformed_transaction");
  pv::require(static_cast<std::uint8_t>(v6::AdmissionError::malformed_transaction) ==
                      1 &&
                  v6::result_code_name(1) == "ZERO_AMOUNT",
              "admission code one and result code one are different names");
  expect_true(values, "derived.admission_code_one_and_result_code_one_are_different_names");
  // The rule is observable only through a transition, because the predicate it
  // guards is over a stored posture: a tightening carrying a confirmation field
  // nothing asked for is refused with `UNAUTHORIZED`.
  pv::require(expect_text(values, "posture.tighten_signed.result") == "UNAUTHORIZED",
              "an unrequested confirmation is refused with UNAUTHORIZED");
  expect_true(values, "derived.an_unrequested_confirmation_is_refused_with_unauthorized");

  // 3. `NOTHING_TO_MINT` is the empty walk range. A seat activated in window `w`
  //    holds mark `w` while the last assigned window is `w - 2`, so the literal
  //    "already equal" reading would let the mint lower the mark.
  const auto mark = v6::window_of_height(kActivationHeight);
  const auto last = v6::last_assigned_window(kActivationHeight);
  pv::require(last.has_value(), "the activation height has an assigned window");
  agree(values, "derived.mark_at_activation", mark);
  agree(values, "derived.last_assigned_window_at_activation", *last);
  pv::require(mark > *last, "a fresh mark exceeds the last assigned window");
  expect_true(values, "derived.a_fresh_mark_exceeds_the_last_assigned_window");
  pv::require(!v6::walk_range(mark, last).has_value() &&
                  v6::walk_range(*last - 1, last).has_value(),
              "NOTHING_TO_MINT is the empty walk range");
  expect_true(values, "derived.nothing_to_mint_is_the_empty_walk_range");
}

// A version-six escrow identifier is a digest of an identity and an index, so
// reaching the accepted recipient would be a SHA-256 preimage: the accepted
// transfer is refused on every conforming chain rather than only on this fixture.
void check_compatibility(const pv::Values& values, const pv::Values& primitives) {
  Signatures signatures;
  const auto scenario = compatibility_scenario(signatures, primitives);
  const auto& accepted = scenario.blocks[1];
  pv::require(accepted.executed.size() == 1, "the accepted transfer is one block");

  bool reachable = false;
  for (const auto& identity :
       {kAliceIdentity, kBobIdentity, kCarolIdentity, kMariaIdentity, kDaveIdentity,
        kAcceptedIdentity}) {
    for (std::uint32_t index = 0; index < 1'024; ++index) {
      reachable = reachable || v6::escrow_id(identity, index) == kAcceptedRecipient;
    }
  }
  pv::require(!reachable,
              "the accepted recipient is no escrow of any fixture identity");
  expect_true(values, "compatibility.the_accepted_recipient_is_no_escrow_of_any_fixture_identity");

  const auto signed_transaction = expect_text(values, "compatibility.signed_transaction");
  pv::require(signed_transaction == expect_text(primitives, "signed_tx"),
              "the executed bytes are the accepted signed transfer");
  expect_true(values, "compatibility.signed_transaction_is_the_accepted_one");
  pv::require(expect_text(values, "compatibility.unsigned_transaction") ==
                  expect_text(primitives, "unsigned_tx"),
              "the executed unsigned bytes are the accepted ones");
  expect_true(values, "compatibility.unsigned_transaction_is_the_accepted_one");
  const auto derived_id = v6::transaction_id(pv::hex_decode(signed_transaction));
  agree(values, "compatibility.transaction_id", hex(derived_id));
  pv::require(hex(derived_id) == expect_text(primitives, "tx_id"),
              "the transaction identifier is the accepted one");
  expect_true(values, "compatibility.transaction_id_is_the_accepted_one");
  pv::require(hex(accepted.executed[0].transaction_id) == expect_text(primitives, "tx_id"),
              "the executed transaction carries the accepted identifier");
  expect_true(values, "compatibility.byte_identity_is_preserved_and_execution_identity_is_not");

  // The comparison the founder answer produced. Renumbering the nonce and
  // replacing the recipient are the only two edits, and they are separable: the
  // second moves exactly the 32 octets of the recipient field and nothing else.
  const auto unsigned_of = [&](const Octets32& recipient, std::uint64_t nonce) {
    v6::Envelope envelope;
    envelope.kind = static_cast<std::uint8_t>(v6::Kind::native_transfer);
    envelope.chain_id = kAcceptedChainId;
    envelope.scheme = v6::kSchemeSigner;
    envelope.authority_public_key =
        from_hex(expect_text(primitives, "rfc8032.public_key"));
    envelope.nonce = nonce;
    v6::Body body;
    body.recipient_escrow_id = recipient;
    body.amount_atomic = kAcceptedAmount;
    envelope.body = v6::encode_body(envelope.kind, body);
    envelope.fee_limit = kAcceptedFeeLimit;
    envelope.valid_until_height = kAcceptedValidUntil;
    return v6::encode_unsigned(envelope);
  };
  const auto accepted_unsigned = unsigned_of(kAcceptedRecipient, kAcceptedNonce);
  const auto renonced = unsigned_of(kAcceptedRecipient, 2);
  const auto rerouted = unsigned_of(v6::escrow_id(kBobIdentity, 0), 2);
  const auto differing = [](const Bytes& left, const Bytes& right) {
    pv::require(left.size() == right.size(), "compared bytes have one width");
    std::size_t count = 0;
    for (std::size_t index = 0; index < left.size(); ++index) {
      if (left[index] != right[index]) ++count;
    }
    return count;
  };
  agree(values, "compatibility.renonced_differs_from_the_accepted_bytes_in_octets",
        differing(accepted_unsigned, renonced));
  agree(values, "compatibility.rerouted_differs_from_the_renonced_bytes_in_octets",
        differing(renonced, rerouted));
  std::size_t first = renonced.size();
  std::size_t last = 0;
  for (std::size_t index = 0; index < renonced.size(); ++index) {
    if (renonced[index] == rerouted[index]) continue;
    first = std::min(first, index);
    last = index + 1;
  }
  pv::require(first == v6::kHeaderBytes && last == v6::kHeaderBytes + 32,
              "the only field that moved is the recipient");
  expect_true(values, "compatibility.the_only_field_that_moved_is_the_recipient");
}

// Replaying every scenario reproduces every commitment it recorded. The file
// counts one scenario this kernel does not execute — the boundary block, whose
// four seat transitions read a cycle assignment — so the count is compared
// against the recorded figure less exactly that one.
void check_determinism(const pv::Values& values, const pv::Values& primitives) {
  const auto replay = [&primitives](int index) {
    Signatures signatures;
    switch (index) {
      case 0: return registration_scenario(signatures);
      case 1: return millionth_scenario(signatures);
      case 2: return recovery_scenario(signatures);
      case 3: return compatibility_scenario(signatures, primitives);
      default: return posture_scenario(signatures);
    }
  };
  bool roots_match = true;
  bool receipts_match = true;
  int replayed = 0;
  for (int index = 0; index < 5; ++index) {
    const auto first = replay(index);
    const auto second = replay(index);
    pv::require(first.blocks.size() == second.blocks.size(),
                "a replay executes the same blocks");
    for (std::size_t block = 0; block < first.blocks.size(); ++block) {
      const auto& left = first.blocks[block];
      const auto& right = second.blocks[block];
      roots_match = roots_match && left.resulting_state_root == right.resulting_state_root;
      roots_match = roots_match && left.block_id == right.block_id;
      receipts_match = receipts_match && left.executed.size() == right.executed.size();
      for (std::size_t position = 0; position < left.executed.size(); ++position) {
        receipts_match = receipts_match && v6::encode_receipt(left.executed[position].receipt) ==
                                               v6::encode_receipt(right.executed[position].receipt);
      }
    }
    ++replayed;
  }
  pv::require(roots_match, "every replayed block must commit the same root");
  expect_true(values, "determinism.every_replayed_block_commits_the_same_root");
  pv::require(receipts_match, "every replayed block must emit the same receipts");
  expect_true(values, "determinism.every_replayed_block_emits_the_same_receipts");
  pv::require(expect_number(values, "determinism.scenarios_replayed") ==
                  static_cast<std::uint64_t>(replayed) + 1,
              "the kernel replays every scenario but the boundary block");
}

}  // namespace

void verify_derivations(const pv::Values& values, const pv::Values& primitives,
                        const pv::Values& ledger_vectors, const pv::Values& manifest,
                        const pv::Values& version_three) {
  check_constructions(values, primitives, ledger_vectors);
  check_genesis(values);
  check_tables(manifest, version_three);
  check_derived_rules(values);
  check_compatibility(values, primitives);
  check_determinism(values, primitives);
}

}  // namespace economy_v6_execution
