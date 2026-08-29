// Every conservation and structural equality a version-seven state must satisfy.
//
// All of them are equalities or exact bounds rather than loose ones, because a
// bound would admit a defect that lost a count. The first structural one is what
// this whole version exists for: every account is an escrow, which is the
// founder direction "there is no unverified participation" written as a property
// of state.

#include "economy_ledger_internal.hpp"

#include <algorithm>

namespace protocol::v7 {
namespace {

// A product that leaves `u64` is itself a failure rather than a wrapped
// comparison, so the identity is never checked against a truncated expectation.
bool product(std::uint64_t left, std::uint64_t right, std::uint64_t& result) {
  if (left != 0 && right > kMaxU64 / left) return false;
  result = left * right;
  return true;
}

bool sum_into(std::uint64_t& target, std::uint64_t amount) {
  if (amount > kMaxU64 - target) return false;
  target += amount;
  return true;
}

void check_supply(const Ledger& ledger, std::vector<std::string_view>& failures) {
  std::uint64_t held = 0;
  bool fits = true;
  for (const auto& [escrow, account] : ledger.registry.accounts) {
    (void)escrow;
    fits = fits && sum_into(held, account.balance);
  }
  fits = fits && sum_into(held, ledger.fee_pool);
  for (const auto& [beneficiary, amount] : ledger.custody) {
    (void)beneficiary;
    fits = fits && sum_into(held, amount);
  }
  // Value in custody has been issued and has not reached an account, so a check
  // that omitted it would report a shortfall after every node mint.
  if (!fits || held != ledger.total_supply) {
    failures.push_back("balances, the fee pool, and custody do not sum to supply");
  }
  if (ledger.total_supply > ledger.supply_limit) {
    failures.push_back("total supply exceeds the supply limit");
  }
}

// The two identities version seven states where version six stated one.
//
// **The channel identity** has two terms rather than three, because nothing is
// moved out of `outstanding` any more:
//
//     issued(c) + outstanding(c) = assigned_permissions * leg(c)
//
// **The backing identity** is the one that makes "100% is assigned" checkable:
//
//     outstanding(c) = claimable(c) + recovery_pool(c)
//
// The channel identity alone cannot catch a stranded unit, because `outstanding`
// is one number and a lost claim simply leaves it larger. Naming both halves
// makes value created without a claimant and a claim destroyed without payment
// two different failures, each an inequality against an exact figure.
//
// Version seven has no carry map to require empty. ADR 0055's Python model
// subclasses version six's ledger and inherits one; this kernel *replaces*
// version six under ADR 0046, so the field is gone rather than dead, and the
// root's shape rules refuse entry kind 7 outright.
void check_channel_identities(const Ledger& ledger,
                              std::vector<std::string_view>& failures) {
  const auto owed_per_channel = claimable(ledger);
  if (!owed_per_channel) {
    failures.push_back("a recorded cycle assignment does not decode");
  }
  for (std::uint8_t channel = 0; channel < kChannelCount; ++channel) {
    const auto leg = base_permission_leg(channel);
    if (leg == 0) continue;
    std::uint64_t expected = 0;
    std::uint64_t actual = ledger.channel_issued[channel];
    const bool fits = product(ledger.assigned_permissions, leg, expected) &&
                      sum_into(actual, ledger.channel_outstanding[channel]);
    if (!fits || actual != expected) {
      failures.push_back("a Founder Node channel breaks the channel identity");
    }
    if (!owed_per_channel) continue;
    std::uint64_t backing = (*owed_per_channel)[channel];
    if (!sum_into(backing, ledger.pool[channel]) ||
        backing != ledger.channel_outstanding[channel]) {
      failures.push_back("a Founder Node channel breaks the backing identity");
    }
  }

  std::uint64_t expected = 0;
  std::uint64_t actual = ledger.channel_issued[kReferralChannel];
  const bool fits =
      product(ledger.assigned_permissions, kReferralLegAtomic, expected) &&
      sum_into(actual, ledger.channel_outstanding[kReferralChannel]);
  if (!fits || actual != expected) {
    failures.push_back("the referral channel breaks its identity");
  }

  // The referral channel keeps version six's identity unchanged, including the
  // unreferred pool term: the referral leg has no winner split and therefore no
  // remainder, so the recovery pool never touches it.
  std::uint64_t referral_owed = 0;
  bool referral_fits = true;
  for (const auto& [identity, balance] : ledger.referral) {
    (void)identity;
    if (balance.minted_atomic > balance.accrued_atomic) {
      referral_fits = false;
      break;
    }
    referral_fits =
        sum_into(referral_owed, balance.accrued_atomic - balance.minted_atomic);
    if (!referral_fits) break;
  }
  referral_fits = referral_fits && ledger.pool_minted <= ledger.pool_accrued &&
                  sum_into(referral_owed, ledger.pool_accrued - ledger.pool_minted);
  if (!referral_fits ||
      referral_owed != ledger.channel_outstanding[kReferralChannel]) {
    failures.push_back("referral outstanding is not what the balances owe");
  }
}

// Channel 8 satisfies an inequality, and that is what forfeiture forces: the
// channel has no accrual step, so value is issued when it is collected and is
// otherwise never represented anywhere.
void check_verified_user(const Ledger& ledger,
                         std::vector<std::string_view>& failures) {
  if (ledger.channel_outstanding[kVerifiedUserChannel] != 0) {
    failures.push_back("the verified-user channel holds an outstanding amount");
  }
  std::uint64_t enrolled = 0;
  bool fits = true;
  for (const auto& [identity, enrollment] : ledger.registry.enrollments) {
    (void)identity;
    fits = fits && sum_into(enrolled, enrollment.issued_atomic);
  }
  if (!fits || ledger.channel_issued[kVerifiedUserChannel] != enrolled) {
    failures.push_back("verified-user issuance is not what the enrollments record");
  }
  if (ledger.channel_issued[kVerifiedUserChannel] > kVerifiedUserChannelCapAtomic) {
    failures.push_back("verified-user issuance exceeds its channel cap");
  }
}

void check_structure(const Ledger& ledger,
                     std::vector<std::string_view>& failures) {
  const auto& registry = ledger.registry;
  if (registry.accounts.size() != registry.escrows.size() ||
      !std::equal(registry.accounts.begin(), registry.accounts.end(),
                  registry.escrows.begin(),
                  [](const auto& account, const auto& escrow) {
                    return account.first == escrow.first;
                  })) {
    failures.push_back("the account map and the escrow set have different keys");
  }
  for (const auto& [escrow, record] : registry.escrows) {
    if (!registry.identities.contains(record.owner_hub_identity)) {
      failures.push_back("an escrow names an unregistered identity");
    }
    // A structured binding cannot be captured by a lambda in C++20, so each one
    // a predicate needs is copied into a named local first. GCC accepts the
    // capture and Clang refuses it, which is why the matrix runs both.
    const auto& named = escrow;
    const auto assigned = static_cast<std::uint32_t>(std::count_if(
        registry.signers.begin(), registry.signers.end(),
        [&named](const auto& entry) { return entry.second == named; }));
    if (assigned != record.signer_count) {
      failures.push_back("an escrow's signer count is not its signer entries");
    }
    if (record.signer_count > kMaxSignersPerEscrow) {
      failures.push_back("an escrow holds more than sixteen signers");
    }
  }
  for (const auto& [identifier, escrow] : registry.signers) {
    (void)identifier;
    if (!registry.escrows.contains(escrow)) {
      failures.push_back("a signer names an escrow that does not exist");
    }
  }
  for (const auto& [hash, identity] : registry.identities) {
    const auto& owner = hash;
    const auto live = static_cast<std::uint32_t>(std::count_if(
        registry.escrows.begin(), registry.escrows.end(),
        [&owner](const auto& entry) {
          return entry.second.owner_hub_identity == owner;
        }));
    if (live != identity.escrow_count) {
      failures.push_back("an identity's escrow count is not its escrow entries");
    }
    if (identity.next_escrow_index < identity.escrow_count) {
      failures.push_back("an identity's next index is below its live count");
    }
    if (identity.seat_count > kMaxSeatsPerIdentity) {
      failures.push_back("an identity holds more than one thousand seats");
    }
    const auto held = static_cast<std::uint32_t>(std::count_if(
        ledger.seats.begin(), ledger.seats.end(), [&owner](const auto& entry) {
          return entry.second.hub_identity_hash == owner;
        }));
    if (held != identity.seat_count) {
      failures.push_back("an identity's seat count is not its seat entries");
    }
  }
  for (const auto& [seat_id, seat] : ledger.seats) {
    (void)seat_id;
    if (!registry.identities.contains(seat.hub_identity_hash)) {
      failures.push_back("a seat names an unregistered identity");
    }
  }
}

}  // namespace

std::vector<std::string_view> conservation_failures(const Ledger& ledger) {
  std::vector<std::string_view> failures;
  check_supply(ledger, failures);
  check_channel_identities(ledger, failures);
  check_verified_user(ledger, failures);
  check_structure(ledger, failures);
  std::sort(failures.begin(), failures.end());
  failures.erase(std::unique(failures.begin(), failures.end()), failures.end());
  return failures;
}

}  // namespace protocol::v7
