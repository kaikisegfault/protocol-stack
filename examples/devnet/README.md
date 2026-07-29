# M1 local devnet fixtures

These hexadecimal fixtures reproduce the public deterministic differential-test
fixture. They are development-only values with publicly known signing seeds
and must never hold real value.

- `protocol.genesis.hex` is the canonical four-account synthetic genesis.
- `transaction-1.hex` is a valid transfer from the first funded account with
  nonce `1`.
- `transaction-2.hex` is a valid next transfer from the same account with
  nonce `2`.

`tools/devnet.sh` decodes these fixtures into its ignored persistent devnet
directory. The four CometBFT validator and node keys are generated locally and
are never printed or committed. Ephemeral application sockets are kept in a
short owner-only platform temporary directory, outside the persistent network
tree.
