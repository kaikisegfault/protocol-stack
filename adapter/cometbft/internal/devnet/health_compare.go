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
	replicas Replicas,
	statuses []statusResult,
	infos []abciInfoResult,
) (NetworkHealth, error) {
	var expected NetworkHealth
	for position, index := range replicas {
		if statuses[position].SyncInfo.CatchingUp {
			return NetworkHealth{}, fmt.Errorf(
				"node %d is still catching up", index)
		}
		statusHeight, err := parseUint(
			"latest block height", statuses[position].SyncInfo.LatestBlockHeight)
		if err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		headerHash, err := hex.DecodeString(
			statuses[position].SyncInfo.LatestAppHash)
		if err != nil {
			return NetworkHealth{}, fmt.Errorf(
				"node %d latest application hash: %w", index, err)
		}
		infoHeight, err := parseUint(
			"ABCI height", infos[position].Response.LastBlockHeight)
		if err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		infoRoot, err := base64.StdEncoding.DecodeString(
			infos[position].Response.LastBlockAppHash)
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
			ChainID:         statuses[position].NodeInfo.Network,
			Height:          infoHeight,
			ApplicationRoot: root,
			HeaderHeight:    statusHeight,
			HeaderAppHash:   headerHash,
		}
		if current.ChainID == "" || statuses[position].NodeInfo.ID == "" {
			return NetworkHealth{}, fmt.Errorf(
				"node %d omitted network identity", index)
		}
		if position == 0 {
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

// comparePeers requires each named replica to see exactly the others.
//
// The expected count follows the **subset**, not the topology, and that is what
// keeps the check sharp while a replica is down: three running replicas must
// each report two peers, so a stopped replica whose process is still gossiping
// is caught here rather than passing as an extra peer nobody counted.
func comparePeers(
	replicas Replicas,
	statuses []statusResult,
	networks []netInfoResult,
) error {
	nodeIDs := make(map[string]struct{}, len(replicas))
	for position, index := range replicas {
		status := statuses[position]
		if status.NodeInfo.ID == "" {
			return fmt.Errorf("node %d omitted node ID", index)
		}
		if _, duplicate := nodeIDs[status.NodeInfo.ID]; duplicate {
			return errors.New("validator RPC node IDs are not distinct")
		}
		nodeIDs[status.NodeInfo.ID] = struct{}{}
	}
	for position, index := range replicas {
		network := networks[position]
		count, err := parseUint("peer count", network.NPeers)
		if err != nil || count != uint64(len(replicas)-1) ||
			len(network.Peers) != len(replicas)-1 {
			return fmt.Errorf(
				"node %d does not have exactly %d peers",
				index, len(replicas)-1)
		}
		expected := make(map[string]struct{}, len(replicas)-1)
		for id := range nodeIDs {
			if id != statuses[position].NodeInfo.ID {
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

// compareValidators requires every named replica to report the same four.
//
// The validator **set** does not narrow with the subset: it comes from a
// genesis file four homes share, and stopping a process does not retire its
// validator. A run that reported three validators while one replica was down
// would mean the set had actually changed, which is a different and much
// larger event than a stopped process.
func compareValidators(replicas Replicas, results []validatorsResult) error {
	var expected []string
	for position, index := range replicas {
		result := results[position]
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
		if position == 0 {
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
