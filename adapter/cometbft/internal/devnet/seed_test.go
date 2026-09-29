package devnet

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

const seededOutput = "chain_id=" + identityChainID + "\n" +
	"height=86402\n" +
	"timestamp=1790259207579\n" +
	"app_hash=" + identityAppHash + "\n"

func TestParseSeededHeadReadsTheFourKeys(t *testing.T) {
	head, err := parseSeededHead([]byte(seededOutput))
	if err != nil {
		t.Fatal(err)
	}
	if head.Height != 86_402 || head.Timestamp != 1_790_259_207_579 ||
		head.ChainID[1] != 0x01 || head.AppHash[0] != 0xFF {
		t.Fatalf("seeded head = %+v", head)
	}
}

// The key set is exact, as for identity mode: genesis identity output is not
// a seeded head, and neither is a seeded head with anything added.
func TestParseSeededHeadRefusesAnyOtherKeySet(t *testing.T) {
	for name, output := range map[string]string{
		"genesis identity": identityV9,
		"missing stamp": strings.Replace(
			seededOutput, "timestamp=1790259207579\n", "", 1),
		"extra key":     seededOutput + "genesis_timestamp=0\n",
		"duplicate key": seededOutput + "height=86402\n",
		"height zero":   strings.Replace(seededOutput, "=86402", "=0", 1),
	} {
		if _, err := parseSeededHead([]byte(output)); err == nil {
			t.Fatalf("%s: accepted as a seeded head", name)
		}
	}
}

// fakeApplication writes a script standing in for `--seed`: it creates the
// database it is given and prints `output`. A seed that must not run gets a
// script that fails, so running it at all is the failure.
func fakeApplication(t *testing.T, output string, succeed bool) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "application")
	body := "#!/bin/sh\nexit 7\n"
	if succeed {
		body = "#!/bin/sh\n: > \"$2\"\nprintf '%s' '" + output + "'\n"
	}
	if err := os.WriteFile(path, []byte(body), 0o700); err != nil {
		t.Fatal(err)
	}
	return path
}

func seededDevnet(t *testing.T) nodeconfig.Devnet {
	t.Helper()
	root := t.TempDir()
	devnet, err := nodeconfig.NewDevnetWithSocketRoot(
		filepath.Join(root, "devnet"), filepath.Join(root, "sockets"),
		nodeconfig.DefaultDevnetBaseP2PPort)
	if err != nil {
		t.Fatal(err)
	}
	for _, node := range devnet.Nodes {
		if err := os.MkdirAll(node.Root, 0o700); err != nil {
			t.Fatal(err)
		}
	}
	return devnet
}

func storesPresent(t *testing.T, devnet nodeconfig.Devnet) int {
	t.Helper()
	count := 0
	for _, node := range devnet.Nodes {
		exists, err := storeExists(node.Database)
		if err != nil {
			t.Fatal(err)
		}
		if exists {
			count++
		}
	}
	return count
}

func TestSeedStoresSeedsAllFourOrNone(t *testing.T) {
	head, err := parseSeededHead([]byte(seededOutput))
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	devnet := seededDevnet(t)
	seeding := fakeApplication(t, seededOutput, true)
	if err := seedStores(ctx, devnet, seeding, "/genesis", "/snapshot",
		head); err != nil {
		t.Fatalf("first start: %v", err)
	}
	if count := storesPresent(t, devnet); count != nodeconfig.DevnetNodeCount {
		t.Fatalf("first start seeded %d stores", count)
	}
	// A restart: every store has moved on, and none is seeded again.
	refusing := fakeApplication(t, "", false)
	if err := seedStores(ctx, devnet, refusing, "/genesis", "/snapshot",
		head); err != nil {
		t.Fatalf("a restart seeded again: %v", err)
	}

	partial := seededDevnet(t)
	if err := os.WriteFile(partial.Nodes[2].Database, nil, 0o600); err != nil {
		t.Fatal(err)
	}
	err = seedStores(ctx, partial, refusing, "/genesis", "/snapshot", head)
	if err == nil || !strings.Contains(err.Error(), "incomplete set") {
		t.Fatalf("a partial set of stores was accepted: %v", err)
	}
}

// Every store must report the head the genesis was derived from. A seed that
// reports another is a snapshot changed between inspection and seeding, and
// the replica would never agree with the engine's genesis.
func TestSeedStoresRefusesAnotherHead(t *testing.T) {
	head, err := parseSeededHead([]byte(seededOutput))
	if err != nil {
		t.Fatal(err)
	}
	other := strings.Replace(seededOutput, "=86402", "=86403", 1)
	err = seedStores(context.Background(), seededDevnet(t),
		fakeApplication(t, other, true), "/genesis", "/snapshot", head)
	if err == nil || !strings.Contains(err.Error(), "not derived from") {
		t.Fatalf("a store seeded at another head was accepted: %v", err)
	}
}

func TestInspectLaunchWithoutASnapshotIsTheChainsGenesis(t *testing.T) {
	launch, err := inspectLaunch(context.Background(),
		fakeApplication(t, "", false), "/genesis", "")
	if err != nil {
		t.Fatal(err)
	}
	if _, seeded := launch.Seed(); seeded {
		t.Fatal("a launch without a snapshot is seeded")
	}
}
