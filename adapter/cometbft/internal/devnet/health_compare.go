package devnet

import (
	"bytes"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"fmt"
	"sort"
	"strconv"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

func compareHeads(
	statuses []statusResult,
	infos [nodeconfig.DevnetNodeCount]abciInfoResult,
) (NetworkHealth, error) {
	var expected NetworkHealth
	for index := range nodeconfig.DevnetNodeCount {
		statusHeight, err := parseUint(
			"latest block height", statuses[index].SyncInfo.LatestBlockHeight)
		if err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		headerHash, err := hex.DecodeString(statuses[index].SyncInfo.LatestAppHash)
		if err != nil {
			return NetworkHealth{}, fmt.Errorf(
				"node %d latest application hash: %w", index, err)
		}
		infoHeight, err := parseUint(
			"ABCI height", infos[index].Response.LastBlockHeight)
		if err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		infoRoot, err := base64.StdEncoding.DecodeString(
			infos[index].Response.LastBlockAppHash)
		if err != nil || len(infoRoot) != len(nodeconfig.Hash{}) {
			return NetworkHealth{}, fmt.Errorf(
				"node %d returned invalid ABCI application root", index)
		}
		if statusHeight != infoHeight ||
			(statusHeight == 0 && len(headerHash) != 0) ||
			(statusHeight > 0 && len(headerHash) != len(nodeconfig.Hash{})) {
			return NetworkHealth{}, fmt.Errorf(
				"node %d returned inconsistent head metadata", index)
		}
		var root nodeconfig.Hash
		copy(root[:], infoRoot)
		current := NetworkHealth{
			ChainID:         statuses[index].NodeInfo.Network,
			Height:          infoHeight,
			ApplicationRoot: root,
			HeaderHeight:    statusHeight,
			HeaderAppHash:   headerHash,
		}
		if current.ChainID == "" || statuses[index].NodeInfo.ID == "" {
			return NetworkHealth{}, fmt.Errorf(
				"node %d omitted network identity", index)
		}
		if index == 0 {
			expected = current
		} else if current.ChainID != expected.ChainID ||
			current.Height != expected.Height ||
			current.ApplicationRoot != expected.ApplicationRoot ||
			current.HeaderHeight != expected.HeaderHeight ||
			!bytes.Equal(current.HeaderAppHash, expected.HeaderAppHash) {
			return NetworkHealth{}, errors.New(
				"validator replicas have not converged")
		}
	}
	return expected, nil
}

func comparePeers(statuses []statusResult, networks []netInfoResult) error {
	nodeIDs := make(map[string]struct{}, nodeconfig.DevnetNodeCount)
	for index, status := range statuses {
		if _, duplicate := nodeIDs[status.NodeInfo.ID]; duplicate {
			return errors.New("validator RPC node IDs are not distinct")
		}
		if status.NodeInfo.ID == "" {
			return fmt.Errorf("node %d omitted node ID", index)
		}
		nodeIDs[status.NodeInfo.ID] = struct{}{}
	}
	for index, network := range networks {
		count, err := parseUint("peer count", network.NPeers)
		if err != nil || count != nodeconfig.DevnetNodeCount-1 ||
			len(network.Peers) != nodeconfig.DevnetNodeCount-1 {
			return fmt.Errorf("node %d does not have exactly three peers", index)
		}
		expected := make(map[string]struct{}, nodeconfig.DevnetNodeCount-1)
		for id := range nodeIDs {
			if id != statuses[index].NodeInfo.ID {
				expected[id] = struct{}{}
			}
		}
		for _, peer := range network.Peers {
			if _, present := expected[peer.NodeInfo.ID]; !present {
				return fmt.Errorf("node %d reported unexpected peer", index)
			}
			delete(expected, peer.NodeInfo.ID)
		}
		if len(expected) != 0 {
			return fmt.Errorf("node %d omitted a direct peer", index)
		}
	}
	return nil
}

func compareValidators(results []validatorsResult) error {
	var expected []string
	for index, result := range results {
		if len(result.Validators) != nodeconfig.DevnetNodeCount {
			return fmt.Errorf(
				"node %d does not report four validators", index)
		}
		current := make([]string, 0, nodeconfig.DevnetNodeCount)
		for _, validator := range result.Validators {
			power, err := parseUint("validator power", validator.VotingPower)
			if err != nil || power != 10 || validator.Address == "" {
				return fmt.Errorf(
					"node %d returned invalid validator set", index)
			}
			current = append(current, validator.Address)
		}
		sort.Strings(current)
		if index == 0 {
			expected = current
		} else if !equalStrings(current, expected) {
			return errors.New("validator replicas report different validator sets")
		}
	}
	return nil
}

func equalStrings(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}

func parseUint(name, value string) (uint64, error) {
	result, err := strconv.ParseUint(value, 10, 64)
	if err != nil {
		return 0, fmt.Errorf("%s is invalid: %w", name, err)
	}
	return result, nil
}
