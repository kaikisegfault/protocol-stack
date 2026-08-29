// Every conservation and structural equality a version-six state must satisfy.
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

void check_carry_identity(const Ledger& ledger,
                          std::vector<std::string_view>& failures) {
  for (std::uint8_t channel = 0; channel < kChannelCount; ++channel) {
    const auto leg = base_permission_leg(channel);
    if (leg == 0) continue;
    std::uint64_t expected = 0;
    std::uint64_t actual = ledger.channel_issued[channel];
    const bool fits = product(ledger.assigned_permissions, leg, expected) &&
                      sum_into(actual, ledger.channel_outstanding[channel]) &&
                      sum_into(actual, ledger.carry[channel]);
    if (!fits || actual != expected) {
      failures.push_back("a Founder Node channel breaks the carry identity");
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

  std::uint64_t owed = 0;
  bool owed_fits = true;
  for (const auto& [identity, balance] : ledger.referral) {
    (void)identity;
    if (balance.minted_atomic > balance.accrued_atomic) {
      owed_fits = false;
      break;
    }
    owed_fits = sum_into(owed, balance.accrued_atomic - balance.minted_atomic);
    if (!owed_fits) break;
  }
  owed_fits = owed_fits && ledger.pool_minted <= ledger.pool_accrued &&
              sum_into(owed, ledger.pool_accrued - ledger.pool_minted);
  if (!owed_fits || owed != ledger.channel_outstanding[kReferralChannel]) {
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
  check_carry_identity(ledger, failures);
  check_verified_user(ledger, failures);
  check_structure(ledger, failures);
  std::sort(failures.begin(), failures.end());
  failures.erase(std::unique(failures.begin(), failures.end()), failures.end());
  return failures;
}

}  // namespace protocol::v7
