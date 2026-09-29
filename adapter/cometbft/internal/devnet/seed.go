package devnet

import (
	"context"
	"errors"
	"fmt"
	"os"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

// A seeded network (ADR 0097): four stores begun from one snapshot, and an
// engine genesis derived from the head the snapshot holds.
//
// **The snapshot is an input to every start, not only the first.** The engine's
// genesis names the seeded height, root, and stamp, and a restart must derive
// the same document to compare the homes against. After the first block the
// stores are past the seeded head and cannot say what it was, so the launcher
// asks the snapshot again, through the application's own gates.

// inspectLaunch is where a network's engine begins: the chain's own genesis
// when no snapshot is named, and otherwise the block after the snapshot's head.
func inspectLaunch(
	ctx context.Context,
	application string,
	genesis string,
	snapshot string,
) (nodeconfig.Launch, error) {
	if snapshot == "" {
		return nodeconfig.Launch{}, nil
	}
	head, err := InspectSeed(ctx, application, genesis, snapshot)
	if err != nil {
		return nodeconfig.Launch{}, err
	}
	return nodeconfig.SeededLaunch(head), nil
}

// InspectSeed reads the head a snapshot would seed, checked by the seed's own
// rules, without writing a store.
func InspectSeed(
	ctx context.Context,
	application string,
	genesis string,
	snapshot string,
) (nodeconfig.SeededHead, error) {
	output, err := runApplication(ctx, "inspect seed",
		application, "--inspect-seed", genesis, snapshot)
	if err != nil {
		return nodeconfig.SeededHead{}, err
	}
	return parseSeededHead(output)
}

// parseSeededHead reads `--seed` and `--inspect-seed` output, whose key set is
// exact: the chain identity, the height, the stamp, and the root.
func parseSeededHead(output []byte) (nodeconfig.SeededHead, error) {
	values, err := readFields(output, "seeded head",
		"chain_id", "height", "timestamp", "app_hash")
	if err != nil {
		return nodeconfig.SeededHead{}, err
	}
	head, err := nodeconfig.ParseSeededHead(values["chain_id"],
		values["height"], values["timestamp"], values["app_hash"])
	if err != nil {
		return nodeconfig.SeededHead{}, fmt.Errorf(
			"application seeded head: %w", err)
	}
	return head, nil
}

// seedStores gives every replica its store from the snapshot, or finds that
// every replica already has one.
//
// **All four or none, as for the homes.** Four stores are a restart, which
// seeds nothing: the stores have moved on, and the engine's handshake compares
// each one's head with its own. No store is a first start, which seeds all
// four and requires each to report exactly the head the genesis was derived
// from. Anything between is refused, because a replica started without a
// store would create one at height zero and never join.
func seedStores(
	ctx context.Context,
	devnet nodeconfig.Devnet,
	application string,
	genesis string,
	snapshot string,
	head nodeconfig.SeededHead,
) error {
	present := 0
	for _, node := range devnet.Nodes {
		exists, err := storeExists(node.Database)
		if err != nil {
			return fmt.Errorf("node %d: %w", node.Index, err)
		}
		if exists {
			present++
		}
	}
	switch present {
	case nodeconfig.DevnetNodeCount:
		return nil
	case 0:
	default:
		return errors.New("devnet contains an incomplete set of replica ledgers")
	}
	for _, node := range devnet.Nodes {
		output, err := runApplication(ctx,
			fmt.Sprintf("seed node %d", node.Index),
			application, "--seed", node.Database, genesis, snapshot)
		if err != nil {
			return err
		}
		seeded, err := parseSeededHead(output)
		if err != nil {
			return fmt.Errorf("node %d: %w", node.Index, err)
		}
		if seeded != head {
			return fmt.Errorf(
				"node %d was seeded at a head its genesis was not derived from",
				node.Index)
		}
	}
	return nil
}

func storeExists(path string) (bool, error) {
	info, err := os.Lstat(path)
	if errors.Is(err, os.ErrNotExist) {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("inspect %s: %w", path, err)
	}
	if !info.Mode().IsRegular() {
		return false, fmt.Errorf("%s is not a regular file", path)
	}
	return true, nil
}
