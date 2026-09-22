package nodeconfig

import (
	"errors"
	"fmt"
	"strconv"
	"time"
)

const (
	appStateV1 = `"protocol-stack-v1"`
	appStateV8 = `"protocol-stack-v8"`
	appStateV9 = `"protocol-stack-v9"`
	// maxGenesisTimestampMillis is calendar-v1's MAX_TIMESTAMP_MILLIS,
	// 9999-12-31T23:59:59.999Z. The range starts at zero, so every stamp at or
	// below it is in range. It is also the last instant CometBFT's RFC 3339
	// genesis encoding can write, so the two bounds are one bound.
	maxGenesisTimestampMillis = 253_402_300_799_999
)

// ProtocolVersion is the ledger version a home is initialised for. It reaches
// the application as the genesis application state, and **that is what stops a
// node started against a version-one genesis and a version-eight engine**: the
// application refuses at InitChain rather than at the first block.
//
// The refusal is exact rather than a range. `ApplicationV8::init_chain` still
// names the retired version-seven app state as a case of its own, because that
// is the string a stale deployment would be sending long after this adapter
// stopped offering to write one, so a home initialised at the wrong version
// fails at the handshake with the version it was initialised for.
type ProtocolVersion uint8

const (
	ProtocolV1 ProtocolVersion = 1
	ProtocolV8 ProtocolVersion = 8
	ProtocolV9 ProtocolVersion = 9
)

// ParseProtocolVersion accepts only the versions this adapter bridges, so an
// operator who mistypes one gets an error rather than a chain nobody joins.
func ParseProtocolVersion(value uint) (ProtocolVersion, error) {
	// Compared as the wider type on purpose: converting first would truncate,
	// and 257 would be admitted as version one.
	switch value {
	case uint(ProtocolV1):
		return ProtocolV1, nil
	case uint(ProtocolV8):
		return ProtocolV8, nil
	case uint(ProtocolV9):
		return ProtocolV9, nil
	}
	return 0, fmt.Errorf("unsupported protocol version %d", value)
}

func (p ProtocolVersion) appState() (string, error) {
	switch p {
	case ProtocolV1:
		return appStateV1, nil
	case ProtocolV8:
		return appStateV8, nil
	case ProtocolV9:
		return appStateV9, nil
	}
	return "", fmt.Errorf("unsupported protocol version %d", uint8(p))
}

// BindsGenesisTimestamp reports whether this version's canonical genesis
// carries a timestamp. It is exactly the versions whose application prints
// `genesis_timestamp=` in identity mode, which is why the identity parser asks.
func (p ProtocolVersion) BindsGenesisTimestamp() bool {
	return p == ProtocolV9
}

// GenesisTimestamp is version nine's canonical genesis stamp, in milliseconds
// since the Unix epoch. **Its zero value is the absence of a stamp**, which is
// what versions one and eight bind. A present stamp of zero is a different
// value and a valid one, because calendar-v1's range starts at zero, so
// absence cannot be spelled as a number.
type GenesisTimestamp struct {
	millis  uint64
	present bool
}

// NewGenesisTimestamp applies calendar-v1's C1 range to a genesis stamp.
func NewGenesisTimestamp(millis uint64) (GenesisTimestamp, error) {
	if millis > maxGenesisTimestampMillis {
		return GenesisTimestamp{}, fmt.Errorf(
			"genesis timestamp %d is outside calendar-v1's range", millis)
	}
	return GenesisTimestamp{millis: millis, present: true}, nil
}

// ParseGenesisTimestamp accepts exactly the decimal the application's identity
// mode prints: digits only, with no sign, no leading zero, and no whitespace.
// One value has one spelling, as the 64-character hash rule already requires
// of the other two identity fields.
func ParseGenesisTimestamp(value string) (GenesisTimestamp, error) {
	millis, err := strconv.ParseUint(value, 10, 64)
	if err != nil || strconv.FormatUint(millis, 10) != value {
		return GenesisTimestamp{}, errors.New(
			"genesis timestamp must be canonical decimal milliseconds")
	}
	return NewGenesisTimestamp(millis)
}

// Millis returns the stamp and whether one is present.
func (g GenesisTimestamp) Millis() (uint64, bool) {
	return g.millis, g.present
}

// genesisTime is consensus-application-v2's fifth derived genesis value.
//
// Versions one and eight bind no stamp and keep the epoch they have always
// written, so their genesis files are byte-identical to before. Version nine's
// is the canonical stamp at exactly millisecond precision, which is the one
// time the bridge's exact genesis conversion maps back to that stamp.
//
// **The pairing is refused in both directions.** A version-nine home written
// without a stamp would carry the epoch, which the application refuses at
// InitChain against its own genesis; a version-eight home given one would
// silently drop it. Both are an operator holding the wrong binary or the wrong
// flag, and this is the earliest point either can be named.
func (p ProtocolVersion) genesisTime(stamp GenesisTimestamp) (time.Time, error) {
	if _, err := p.appState(); err != nil {
		return time.Time{}, err
	}
	millis, present := stamp.Millis()
	switch {
	case present && !p.BindsGenesisTimestamp():
		return time.Time{}, fmt.Errorf(
			"protocol version %d binds no genesis timestamp", uint8(p))
	case !present && p.BindsGenesisTimestamp():
		return time.Time{}, fmt.Errorf(
			"protocol version %d requires a genesis timestamp", uint8(p))
	case !present:
		return time.Unix(0, 0).UTC(), nil
	}
	return time.UnixMilli(int64(millis)).UTC(), nil
}

// genesisValues are the derived values a protocol version fixes in every
// genesis this package writes, the single-validator one and the devnet's alike.
// The chain ID and application hash are the identity's own, and the initial
// height is always one.
func genesisValues(
	identity Identity,
	protocol ProtocolVersion,
) (appState string, genesisTime time.Time, err error) {
	appState, err = protocol.appState()
	if err != nil {
		return "", time.Time{}, err
	}
	genesisTime, err = protocol.genesisTime(identity.GenesisTimestamp)
	if err != nil {
		return "", time.Time{}, err
	}
	return appState, genesisTime, nil
}
