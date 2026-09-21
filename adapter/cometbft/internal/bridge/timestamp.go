package bridge

import (
	"errors"
	"math"
	"time"
)

// consensus-application-v2's timestamp conversion. CometBFT carries a time as
// separate seconds and nanoseconds, and the ledger's unit is the millisecond.
// The result enters the state root, so every replica must derive the same one
// from the same agreed value:
//
//	millis = seconds * 1000 + nanos / 1000000
//
// with the division truncating and the multiplication checked.
//
// **The bridge refuses only what it cannot represent.** A negative `seconds` is
// no `u64` millisecond count, an out-of-range `nanos` is not a well-formed
// timestamp, and an overflowing multiplication is a value no clock produced.
// Everything else is passed through — including a stamp above
// `MAX_TIMESTAMP_MILLIS`, which the application refuses itself as
// `TIMESTAMP_RANGE`. A bridge that pre-filtered the range would make
// `calendar-v1`'s first condition untestable end to end.
func millisFromTimestamp(seconds int64, nanos int32) (uint64, error) {
	if seconds < 0 {
		return 0, errors.New("timestamp precedes the epoch")
	}
	if nanos < 0 || nanos > 999_999_999 {
		return 0, errors.New("timestamp nanoseconds are out of range")
	}
	if uint64(seconds) > (math.MaxUint64-999)/1000 {
		return 0, errors.New("timestamp milliseconds overflow")
	}
	return uint64(seconds)*1000 + uint64(nanos)/1_000_000, nil
}

// A block time truncates. BFT time has nanosecond precision and is almost never
// a whole millisecond, so requiring one would refuse essentially every block.
// Truncation is safe for both rules the stamp feeds: a non-decreasing sequence
// stays non-decreasing under a monotone map, and the downward shift of at most
// 0.999 ms is four orders of magnitude inside the tolerance.
func blockMillis(value time.Time) (uint64, error) {
	return millisFromTimestamp(value.Unix(), int32(value.Nanosecond()))
}

// A genesis time must be exact. The launcher writes it, so it controls the
// value, and an exact comparison is what makes the CometBFT genesis and the
// canonical genesis one-to-one: truncating here would let two different
// CometBFT genesis files name one chain.
func genesisMillis(value time.Time) (uint64, error) {
	if value.Nanosecond()%1_000_000 != 0 {
		return 0, errors.New("genesis time has a sub-millisecond remainder")
	}
	return blockMillis(value)
}
