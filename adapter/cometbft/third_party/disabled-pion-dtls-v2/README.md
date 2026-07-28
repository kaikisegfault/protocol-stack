# Disabled Pion DTLS v2 module

This intentionally empty local module replaces `github.com/pion/dtls/v2`.
CometBFT `v0.39.4` retains the unpatched module in its manifest even after the
selected libp2p closure migrates to DTLS v3.

The node build must prove that no package imports this module. If an upstream
change reintroduces an import, compilation fails because this replacement
contains no packages. Do not add implementation code here.
