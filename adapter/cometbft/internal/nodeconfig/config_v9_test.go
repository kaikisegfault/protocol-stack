package nodeconfig

import (
	"bytes"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	cfg "github.com/cometbft/cometbft/config"
)

// 2026-09-21T14:13:20.123Z. **Deliberately not a whole second**: a rendering
// that dropped or rounded the fraction would still agree on every stamp that
// ends in 000, and the bridge's exact genesis conversion is what would then
// refuse the chain at InitChain.
const testStampMillis = 1_790_000_000_123

func testIdentityV9(t *testing.T, millis uint64) Identity {
	t.Helper()
	stamp, err := NewGenesisTimestamp(millis)
	if err != nil {
		t.Fatalf("stamp %d: %v", millis, err)
	}
	identity := testIdentity()
	identity.GenesisTimestamp = stamp
	return identity
}

func genesisPathOf(home string) string {
	return filepath.Join(home, cfg.DefaultConfigDir, cfg.DefaultGenesisJSONName)
}

func TestParseGenesisTimestamp(t *testing.T) {
	for value, expected := range map[string]uint64{
		"0":               0,
		"1":               1,
		"1790000000123":   testStampMillis,
		"253402300799999": maxGenesisTimestampMillis,
	} {
		stamp, err := ParseGenesisTimestamp(value)
		if err != nil {
			t.Fatalf("ParseGenesisTimestamp(%q): %v", value, err)
		}
		millis, present := stamp.Millis()
		if !present || millis != expected {
			t.Fatalf("ParseGenesisTimestamp(%q) = %d, %v", value, millis, present)
		}
	}
	// One value, one spelling: each of these names a number the parser could
	// have read, and accepting it would give one chain two command lines.
	// The last two are one past calendar-v1's range and one past a u64.
	for _, value := range []string{
		"", "-1", "+1", "01", "00", " 1", "1 ", "1\n", "1.0", "1e3",
		"0x10", "1_000", "253402300800000", "18446744073709551616",
	} {
		if _, err := ParseGenesisTimestamp(value); err == nil {
			t.Fatalf("ParseGenesisTimestamp(%q) was accepted", value)
		}
	}
	if _, err := NewGenesisTimestamp(maxGenesisTimestampMillis + 1); err == nil {
		t.Fatal("a stamp past calendar-v1's range was accepted")
	}
	// The zero value is the absence of a stamp, and a present zero is not it.
	if millis, present := (GenesisTimestamp{}).Millis(); present || millis != 0 {
		t.Fatal("the zero GenesisTimestamp claims a stamp")
	}
	zero, err := NewGenesisTimestamp(0)
	if err != nil || zero == (GenesisTimestamp{}) {
		t.Fatalf("a present zero stamp is indistinguishable from none: %v", err)
	}
}

// consensus-application-v2's `genesis_time` is the canonical stamp at exactly
// millisecond precision, in UTC.
func TestGenesisTimeIsTheStampAtMillisecondPrecision(t *testing.T) {
	for _, millis := range []uint64{
		0, 1, 999, 1_000, testStampMillis, maxGenesisTimestampMillis,
	} {
		stamp, err := NewGenesisTimestamp(millis)
		if err != nil {
			t.Fatal(err)
		}
		value, err := ProtocolV9.genesisTime(stamp)
		if err != nil {
			t.Fatalf("stamp %d: %v", millis, err)
		}
		if value.UnixMilli() != int64(millis) ||
			value.Nanosecond()%1_000_000 != 0 ||
			value.Location() != time.UTC {
			t.Fatalf("stamp %d rendered as %v", millis, value)
		}
	}
	for _, protocol := range []ProtocolVersion{ProtocolV1, ProtocolV8} {
		value, err := protocol.genesisTime(GenesisTimestamp{})
		if err != nil || !value.Equal(time.Unix(0, 0)) {
			t.Fatalf("version %d genesis time = %v, %v",
				uint8(protocol), value, err)
		}
	}
}

func TestTheStampAndTheVersionArePaired(t *testing.T) {
	present, err := NewGenesisTimestamp(testStampMillis)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ProtocolV9.genesisTime(GenesisTimestamp{}); err == nil ||
		!strings.Contains(err.Error(), "requires a genesis timestamp") {
		t.Fatalf("version nine without a stamp: %v", err)
	}
	for _, protocol := range []ProtocolVersion{ProtocolV1, ProtocolV8} {
		if _, err := protocol.genesisTime(present); err == nil ||
			!strings.Contains(err.Error(), "binds no genesis timestamp") {
			t.Fatalf("version %d with a stamp: %v", uint8(protocol), err)
		}
	}
	for _, unbridged := range []ProtocolVersion{0, 7, 10} {
		for _, stamp := range []GenesisTimestamp{{}, present} {
			if _, err := unbridged.genesisTime(stamp); err == nil {
				t.Fatalf("unbridged version %d produced a genesis time",
					uint8(unbridged))
			}
		}
	}
	if !ProtocolV9.BindsGenesisTimestamp() ||
		ProtocolV1.BindsGenesisTimestamp() ||
		ProtocolV8.BindsGenesisTimestamp() {
		t.Fatal("BindsGenesisTimestamp disagrees with the versions")
	}
}

// **`genesis_time` is enforced, not decorative.** The engine and the
// application must agree on it, so a home that disagrees is refused when it is
// initialised, which is when an operator is looking.
func TestAVersionNineHomeCarriesTheStampAndRefusesAnother(t *testing.T) {
	home := filepath.Join(t.TempDir(), "node")
	identity := testIdentityV9(t, testStampMillis)
	if err := Ensure(home, identity, testEndpoints(), ProtocolV9); err != nil {
		t.Fatalf("fresh version-nine ensure: %v", err)
	}
	genesisPath := genesisPathOf(home)
	document, err := readGenesis(genesisPath)
	if err != nil {
		t.Fatalf("read generated genesis: %v", err)
	}
	if !bytes.Equal(document.AppState, []byte(appStateV9)) ||
		document.GenesisTime.UnixMilli() != testStampMillis ||
		document.GenesisTime.Nanosecond() != 123_000_000 ||
		document.ChainID != identity.CometChainID() ||
		!bytes.Equal(document.AppHash, identity.AppHash[:]) {
		t.Fatalf("version-nine genesis mismatch: %v %q",
			document.GenesisTime, document.AppState)
	}
	// The file is what CometBFT reads, so the exact text is the claim.
	original := readFile(t, genesisPath)
	if !bytes.Contains(original,
		[]byte(`"genesis_time": "2026-09-21T14:13:20.123Z"`)) {
		t.Fatalf("genesis file does not carry the stamp:\n%s", original)
	}

	if err := Ensure(home, identity, testEndpoints(), ProtocolV9); err != nil {
		t.Fatalf("repeated version-nine ensure: %v", err)
	}
	refusals := map[string]struct {
		identity Identity
		protocol ProtocolVersion
		want     string
	}{
		"one millisecond later": {
			testIdentityV9(t, testStampMillis+1), ProtocolV9, "genesis differs",
		},
		"the epoch": {testIdentityV9(t, 0), ProtocolV9, "genesis differs"},
		"no stamp":  {testIdentity(), ProtocolV9, "requires a genesis timestamp"},
		"version eight with the stamp": {
			identity, ProtocolV8, "binds no genesis timestamp",
		},
		"version eight": {testIdentity(), ProtocolV8, "genesis differs"},
	}
	for name, refusal := range refusals {
		err := Ensure(home, refusal.identity, testEndpoints(), refusal.protocol)
		if err == nil || !strings.Contains(err.Error(), refusal.want) {
			t.Fatalf("%s: error = %v, want %q", name, err, refusal.want)
		}
		if !bytes.Equal(readFile(t, genesisPath), original) {
			t.Fatalf("%s: the refusal modified the genesis", name)
		}
	}
}

// The largest stamp calendar-v1 admits is also the last instant RFC 3339 can
// write, and a present zero is the epoch under version nine's app state.
func TestTheStampBoundariesRoundTrip(t *testing.T) {
	for millis, rendered := range map[uint64]string{
		maxGenesisTimestampMillis: `"genesis_time": "9999-12-31T23:59:59.999Z"`,
		0:                         `"genesis_time": "1970-01-01T00:00:00Z"`,
	} {
		home := filepath.Join(t.TempDir(), "node")
		identity := testIdentityV9(t, millis)
		if err := Ensure(home, identity, testEndpoints(), ProtocolV9); err != nil {
			t.Fatalf("stamp %d: %v", millis, err)
		}
		if err := Ensure(home, identity, testEndpoints(), ProtocolV9); err != nil {
			t.Fatalf("stamp %d did not survive a round trip: %v", millis, err)
		}
		if !bytes.Contains(readFile(t, genesisPathOf(home)), []byte(rendered)) {
			t.Fatalf("stamp %d is not rendered as %s", millis, rendered)
		}
	}
}

// Versions one and eight keep the epoch, so their homes are the ones they were.
func TestVersionsOneAndEightKeepTheEpoch(t *testing.T) {
	for _, protocol := range []ProtocolVersion{ProtocolV1, ProtocolV8} {
		home := filepath.Join(t.TempDir(), "node")
		if err := Ensure(home, testIdentity(), testEndpoints(), protocol); err != nil {
			t.Fatalf("version %d: %v", uint8(protocol), err)
		}
		if !bytes.Contains(readFile(t, genesisPathOf(home)),
			[]byte(`"genesis_time": "1970-01-01T00:00:00Z"`)) {
			t.Fatalf("version %d genesis left the epoch", uint8(protocol))
		}
	}
}

// A refused pairing must leave nothing behind. The devnet case is the one that
// matters: keys written before the refusal would be a home without a genesis,
// which preflight refuses as incomplete on every later start.
func TestARefusedPairingWritesNothing(t *testing.T) {
	requireAbsent := func(path string) {
		t.Helper()
		if _, err := os.Lstat(path); !errors.Is(err, os.ErrNotExist) {
			t.Fatalf("%s exists after a refused pairing: %v", path, err)
		}
	}
	home := filepath.Join(t.TempDir(), "node")
	if err := Ensure(
		home, testIdentity(), testEndpoints(), ProtocolV9); err == nil {
		t.Fatal("a version-nine home without a stamp was initialised")
	}
	requireAbsent(home)

	devnet := mustDevnet(t)
	if err := devnet.Ensure(testIdentity(), ProtocolV9); err == nil {
		t.Fatal("a version-nine devnet without a stamp was initialised")
	}
	if err := devnet.Ensure(
		testIdentityV9(t, testStampMillis), ProtocolV8); err == nil {
		t.Fatal("a version-eight devnet with a stamp was initialised")
	}
	requireAbsent(devnet.Root)
}

func TestAVersionNineDevnetSharesTheStamp(t *testing.T) {
	devnet := mustDevnet(t)
	identity := testIdentityV9(t, testStampMillis)
	if err := devnet.Ensure(identity, ProtocolV9); err != nil {
		t.Fatalf("fresh version-nine devnet: %v", err)
	}
	for _, node := range devnet.Nodes {
		document, err := readGenesis(genesisPathOf(node.Home))
		if err != nil {
			t.Fatalf("node %d: %v", node.Index, err)
		}
		if document.GenesisTime.UnixMilli() != testStampMillis ||
			!bytes.Equal(document.AppState, []byte(appStateV9)) ||
			len(document.Validators) != DevnetNodeCount {
			t.Fatalf("node %d genesis mismatch", node.Index)
		}
	}
	if err := devnet.Ensure(identity, ProtocolV9); err != nil {
		t.Fatalf("repeated version-nine devnet: %v", err)
	}
	err := devnet.Ensure(testIdentityV9(t, testStampMillis+1), ProtocolV9)
	if err == nil || !strings.Contains(err.Error(), "genesis differs") {
		t.Fatalf("a devnet re-stamped in place: %v", err)
	}
}
