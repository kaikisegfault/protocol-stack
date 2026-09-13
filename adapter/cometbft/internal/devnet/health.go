package devnet

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"time"

	cfg "github.com/cometbft/cometbft/config"
	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

type statusResult struct {
	NodeInfo struct {
		ID      string `json:"id"`
		Network string `json:"network"`
	} `json:"node_info"`
	SyncInfo struct {
		LatestBlockHeight string `json:"latest_block_height"`
		LatestAppHash     string `json:"latest_app_hash"`
		CatchingUp        bool   `json:"catching_up"`
	} `json:"sync_info"`
}

type netInfoResult struct {
	NPeers string `json:"n_peers"`
	Peers  []struct {
		NodeInfo struct {
			ID string `json:"id"`
		} `json:"node_info"`
	} `json:"peers"`
}

type validatorsResult struct {
	BlockHeight string `json:"block_height"`
	Validators  []struct {
		Address     string `json:"address"`
		VotingPower string `json:"voting_power"`
	} `json:"validators"`
}

type abciInfoResult struct {
	Response struct {
		LastBlockHeight  string `json:"last_block_height"`
		LastBlockAppHash string `json:"last_block_app_hash"`
	} `json:"response"`
}

// NetworkHealth is the agreed current result of all four replicas.
type NetworkHealth struct {
	ChainID         string
	Height          uint64
	ApplicationRoot nodeconfig.Hash
	HeaderHeight    uint64
	HeaderAppHash   []byte
}

// CheckHealth performs one complete health observation of a replica subset.
//
// Every replica named must be running and converged; every replica **not**
// named must be absent from the others' peer sets. Pass `AllReplicas()` for the
// whole network, which is what every caller wants except one that has
// deliberately stopped a replica.
func CheckHealth(
	ctx context.Context,
	devnet nodeconfig.Devnet,
	replicas Replicas,
) (NetworkHealth, error) {
	if err := replicas.validate(); err != nil {
		return NetworkHealth{}, err
	}
	client := newRPCClient()
	statuses := make([]statusResult, len(replicas))
	networks := make([]netInfoResult, len(replicas))
	validators := make([]validatorsResult, len(replicas))
	infos := make([]abciInfoResult, len(replicas))

	for position, index := range replicas {
		node := devnet.Nodes[index]
		var health map[string]any
		if err := client.call(
			ctx, node.RPCPort, "health", map[string]any{}, &health); err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		if len(health) != 0 {
			return NetworkHealth{}, fmt.Errorf(
				"node %d returned nonempty health result", index)
		}
		if err := client.call(
			ctx, node.RPCPort, "status", map[string]any{},
			&statuses[position],
		); err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		if err := client.call(
			ctx, node.RPCPort, "net_info", map[string]any{},
			&networks[position],
		); err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		if err := client.call(
			ctx, node.RPCPort, "abci_info", map[string]any{},
			&infos[position],
		); err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
	}

	health, err := compareHeads(replicas, statuses, infos)
	if err != nil {
		return NetworkHealth{}, err
	}
	if health.Height == 0 {
		// The genesis files are read from disk rather than from an RPC, so a
		// stopped replica's home is still there to be compared. All four are
		// compared whatever the subset is: a devnet whose homes disagree is
		// broken regardless of which processes happen to be running.
		if err := compareGenesisValidators(devnet); err != nil {
			return NetworkHealth{}, err
		}
	} else {
		for position, index := range replicas {
			if err := client.call(
				ctx,
				devnet.Nodes[index].RPCPort,
				"validators",
				map[string]any{
					"height":   strconv.FormatUint(health.Height, 10),
					"page":     "1",
					"per_page": "100",
				},
				&validators[position],
			); err != nil {
				return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
			}
		}
		if err := compareValidators(replicas, validators); err != nil {
			return NetworkHealth{}, err
		}
	}
	if err := comparePeers(replicas, statuses, networks); err != nil {
		return NetworkHealth{}, err
	}
	return health, nil
}

func compareGenesisValidators(devnet nodeconfig.Devnet) error {
	var expected []byte
	for nodeIndex, node := range devnet.Nodes {
		path := filepath.Join(
			node.Home, cfg.DefaultConfigDir, cfg.DefaultGenesisJSONName)
		encoded, err := os.ReadFile(path)
		if err != nil {
			return fmt.Errorf("node %d genesis: %w", nodeIndex, err)
		}
		if expected == nil {
			expected = encoded
		} else if !bytes.Equal(encoded, expected) {
			return errors.New("validator replicas have different genesis files")
		}
	}
	var document struct {
		Validators []struct {
			Address string `json:"address"`
			Power   string `json:"power"`
			Name    string `json:"name"`
		} `json:"validators"`
	}
	if err := json.Unmarshal(expected, &document); err != nil {
		return fmt.Errorf("decode common genesis: %w", err)
	}
	if len(document.Validators) != nodeconfig.DevnetNodeCount {
		return errors.New("common genesis does not contain four validators")
	}
	addresses := make(map[string]struct{}, nodeconfig.DevnetNodeCount)
	for index, validator := range document.Validators {
		if validator.Address == "" ||
			validator.Power != "10" ||
			validator.Name != fmt.Sprintf(
				"protocol-stack-m1-validator-%d", index) {
			return fmt.Errorf("common genesis validator %d is invalid", index)
		}
		if _, duplicate := addresses[validator.Address]; duplicate {
			return errors.New("common genesis validator addresses are not distinct")
		}
		addresses[validator.Address] = struct{}{}
	}
	return nil
}

// healthProbeTimeout bounds **one** health observation.
//
// An observation is a poll rather than a wait: the loops around it expect it to
// fail fast so they can try again, and a probe allowed to consume the caller's
// whole budget would turn a retry loop into a single attempt. Both loops use
// this one figure so they cannot drift, and naming it here is what lets
// `newRPCClient` impose no timeout of its own — see the comment there for the
// blocking call that a client-level cap silently broke.
const healthProbeTimeout = 3 * time.Second

// WaitForHealth retries until one complete health observation succeeds.
func WaitForHealth(
	ctx context.Context,
	devnet nodeconfig.Devnet,
	replicas Replicas,
) (NetworkHealth, error) {
	var lastError error
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()
	for {
		probeContext, cancel := context.WithTimeout(ctx, healthProbeTimeout)
		health, err := CheckHealth(probeContext, devnet, replicas)
		cancel()
		if err == nil {
			return health, nil
		}
		lastError = err
		select {
		case <-ctx.Done():
			return NetworkHealth{}, fmt.Errorf(
				"devnet health: %w (last observation: %v)",
				ctx.Err(), lastError)
		case <-ticker.C:
		}
	}
}
