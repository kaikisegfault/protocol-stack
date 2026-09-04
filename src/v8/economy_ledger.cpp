// The version-eight ledger: opening it, moving value inside it, and projecting
// it into the canonical entries the roots are taken over.
//
// The conservation checks are here rather than in the transitions because they
// are properties of a state rather than of a step. Every one is an equality: a
// bound would admit a defect that lost a term, which is the reason version four
// gives for its own two.

#include "economy_ledger_internal.hpp"

#include <algorithm>
#include <array>

namespace protocol::v8 {
namespace {

// The accepted manifest's ten channel caps, in channel-identifier order. They
// are founder-directed figures rather than derived ones, and the kernel tests
// check every entry against `test-vectors/founder-economy-manifest-v3.txt`.
// ADR 0053's manifest renames channel 9 and moves no figure, so every cap below
// is version two's and the binding is what moved.
constexpr std::array<std::uint64_t, kChannelCount> kChannelCaps{
    2'500'020'000'000'000'000,  // 0 founder_operator
    1'250'010'000'000'000'000,  // 1 venture_escrow
    250'002'000'000'000'000,    // 2 community_grants_escrow
    125'001'000'000'000'000,    // 3 developer_incentives_escrow
    73'100'000'000'000'000,     // 4 system_creator_issuance_royalty
    750'006'000'000'000'000,    // 5 liquidity_mining
    375'003'000'000'000'000,    // 6 impermanent_loss_protection
    250'002'000'000'000'000,    // 7 founder_referral
    125'001'000'000'000'000,    // 8 hub_verified_user_incentives
    1'250'010'000'000'000,      // 9 mini_gamified_incentives
};

// The five base-permission legs one assigned cycle permission is split into.
// Channels 5 through 9 take no leg, so their entry is zero rather than absent:
// the channel identity is stated over every channel and holds trivially where
// the leg is zero. The five that are nonzero are exactly the recovery pool's
// five, which is why one pool entry replaces ten carry entries.
constexpr std::array<std::uint64_t, kChannelCount> kBasePermissionLegs{
    34'200'000'000, 17'100'000'000, 3'420'000'000, 1'710'000'000,
    1'000'000'000,  0,              0,             0,
    0,              0,
};

bool add_checked(std::uint64_t& target, std::uint64_t amount) {
  if (amount > kMaxU64 - target) return false;
  target += amount;
  return true;
}

// A product that leaves `u64` is a failure rather than a wrapped value, so no
// collection is ever compared against a truncated expectation.
bool product_checked(std::uint64_t left, std::uint64_t right,
                     std::uint64_t& result) {
  if (left != 0 && right > kMaxU64 / left) return false;
  result = left * right;
  return true;
}

void push(std::vector<EconomyEntry>& entries, Bytes key, Bytes value) {
  entries.push_back(EconomyEntry{std::move(key), std::move(value)});
}

}  // namespace

std::uint64_t channel_cap(std::uint8_t channel_index) {
  return channel_index < kChannelCount ? kChannelCaps[channel_index] : 0;
}

std::uint64_t base_permission_leg(std::uint8_t channel_index) {
  return channel_index < kChannelCount ? kBasePermissionLegs[channel_index] : 0;
}

PermissionSplit split_permission(std::uint32_t winner_count) {
  PermissionSplit split;
  for (std::size_t channel = 0; channel < kRecoveryPoolLegs; ++channel) {
    const auto leg = kBasePermissionLegs[channel];
    if (winner_count == 0) {
      // No winner divides nothing: the share is zero and the whole leg is the
      // remainder, which is what sends a cycle nobody wins into the pool entire.
      split.share[channel] = 0;
      split.remainder[channel] = leg;
      continue;
    }
    const auto share = leg / winner_count;
    split.share[channel] = share;
    split.remainder[channel] = leg - share * winner_count;
  }
  return split;
}

std::uint64_t Collection::total_atomic() const {
  std::uint64_t total = 0;
  for (const auto amount : per_channel) total += amount;
  return total;
}

std::optional<Collection> collect_node(const Ledger& ledger,
                                       std::uint32_t seat_id, std::uint64_t mark,
                                       std::optional<std::uint64_t> last_assigned) {
  Collection collection;
  const auto span = walk_range(mark, last_assigned);
  if (!span) return collection;
  collection.windows_walked = span->last_window - span->first_window + 1;

  for (auto window = span->first_window; window <= span->last_window; ++window) {
    const auto found = ledger.assignments.find(window);
    // An absent record and a record with both bits clear are the same fact.
    if (found == ledger.assignments.end()) continue;
    const auto record = decode_cycle_assignment_value(found->second);
    // A recorded assignment that will not decode is an invariant failure rather
    // than an empty window: the projection wrote it and the root committed it.
    if (!record) return std::nullopt;

    if (bit_is_set(record->accrued_bitmap, seat_id)) {
      collection.accrued_windows.push_back(window);
      for (std::size_t channel = 0; channel < kRecoveryPoolLegs; ++channel) {
        if (!add_checked(collection.per_channel[channel],
                         kBasePermissionLegs[channel])) {
          return std::nullopt;
        }
      }
    }
    if (bit_is_set(record->winner_bitmap, seat_id)) {
      collection.won_windows.push_back(window);
      // A winner bit with a zero winner count is unrepresentable — the decoder
      // above refuses the record that would carry it — so the division is safe.
      if (record->winner_count == 0) return std::nullopt;
      const auto split = split_permission(record->winner_count);
      for (std::size_t channel = 0; channel < kRecoveryPoolLegs; ++channel) {
        std::uint64_t reallocated = 0;
        if (!product_checked(record->reallocated_count, split.share[channel],
                             reallocated)) {
          return std::nullopt;
        }
        if (!add_checked(collection.per_channel[channel], reallocated)) {
          return std::nullopt;
        }
        // Version seven's added term, and the only change to the walk: a winner
        // also takes this cycle's share of what it absorbed from the pool.
        const auto pool_share =
            record->pool_absorbed[channel] / record->winner_count;
        if (!add_checked(collection.per_channel[channel], pool_share)) {
          return std::nullopt;
        }
      }
    }
  }
  return collection;
}

std::optional<RecoveryPool> claimable(const Ledger& ledger) {
  RecoveryPool owed{};
  // The largest window with a record, which is what a mint at any height past
  // that window's boundary would walk to.
  std::optional<std::uint64_t> last_assigned;
  if (!ledger.assignments.empty()) last_assigned = ledger.assignments.rbegin()->first;

  for (const auto& [seat_id, seat] : ledger.seats) {
    const auto collection =
        collect_node(ledger, seat_id, seat.minted_through_window, last_assigned);
    if (!collection) return std::nullopt;
    for (std::size_t channel = 0; channel < kRecoveryPoolLegs; ++channel) {
      if (!add_checked(owed[channel], collection->per_channel[channel])) {
        return std::nullopt;
      }
    }
  }
  return owed;
}

std::optional<Ledger> open_ledger(const Genesis& genesis) {
  const auto identity = chain_id(genesis);
  if (!identity) return std::nullopt;
  Ledger ledger;
  ledger.chain_id = *identity;
  ledger.supply_limit = genesis.supply_limit;
  ledger.fixed_fee = genesis.fixed_transfer_fee;
  ledger.verifier_key = genesis.verifier_key;
  // The ninth genesis field, bound into the chain identity above and carried
  // here so the dispute transition can check a signature against it. Version
  // eight writes no open challenge and no seat window record at genesis: a
  // challenge is issued by a block, and a window record exists only once a seat
  // has lost or had a slot voided.
  ledger.dispute_authority_key = genesis.dispute_authority_key;
  return ledger;
}

std::vector<EconomyEntry> economy_entries(const Ledger& ledger) {
  std::vector<EconomyEntry> entries;
  // The fixed tables genesis writes, carrying their current values. Writing them
  // explicitly is what keeps an absent entry unambiguous rather than making
  // absence an implicit zero default.
  for (std::uint8_t index = 0; index < kChannelCount; ++index) {
    push(entries, channel_key(index),
         channel_value(ledger.channel_issued[index],
                       ledger.channel_outstanding[index]));
  }
  // One recovery pool entry where version six wrote ten carries, five of which
  // were structurally always zero. Entry kind 7 is never written here and the
  // root's shape rules refuse it, so a projection that regressed to version
  // six's carry would fail at the root rather than produce a root nothing else
  // would ever match.
  push(entries, recovery_pool_key(), recovery_pool_value(ledger.pool));
  push(entries, verifier_key_key(), verifier_key_value(ledger.verifier_key));
  push(entries, unreferred_pool_key(),
       unreferred_pool_value(ledger.pool_accrued, ledger.pool_minted));
  push(entries, verified_user_counter_key(),
       verified_user_counter_value(ledger.registry.enrolled_count));

  for (const auto& [hash, identity] : ledger.registry.identities) {
    push(entries, hub_identity_key(hash), hub_identity_value(identity));
  }
  for (const auto& [escrow, record] : ledger.registry.escrows) {
    push(entries, escrow_key(escrow), escrow_value(record));
  }
  for (const auto& [identifier, escrow] : ledger.registry.signers) {
    push(entries, signer_key(identifier), signer_value(escrow));
  }
  for (const auto& [hash, enrollment] : ledger.registry.enrollments) {
    push(entries, verified_user_key(hash), verified_user_value(enrollment));
  }
  for (const auto& [beneficiary, amount] : ledger.custody) {
    push(entries, typed_custody_key(beneficiary, internal::kSingletonBeneficiaryId),
         typed_custody_value(amount));
  }
  for (const auto& [seat_id, seat] : ledger.seats) {
    push(entries, seat_key(seat_id), seat_value(seat));
  }
  for (const auto& [hash, balance] : ledger.referral) {
    push(entries, referral_balance_key(hash),
         referral_balance_value(balance.accrued_atomic, balance.minted_atomic,
                                balance.collected_through_window));
  }
  for (const auto& decision : ledger.decisions) {
    push(entries, direct_decision_key(decision), Bytes{});
  }
  for (const auto& [window, value] : ledger.assignments) {
    push(entries, cycle_assignment_key(window), value);
  }
  // The uptime carrier's two entry kinds, appended raw. They are held as encoded
  // bytes on the ledger precisely so this projection is a copy rather than a
  // re-encoding: the two transitions write the same key space the root commits
  // to, so there is nothing here that could disagree with them.
  for (const auto& [key, value] : ledger.uptime) {
    push(entries, key, value);
  }
  return entries;
}

std::vector<AccountEntry> account_entries(const Ledger& ledger) {
  std::vector<AccountEntry> accounts;
  accounts.reserve(ledger.registry.accounts.size());
  for (const auto& [escrow, account] : ledger.registry.accounts) {
    accounts.push_back(AccountEntry{escrow, account.balance, account.nonce});
  }
  return accounts;
}

std::optional<Hash> ledger_state_root(const Ledger& ledger) {
  StateSummary summary;
  summary.chain_id = ledger.chain_id;
  summary.height = ledger.height;
  summary.supply_limit = ledger.supply_limit;
  summary.total_supply = ledger.total_supply;
  summary.fee_pool_balance = ledger.fee_pool;
  return state_root(summary, account_entries(ledger), economy_entries(ledger));
}

namespace internal {

std::uint64_t balance_of(const Ledger& ledger, const Octets32& escrow) {
  const auto found = ledger.registry.accounts.find(escrow);
  return found == ledger.registry.accounts.end() ? 0 : found->second.balance;
}

std::uint64_t nonce_of(const Ledger& ledger, const Octets32& escrow) {
  const auto found = ledger.registry.accounts.find(escrow);
  return found == ledger.registry.accounts.end() ? 0 : found->second.nonce;
}

void set_nonce(Ledger& ledger, const Octets32& escrow, std::uint64_t nonce) {
  ledger.registry.accounts[escrow].nonce = nonce;
}

bool credit(Ledger& ledger, const Octets32& escrow, std::uint64_t amount) {
  const auto found = ledger.registry.accounts.find(escrow);
  if (found == ledger.registry.accounts.end()) return false;
  return add_checked(found->second.balance, amount);
}

bool debit(Ledger& ledger, const Octets32& escrow, std::uint64_t amount) {
  const auto found = ledger.registry.accounts.find(escrow);
  if (found == ledger.registry.accounts.end()) return false;
  if (found->second.balance < amount) return false;
  found->second.balance -= amount;
  return true;
}

bool collect_fee(Ledger& ledger, const Octets32& escrow) {
  if (!debit(ledger, escrow, ledger.fixed_fee)) return false;
  return add_checked(ledger.fee_pool, ledger.fixed_fee);
}

bool issue(Ledger& ledger, std::uint8_t channel, std::uint64_t amount) {
  if (channel >= kChannelCount) return false;
  if (channel != kVerifiedUserChannel) {
    if (ledger.channel_outstanding[channel] < amount) return false;
    ledger.channel_outstanding[channel] -= amount;
  }
  if (!add_checked(ledger.channel_issued[channel], amount)) return false;
  if (!add_checked(ledger.total_supply, amount)) return false;
  return ledger.total_supply <= ledger.supply_limit;
}

bool fits_channel(const Ledger& ledger, std::uint8_t channel,
                  std::uint64_t amount) {
  if (channel >= kChannelCount) return false;
  const auto cap = channel_cap(channel);
  const auto issued = ledger.channel_issued[channel];
  return amount <= cap && issued <= cap - amount;
}

std::optional<Outcome> charged(Ledger& ledger, const Octets32& escrow) {
  set_nonce(ledger, escrow, nonce_of(ledger, escrow) + 1);
  if (!collect_fee(ledger, escrow)) return std::nullopt;
  Outcome outcome;
  outcome.fee_charged = ledger.fixed_fee;
  return outcome;
}

std::optional<std::uint8_t> leg_beneficiary_kind(std::uint8_t channel_index) {
  // The Founder operator leg credits an account balance and has no custody
  // kind; the four institutional legs credit typed custody 1 through 4.
  if (channel_index == kFounderOperatorChannel) return std::nullopt;
  if (channel_index > 4) return std::nullopt;
  return channel_index;
}

}  // namespace internal
}  // namespace protocol::v8
