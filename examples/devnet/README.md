# M1 local devnet fixtures

These hexadecimal fixtures reproduce the public synthetic ledger-transition
vectors. They are development-only values with publicly known signing seeds
and must never hold real value.

- `protocol.genesis.hex` is the canonical two-account synthetic genesis.
- `transaction-1.hex` is a valid height-one transfer from the first funded
  account with nonce `1`.
- `transaction-2.hex` is a valid next transfer from the same account with
  nonce `2`.

`tools/devnet.sh` decodes these fixtures into its ignored persistent devnet
directory. The four CometBFT validator and node keys are generated locally and
are never printed or committed.
