package bridge

import (
	"math"
	"testing"
	"time"
)

// consensus-application-v2's conversion cases, each on its own.
func TestTimestampConversion(t *testing.T) {
	refused := map[string]struct {
		seconds int64
		nanos   int32
	}{
		"negative seconds":       {-1, 0},
		"negative nanos":         {0, -1},
		"nanos past a second":    {0, 1_000_000_000},
		"overflowing seconds":    {int64((math.MaxUint64-999)/1000 + 1), 0},
		"largest signed seconds": {math.MaxInt64, 0},
	}
	for name, value := range refused {
		if _, err := millisFromTimestamp(value.seconds, value.nanos); err == nil {
			t.Fatalf("%s was converted", name)
		}
	}
	// The largest `seconds` whose millisecond count, plus the largest
	// sub-second part, still fits.
	largest := int64((math.MaxUint64 - 999) / 1000)
	if millis, err := millisFromTimestamp(largest, 999_999_999); err != nil ||
		millis != uint64(largest)*1000+999 {
		t.Fatalf("the largest representable stamp = %d, %v", millis, err)
	}
}

// A block time truncates downward, and a genesis time must be exact.
func TestBlockAndGenesisTimes(t *testing.T) {
	block := time.Unix(1_768_435_290, 999_999_999)
	if millis, err := blockMillis(block); err != nil || millis != 1_768_435_290_999 {
		t.Fatalf("a sub-millisecond block time = %d, %v", millis, err)
	}
	if _, err := genesisMillis(block); err == nil {
		t.Fatal("a genesis time with a sub-millisecond remainder was accepted")
	}
	genesis := time.UnixMilli(1_768_435_200_000)
	if millis, err := genesisMillis(genesis); err != nil || millis != 1_768_435_200_000 {
		t.Fatalf("an exact genesis time = %d, %v", millis, err)
	}
	// Go's zero time is the year 1, before the epoch.
	if _, err := blockMillis(time.Time{}); err == nil {
		t.Fatal("the zero time was converted")
	}
}

// **A stamp above `MAX_TIMESTAMP_MILLIS` is representable and is passed
// through.** The application refuses it as `TIMESTAMP_RANGE`; a bridge that
// refused it first would make that condition unreachable end to end.
func TestAStampPastTheCalendarReachesTheApplication(t *testing.T) {
	const maxTimestampMillis = 253_402_300_799_999
	past := time.UnixMilli(maxTimestampMillis + 1)
	if millis, err := blockMillis(past); err != nil || millis != maxTimestampMillis+1 {
		t.Fatalf("a stamp past the calendar = %d, %v", millis, err)
	}
}
