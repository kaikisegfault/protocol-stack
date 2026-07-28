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
	if err := Ensure(home, identity, testEndpoints()); err != nil {
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
		!bytes.Equal(document.AppState, []byte(appState)) {
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
	if err := Ensure(home, identity, testEndpoints()); err != nil {
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
	if err := Ensure(home, identity, testEndpoints()); err != nil {
		t.Fatalf("fresh ensure: %v", err)
	}
	genesisPath := filepath.Join(
		home, cfg.DefaultConfigDir, cfg.DefaultGenesisJSONName)
	original := readFile(t, genesisPath)

	changedRoot := identity
	changedRoot.AppHash[0] ^= 1
	if err := Ensure(home, changedRoot, testEndpoints()); err == nil ||
		!strings.Contains(err.Error(), "genesis differs") {
		t.Fatalf("changed root error = %v", err)
	}
	if !bytes.Equal(readFile(t, genesisPath), original) {
		t.Fatal("changed-root refusal modified genesis")
	}

	changedChain := identity
	changedChain.ChainID[0] ^= 1
	if err := Ensure(home, changedChain, testEndpoints()); err == nil ||
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
	if err := Ensure(home, identity, testEndpoints()); err != nil {
		t.Fatalf("fresh ensure: %v", err)
	}
	genesisPath := filepath.Join(
		home, cfg.DefaultConfigDir, cfg.DefaultGenesisJSONName)
	malformed := []byte(`{"chain_id":`)
	if err := os.WriteFile(genesisPath, malformed, 0o644); err != nil {
		t.Fatalf("corrupt genesis: %v", err)
	}
	if err := Ensure(home, identity, testEndpoints()); err == nil ||
		!strings.Contains(err.Error(), "decode genesis") {
		t.Fatalf("malformed genesis error = %v", err)
	}
	if !bytes.Equal(readFile(t, genesisPath), malformed) {
		t.Fatal("malformed-genesis refusal modified genesis")
	}
}

func TestEnsureRejectsInvalidInputs(t *testing.T) {
	identity := testIdentity()
	if err := Ensure("relative", identity, testEndpoints()); err == nil {
		t.Fatal("relative home accepted")
	}
	if err := Ensure(string(filepath.Separator), identity, testEndpoints()); err == nil {
		t.Fatal("root home accepted")
	}
	if err := Ensure(filepath.Join(t.TempDir(), "node"), identity, Endpoints{}); err == nil {
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
	if err := Ensure(partialHome, identity, testEndpoints()); err == nil ||
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
