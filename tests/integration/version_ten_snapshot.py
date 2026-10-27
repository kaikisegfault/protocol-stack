#!/usr/bin/env python3

"""The version-ten snapshot payload, encoded from the model's ledger.

This is `encode_snapshot_v10` in `src/storage/snapshot_v10.cpp`, field for
field, and it exists so that a network can begin from a state the model's
blocks produced (ADRs 0096 and 0108). **It is not trusted.** A C++ node accepts
a payload only through `decode_snapshot_v10`'s gates, the retirement rule among
them, and `seed_sqlite_ledger_v10` also requires the payload to re-encode to
exactly its own octets. So every successful
seed is a check that this module and the C++ encoder write the same bytes for
the same state.

The payload is version nine's with two keys in its prefix, which is 198 octets
rather than 166. The launch key takes the verifier key's place, and the build
authority key follows the dispute authority key. No root commits to the build
authority key, so it is carried for the restore's parameters rather than for
the root. Otherwise the payload carries what the state root commits to: the
ordered account map, the key-ordered economy map, the root, and a labelled
digest over everything before it.
"""

from __future__ import annotations

import struct

from simulation.economy_transition.merkle import digest

MAGIC = b"PSSN"
VERSION = 10
DIGEST_LABEL = "protocol-stack:storage:snapshot-v10"


def _u16(value: int) -> bytes:
    return struct.pack(">H", value)


def _u32(value: int) -> bytes:
    return struct.pack(">I", value)


def _u64(value: int) -> bytes:
    return struct.pack(">Q", value)


def encode(ledger) -> bytes:
    """One version-ten ledger as the payload a node restores from.

    `ledger` is a `simulation.economy_transition_v10.ledger.Ledger`. Its root is
    computed here rather than accepted, so a ledger whose projection does not
    commit a root fails before any octet is written.
    """
    root = bytes.fromhex(ledger.state_root())
    accounts = ledger.accounts()
    economy = sorted(ledger.economy_entries().items())

    parts = [
        MAGIC,
        _u16(VERSION),
        ledger.chain_id,
        _u64(ledger.height),
        _u64(ledger.timestamp),
        _u64(ledger.supply_limit),
        _u64(ledger.total_supply),
        _u64(ledger.fee_pool),
        _u64(ledger.fixed_fee),
        ledger.launch_key,
        ledger.dispute_authority_key,
        ledger.build_authority_key,
        _u64(len(accounts)),
        _u64(len(economy)),
    ]
    for account_id, balance, nonce in accounts:
        parts += [account_id, _u64(balance), _u64(nonce)]
    for key, value in economy:
        parts += [_u32(len(key)), key, _u32(len(value)), value]
    parts.append(root)
    payload = b"".join(parts)
    return payload + digest(DIGEST_LABEL, payload)
