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

// CheckHealth performs one complete four-replica health observation.
func CheckHealth(
	ctx context.Context,
	devnet nodeconfig.Devnet,
) (NetworkHealth, error) {
	client := newRPCClient()
	statuses := make([]statusResult, nodeconfig.DevnetNodeCount)
	networks := make([]netInfoResult, nodeconfig.DevnetNodeCount)
	heads := make([]ApplicationHead, nodeconfig.DevnetNodeCount)
	validators := make([]validatorsResult, nodeconfig.DevnetNodeCount)
	var infos [nodeconfig.DevnetNodeCount]abciInfoResult

	for index, node := range devnet.Nodes {
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
			&statuses[index],
		); err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		if err := client.call(
			ctx, node.RPCPort, "net_info", map[string]any{},
			&networks[index],
		); err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		if err := client.call(
			ctx, node.RPCPort, "abci_info", map[string]any{},
			&infos[index],
		); err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		head, err := ReadApplicationHead(ctx, node.ApplicationSocket)
		if err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		heads[index] = head
	}

	health, err := compareHeads(statuses, infos, heads)
	if err != nil {
		return NetworkHealth{}, err
	}
	if health.Height == 0 {
		if err := compareGenesisValidators(devnet); err != nil {
			return NetworkHealth{}, err
		}
	} else {
		for index, node := range devnet.Nodes {
			if err := client.call(
				ctx,
				node.RPCPort,
				"validators",
				map[string]any{
					"height":   strconv.FormatUint(health.Height, 10),
					"page":     "1",
					"per_page": "100",
				},
				&validators[index],
			); err != nil {
				return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
			}
		}
		if err := compareValidators(validators); err != nil {
			return NetworkHealth{}, err
		}
	}
	if err := comparePeers(statuses, networks); err != nil {
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

// WaitForHealth retries until one complete health observation succeeds.
func WaitForHealth(
	ctx context.Context,
	devnet nodeconfig.Devnet,
) (NetworkHealth, error) {
	var lastError error
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()
	for {
		health, err := CheckHealth(ctx, devnet)
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
