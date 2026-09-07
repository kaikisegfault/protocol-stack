package nodeconfig

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"

	cfg "github.com/cometbft/cometbft/config"
)

func testIdentity() Identity {
	var identity Identity
	for index := range identity.ChainID {
		identity.ChainID[index] = byte(index)
		identity.AppHash[index] = byte(255 - index)
	}
	return identity
}

func testEndpoints() Endpoints {
	return Endpoints{
		ProxyApp: "tcp://127.0.0.1:27658",
		RPC:      "tcp://127.0.0.1:27657",
		P2P:      "tcp://127.0.0.1:27656",
	}
}

func requireMode(t *testing.T, path string, expected os.FileMode) {
	t.Helper()
	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("stat %s: %v", path, err)
	}
	if info.Mode().Perm() != expected {
		t.Fatalf("%s mode %04o, want %04o",
			path, info.Mode().Perm(), expected)
	}
}

func readFile(t *testing.T, path string) []byte {
	t.Helper()
	value, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s: %v", path, err)
	}
	return value
}

func TestParseIdentity(t *testing.T) {
	identity := testIdentity()
	parsed, err := ParseIdentity(
		strings.ToUpper(hexString(identity.ChainID[:])),
		hexString(identity.AppHash[:]),
	)
	if err != nil {
		t.Fatalf("parse identity: %v", err)
	}
	if parsed != identity {
		t.Fatal("parsed identity mismatch")
	}
	if parsed.CometChainID() !=
		"ps-AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8" {
		t.Fatalf("unexpected CometBFT chain ID %q", parsed.CometChainID())
	}
	for _, values := range [][2]string{
		{"", hexString(identity.AppHash[:])},
		{strings.Repeat("z", 64), hexString(identity.AppHash[:])},
		{hexString(identity.ChainID[:]), "00"},
	} {
		if _, err := ParseIdentity(values[0], values[1]); err == nil {
			t.Fatalf("accepted invalid identity %#v", values)
		}
	}
}

func TestEnsureFreshAndRepeated(t *testing.T) {
	home := filepath.Join(t.TempDir(), "node")
	identity := testIdentity()
	if err := Ensure(home, identity, testEndpoints(), ProtocolV1); err != nil {
		t.Fatalf("fresh ensure: %v", err)
	}

	configPath := filepath.Join(
		home, cfg.DefaultConfigDir, cfg.DefaultConfigFileName)
	genesisPath := filepath.Join(
		home, cfg.DefaultConfigDir, cfg.DefaultGenesisJSONName)
	validatorKeyPath := filepath.Join(
		home, cfg.DefaultConfigDir, cfg.DefaultPrivValKeyName)
	validatorStatePath := filepath.Join(
		home, cfg.DefaultDataDir, cfg.DefaultPrivValStateName)
	nodeKeyPath := filepath.Join(
		home, cfg.DefaultConfigDir, cfg.DefaultNodeKeyName)

	for _, path := range []string{
		home,
		filepath.Join(home, cfg.DefaultConfigDir),
		filepath.Join(home, cfg.DefaultDataDir),
	} {
		requireMode(t, path, 0o700)
	}
	for _, path := range []string{
		validatorKeyPath, validatorStatePath, nodeKeyPath,
	} {
		requireMode(t, path, 0o600)
	}
	requireMode(t, configPath, 0o644)
	requireMode(t, genesisPath, 0o644)

	document, err := readGenesis(genesisPath)
	if err != nil {
		t.Fatalf("read generated genesis: %v", err)
	}
	if document.ChainID != identity.CometChainID() ||
		document.InitialHeight != 1 ||
		!bytes.Equal(document.AppHash, identity.AppHash[:]) ||
		!bytes.Equal(document.AppState, []byte(appStateV1)) {
		t.Fatal("generated genesis identity mismatch")
	}
	if document.ConsensusParams.ABCI.VoteExtensionsEnableHeight != 0 {
		t.Fatal("vote extensions were enabled")
	}

	configBytes := readFile(t, configPath)
	for _, expected := range []string{
		`proxy_app = "tcp://127.0.0.1:27658"`,
		`laddr = "tcp://127.0.0.1:27657"`,
		`laddr = "tcp://127.0.0.1:27656"`,
		`type = "flood"`,
		`enabled = false`,
		`timeout_commit = "3s"`,
		`skip_timeout_commit = false`,
		`create_empty_blocks = false`,
	} {
		if !bytes.Contains(configBytes, []byte(expected)) {
			t.Fatalf("generated config lacks %q", expected)
		}
	}

	before := map[string][]byte{
		configPath:         configBytes,
		genesisPath:        readFile(t, genesisPath),
		validatorKeyPath:   readFile(t, validatorKeyPath),
		validatorStatePath: readFile(t, validatorStatePath),
		nodeKeyPath:        readFile(t, nodeKeyPath),
	}
	if err := Ensure(home, identity, testEndpoints(), ProtocolV1); err != nil {
		t.Fatalf("repeated ensure: %v", err)
	}
	for path, expected := range before {
		if actual := readFile(t, path); !bytes.Equal(actual, expected) {
			t.Fatalf("repeated ensure changed %s", path)
		}
	}
}

func TestEnsureRejectsDivergentGenesis(t *testing.T) {
	home := filepath.Join(t.TempDir(), "node")
	identity := testIdentity()
	if err := Ensure(home, identity, testEndpoints(), ProtocolV1); err != nil {
		t.Fatalf("fresh ensure: %v", err)
	}
	genesisPath := filepath.Join(
		home, cfg.DefaultConfigDir, cfg.DefaultGenesisJSONName)
	original := readFile(t, genesisPath)

	changedRoot := identity
	changedRoot.AppHash[0] ^= 1
	if err := Ensure(home, changedRoot, testEndpoints(), ProtocolV1); err == nil ||
		!strings.Contains(err.Error(), "genesis differs") {
		t.Fatalf("changed root error = %v", err)
	}
	if !bytes.Equal(readFile(t, genesisPath), original) {
		t.Fatal("changed-root refusal modified genesis")
	}

	changedChain := identity
	changedChain.ChainID[0] ^= 1
	if err := Ensure(
		home, changedChain, testEndpoints(), ProtocolV1); err == nil ||
		!strings.Contains(err.Error(), "genesis differs") {
		t.Fatalf("changed chain error = %v", err)
	}
	if !bytes.Equal(readFile(t, genesisPath), original) {
		t.Fatal("changed-chain refusal modified genesis")
	}
}

func TestEnsureRejectsMalformedExistingGenesis(t *testing.T) {
	home := filepath.Join(t.TempDir(), "node")
	identity := testIdentity()
	if err := Ensure(home, identity, testEndpoints(), ProtocolV1); err != nil {
		t.Fatalf("fresh ensure: %v", err)
	}
	genesisPath := filepath.Join(
		home, cfg.DefaultConfigDir, cfg.DefaultGenesisJSONName)
	malformed := []byte(`{"chain_id":`)
	if err := os.WriteFile(genesisPath, malformed, 0o644); err != nil {
		t.Fatalf("corrupt genesis: %v", err)
	}
	if err := Ensure(home, identity, testEndpoints(), ProtocolV1); err == nil ||
		!strings.Contains(err.Error(), "decode genesis") {
		t.Fatalf("malformed genesis error = %v", err)
	}
	if !bytes.Equal(readFile(t, genesisPath), malformed) {
		t.Fatal("malformed-genesis refusal modified genesis")
	}
}

func TestEnsureRejectsInvalidInputs(t *testing.T) {
	identity := testIdentity()
	if err := Ensure(
		"relative", identity, testEndpoints(), ProtocolV1); err == nil {
		t.Fatal("relative home accepted")
	}
	if err := Ensure(
		string(filepath.Separator), identity, testEndpoints(),
		ProtocolV1); err == nil {
		t.Fatal("root home accepted")
	}
	if err := Ensure(
		filepath.Join(t.TempDir(), "node"), identity, Endpoints{},
		ProtocolV1); err == nil {
		t.Fatal("missing endpoints accepted")
	}

	partialHome := filepath.Join(t.TempDir(), "partial")
	keyPath := filepath.Join(
		partialHome, cfg.DefaultConfigDir, cfg.DefaultPrivValKeyName)
	if err := os.MkdirAll(filepath.Dir(keyPath), 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(keyPath, []byte("{}"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := Ensure(
		partialHome, identity, testEndpoints(), ProtocolV1); err == nil ||
		!strings.Contains(err.Error(), "pair is incomplete") {
		t.Fatalf("partial validator error = %v", err)
	}
}

func hexString(value []byte) string {
	const alphabet = "0123456789abcdef"
	encoded := make([]byte, len(value)*2)
	for index, current := range value {
		encoded[index*2] = alphabet[current>>4]
		encoded[index*2+1] = alphabet[current&0x0f]
	}
	return string(encoded)
}

// The genesis application state is what refuses a node started against a
// version-one genesis and a version-eight engine, so it must be the one thing
// a home initialized for a given version differs by.
func TestProtocolVersionSelectsTheGenesisApplicationState(t *testing.T) {
	for protocol, expected := range map[ProtocolVersion]string{
		ProtocolV1: appStateV1,
		ProtocolV7: appStateV7,
		ProtocolV8: appStateV8,
	} {
		state, err := protocol.appState()
		if err != nil || state != expected {
			t.Fatalf("version %d application state = %q, %v",
				uint8(protocol), state, err)
		}
	}
	if _, err := ProtocolVersion(6).appState(); err == nil {
		t.Fatal("an unbridged protocol version produced a genesis")
	}

	home := filepath.Join(t.TempDir(), "node")
	identity := testIdentity()
	if err := Ensure(home, identity, testEndpoints(), ProtocolV7); err != nil {
		t.Fatalf("fresh version-seven ensure: %v", err)
	}
	genesisPath := filepath.Join(
		home, cfg.DefaultConfigDir, cfg.DefaultGenesisJSONName)
	document, err := readGenesis(genesisPath)
	if err != nil {
		t.Fatalf("read generated genesis: %v", err)
	}
	if !bytes.Equal(document.AppState, []byte(appStateV7)) {
		t.Fatalf("version-seven genesis application state = %q",
			document.AppState)
	}
	// The same home re-ensured for another version is a different genesis,
	// and an exact-validating initializer must say so rather than adopt it.
	for _, other := range []ProtocolVersion{ProtocolV1, ProtocolV8} {
		if err := Ensure(
			home, identity, testEndpoints(), other); err == nil {
			t.Fatalf("a version-%d genesis replaced a version-seven home",
				uint8(other))
		}
	}
}

// The three application states must be three distinct strings. Nothing above
// would catch two versions sharing one: every check there compares a version's
// state against the same constant `appState` returned for it, so a rebound
// copy that forgot its own constant would agree with itself.
func TestTheThreeApplicationStatesAreDistinct(t *testing.T) {
	expected := map[ProtocolVersion]string{
		ProtocolV1: `"protocol-stack-v1"`,
		ProtocolV7: `"protocol-stack-v7"`,
		ProtocolV8: `"protocol-stack-v8"`,
	}
	for protocol, want := range expected {
		state, err := protocol.appState()
		if err != nil || state != want {
			t.Fatalf("version %d application state = %q, %v, want %q",
				uint8(protocol), state, err, want)
		}
	}
}

// A home initialized for version eight carries version eight's application
// state, which is the string `ApplicationV8::init_chain` accepts and the one
// it refuses version seven's in favour of.
func TestAVersionEightHomeCarriesVersionEightsApplicationState(t *testing.T) {
	home := filepath.Join(t.TempDir(), "node")
	identity := testIdentity()
	if err := Ensure(home, identity, testEndpoints(), ProtocolV8); err != nil {
		t.Fatalf("fresh version-eight ensure: %v", err)
	}
	document, err := readGenesis(filepath.Join(
		home, cfg.DefaultConfigDir, cfg.DefaultGenesisJSONName))
	if err != nil {
		t.Fatalf("read generated genesis: %v", err)
	}
	if !bytes.Equal(document.AppState, []byte(appStateV8)) {
		t.Fatalf("version-eight genesis application state = %q",
			document.AppState)
	}
	if err := Ensure(
		home, identity, testEndpoints(), ProtocolV7); err == nil {
		t.Fatal("a version-seven genesis replaced a version-eight home")
	}
}

func TestParseProtocolVersion(t *testing.T) {
	for value, expected := range map[uint]ProtocolVersion{
		1: ProtocolV1,
		7: ProtocolV7,
		8: ProtocolV8,
	} {
		parsed, err := ParseProtocolVersion(value)
		if err != nil || parsed != expected {
			t.Fatalf("ParseProtocolVersion(%d) = %d, %v", value, parsed, err)
		}
	}
	// 257 truncates to one in a byte and 264 to eight; neither may be
	// admitted as the version it truncates to.
	for _, value := range []uint{0, 2, 6, 9, 256, 257, 263, 264} {
		if _, err := ParseProtocolVersion(value); err == nil {
			t.Fatalf("ParseProtocolVersion(%d) was accepted", value)
		}
	}
}
