package nodeconfig

import (
	"bytes"
	"encoding/hex"
	"errors"
	"math"
	"os"
	"strconv"
	"strings"
	"testing"

	cfg "github.com/cometbft/cometbft/config"
	"github.com/cometbft/cometbft/crypto/merkle"
	sm "github.com/cometbft/cometbft/state"
)

const (
	seededHeight = 86_402
	// A stamp later than the chain's genesis stamp, and deliberately not a
	// whole second, for the reason testStampMillis gives.
	seededStampMillis = testStampMillis + 259_207_456
)

func testSeededHead() SeededHead {
	head := SeededHead{
		ChainID:   testIdentity().ChainID,
		Height:    seededHeight,
		Timestamp: seededStampMillis,
	}
	for index := range head.AppHash {
		head.AppHash[index] = byte(0xA0 + index%16)
	}
	return head
}

func hexOf(value Hash) string {
	return strings.ToUpper(hex.EncodeToString(value[:]))
}

func TestParseSeededHeadReadsThePrintedHead(t *testing.T) {
	expected := testSeededHead()
	head, err := ParseSeededHead(hexOf(expected.ChainID),
		strconv.Itoa(seededHeight),
		strconv.FormatUint(seededStampMillis, 10),
		hexOf(expected.AppHash))
	if err != nil || head != expected {
		t.Fatalf("seeded head = %+v, %v", head, err)
	}
}

func TestParseSeededHeadRefusesWhatCannotBeginANetwork(t *testing.T) {
	chain := hexOf(testIdentity().ChainID)
	root := hexOf(testSeededHead().AppHash)
	stamp := strconv.FormatUint(seededStampMillis, 10)
	for name, fields := range map[string][4]string{
		// A height-zero head is a genesis, and the engine would call
		// InitChain for it rather than start above it.
		"height zero":         {chain, "0", stamp, root},
		"height leading zero": {chain, "086402", stamp, root},
		"height signed":       {chain, "+86402", stamp, root},
		"height past int64": {chain,
			strconv.FormatUint(math.MaxInt64, 10), stamp, root},
		"stamp past range":  {chain, "86402", "253402300800000", root},
		"stamp not decimal": {chain, "86402", "0x10", root},
		"short chain ID":    {"00", "86402", stamp, root},
		"root not hex":      {chain, "86402", stamp, strings.Repeat("z", 64)},
	} {
		if _, err := ParseSeededHead(
			fields[0], fields[1], fields[2], fields[3]); err == nil {
			t.Fatalf("%s: a seeded head was accepted", name)
		}
	}
	// The largest height whose successor the engine can still name.
	if _, err := ParseSeededHead(chain,
		strconv.FormatUint(math.MaxInt64-1, 10), stamp, root); err != nil {
		t.Fatalf("the largest launchable height was refused: %v", err)
	}
}

// **The three values come from one head, and only those three change.** The
// chain ID, application state, validators, and consensus parameters are the
// chain's own, so a seeded genesis differs from the chain's genesis in exactly
// the fields a launch height is about.
func TestASeededDevnetBeginsAfterTheSeededHead(t *testing.T) {
	identity := testIdentityV9(t, testStampMillis)
	head := testSeededHead()
	seeded := mustDevnet(t)
	if err := seeded.EnsureLaunch(
		identity, ProtocolV9, SeededLaunch(head)); err != nil {
		t.Fatalf("seeded devnet: %v", err)
	}
	for _, node := range seeded.Nodes {
		document, err := readGenesis(genesisPathOf(node.Home))
		if err != nil {
			t.Fatalf("node %d: %v", node.Index, err)
		}
		if document.InitialHeight != seededHeight+1 ||
			!bytes.Equal(document.AppHash, head.AppHash[:]) ||
			document.GenesisTime.UnixMilli() != seededStampMillis ||
			document.GenesisTime.Nanosecond()%1_000_000 != 0 ||
			document.ChainID != identity.CometChainID() ||
			!bytes.Equal(document.AppState, []byte(appStateV9)) ||
			len(document.Validators) != DevnetNodeCount {
			t.Fatalf("node %d seeded genesis mismatch: %+v", node.Index, document)
		}
	}
	if err := seeded.EnsureLaunch(
		identity, ProtocolV9, SeededLaunch(head)); err != nil {
		t.Fatalf("a seeded devnet restarted from the same head: %v", err)
	}
}

// A home written for one launch is refused by every other, and the refusal
// changes nothing: each of these is an operator naming a different network
// than the one on disk.
func TestASeededHomeRefusesEveryOtherLaunch(t *testing.T) {
	identity := testIdentityV9(t, testStampMillis)
	head := testSeededHead()
	devnet := mustDevnet(t)
	if err := devnet.EnsureLaunch(
		identity, ProtocolV9, SeededLaunch(head)); err != nil {
		t.Fatal(err)
	}
	before, err := os.ReadFile(genesisPathOf(devnet.Nodes[0].Home))
	if err != nil {
		t.Fatal(err)
	}
	later := head
	later.Height++
	moved := head
	moved.Timestamp++
	rerooted := head
	rerooted.AppHash[0] ^= 0x01
	for name, launch := range map[string]Launch{
		"the chain's own genesis": {},
		"a later height":          SeededLaunch(later),
		"a later stamp":           SeededLaunch(moved),
		"another root":            SeededLaunch(rerooted),
	} {
		err := devnet.EnsureLaunch(identity, ProtocolV9, launch)
		if err == nil || !strings.Contains(err.Error(), "genesis differs") {
			t.Fatalf("%s: a seeded home was reused: %v", name, err)
		}
	}
	after, err := os.ReadFile(genesisPathOf(devnet.Nodes[0].Home))
	if err != nil || !bytes.Equal(before, after) {
		t.Fatalf("a refused launch rewrote the genesis: %v", err)
	}

	unseeded := mustDevnet(t)
	if err := unseeded.Ensure(identity, ProtocolV9); err != nil {
		t.Fatal(err)
	}
	err = unseeded.EnsureLaunch(identity, ProtocolV9, SeededLaunch(head))
	if err == nil || !strings.Contains(err.Error(), "genesis differs") {
		t.Fatalf("a genesis home was reused for a seeded launch: %v", err)
	}
}

// A seed for another chain, a seed under a version with no stamp, and a head
// the engine could not start above are all refused before a key is written.
func TestARefusedSeededLaunchWritesNothing(t *testing.T) {
	identity := testIdentityV9(t, testStampMillis)
	foreign := testSeededHead()
	foreign.ChainID[0] ^= 0x01
	zero := testSeededHead()
	zero.Height = 0
	overflow := testSeededHead()
	overflow.Height = math.MaxInt64
	late := testSeededHead()
	late.Timestamp = maxGenesisTimestampMillis + 1
	for name, refusal := range map[string]struct {
		identity Identity
		protocol ProtocolVersion
		head     SeededHead
		message  string
	}{
		"another chain": {identity, ProtocolV9, foreign, "another chain"},
		"version one": {testIdentity(), ProtocolV1, testSeededHead(),
			"cannot launch from a seeded head"},
		"height zero":      {identity, ProtocolV9, zero, "cannot begin"},
		"height overflow":  {identity, ProtocolV9, overflow, "cannot begin"},
		"stamp past range": {identity, ProtocolV9, late, "range"},
	} {
		devnet := mustDevnet(t)
		err := devnet.EnsureLaunch(
			refusal.identity, refusal.protocol, SeededLaunch(refusal.head))
		if err == nil || !strings.Contains(err.Error(), refusal.message) {
			t.Fatalf("%s: refused for another reason: %v", name, err)
		}
		if _, err := os.Lstat(devnet.Root); !errors.Is(err, os.ErrNotExist) {
			t.Fatalf("%s: a refused launch wrote %s", name, devnet.Root)
		}
	}
}

func loadEngineState(t *testing.T, home string) sm.State {
	t.Helper()
	config := cfg.DefaultConfig().SetRoot(home)
	database, err := cfg.DefaultDBProvider(
		&cfg.DBContext{ID: "state", Config: config})
	if err != nil {
		t.Fatal(err)
	}
	defer database.Close()
	state, err := sm.NewStore(database, sm.StoreOptions{}).Load()
	if err != nil {
		t.Fatal(err)
	}
	return state
}

// **A seeded home carries the engine's genesis state before the engine first
// starts**, because CometBFT v0.39.4 saves it only on the InitChain path, which
// a seeded network never takes. A launch at the chain's genesis writes none,
// and a state the engine has moved on is never replaced.
func TestASeededHomeCarriesTheEnginesGenesisState(t *testing.T) {
	identity := testIdentityV9(t, testStampMillis)
	head := testSeededHead()
	devnet := mustDevnet(t)
	if err := devnet.EnsureLaunch(
		identity, ProtocolV9, SeededLaunch(head)); err != nil {
		t.Fatal(err)
	}
	for _, node := range devnet.Nodes {
		state := loadEngineState(t, node.Home)
		if state.IsEmpty() || state.LastBlockHeight != 0 ||
			state.InitialHeight != seededHeight+1 ||
			!bytes.Equal(state.AppHash, head.AppHash[:]) ||
			state.LastBlockTime.UnixMilli() != seededStampMillis ||
			state.Validators.Size() != DevnetNodeCount ||
			!bytes.Equal(state.LastResultsHash, merkle.HashFromByteSlices(nil)) {
			t.Fatalf("node %d engine state = %+v", node.Index, state)
		}
	}

	// The engine's own state after a block, which a restart must keep.
	home := devnet.Nodes[0].Home
	moved := loadEngineState(t, home)
	moved.LastBlockHeight = seededHeight + 1
	moved.LastValidators = moved.Validators.Copy()
	config := cfg.DefaultConfig().SetRoot(home)
	database, err := cfg.DefaultDBProvider(
		&cfg.DBContext{ID: "state", Config: config})
	if err != nil {
		t.Fatal(err)
	}
	if err := sm.NewStore(database, sm.StoreOptions{}).Save(moved); err != nil {
		t.Fatal(err)
	}
	if err := database.Close(); err != nil {
		t.Fatal(err)
	}
	if err := devnet.EnsureLaunch(
		identity, ProtocolV9, SeededLaunch(head)); err != nil {
		t.Fatal(err)
	}
	if state := loadEngineState(t, home); state.LastBlockHeight != seededHeight+1 {
		t.Fatalf("a restart replaced the engine's state at height %d",
			state.LastBlockHeight)
	}

	unseeded := mustDevnet(t)
	if err := unseeded.Ensure(identity, ProtocolV9); err != nil {
		t.Fatal(err)
	}
	if !loadEngineState(t, unseeded.Nodes[0].Home).IsEmpty() {
		t.Fatal("a launch at the chain's genesis wrote an engine state")
	}
}
