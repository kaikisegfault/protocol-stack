package devnet

import (
	"encoding/base64"
	"fmt"
	"testing"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

func healthyFixtures() (
	[]statusResult,
	[nodeconfig.DevnetNodeCount]abciInfoResult,
	[]ApplicationHead,
	[]netInfoResult,
	[]validatorsResult,
) {
	statuses := make([]statusResult, nodeconfig.DevnetNodeCount)
	heads := make([]ApplicationHead, nodeconfig.DevnetNodeCount)
	networks := make([]netInfoResult, nodeconfig.DevnetNodeCount)
	validators := make([]validatorsResult, nodeconfig.DevnetNodeCount)
	var infos [nodeconfig.DevnetNodeCount]abciInfoResult
	var root nodeconfig.Hash
	for index := range root {
		root[index] = byte(index)
	}
	for index := range nodeconfig.DevnetNodeCount {
		statuses[index].NodeInfo.ID = fmt.Sprintf("node-%d", index)
		statuses[index].NodeInfo.Network = "ps-test"
		statuses[index].SyncInfo.LatestBlockHeight = "2"
		statuses[index].SyncInfo.LatestAppHash = "AABB"
		infos[index].Response.LastBlockHeight = "2"
		infos[index].Response.LastBlockAppHash =
			base64.StdEncoding.EncodeToString(root[:])
		heads[index] = ApplicationHead{Height: 2, Root: root}
		networks[index].NPeers = "3"
		for peer := range nodeconfig.DevnetNodeCount {
			if peer == index {
				continue
			}
			var entry struct {
				NodeInfo struct {
					ID string `json:"id"`
				} `json:"node_info"`
			}
			entry.NodeInfo.ID = fmt.Sprintf("node-%d", peer)
			networks[index].Peers = append(networks[index].Peers, entry)
		}
		validators[index].BlockHeight = "2"
		for validator := range nodeconfig.DevnetNodeCount {
			var entry struct {
				Address     string `json:"address"`
				VotingPower string `json:"voting_power"`
			}
			entry.Address = fmt.Sprintf("validator-%d", validator)
			entry.VotingPower = "10"
			validators[index].Validators = append(
				validators[index].Validators, entry)
		}
	}
	return statuses, infos, heads, networks, validators
}

func TestCompareHealthyNetwork(t *testing.T) {
	statuses, infos, heads, networks, validators := healthyFixtures()
	health, err := compareHeads(statuses, infos, heads)
	if err != nil {
		t.Fatalf("compare heads: %v", err)
	}
	if health.ChainID != "ps-test" ||
		health.Height != 2 ||
		health.HeaderHeight != 2 ||
		len(health.HeaderAppHash) != 2 {
		t.Fatalf("unexpected health: %#v", health)
	}
	if err := comparePeers(statuses, networks); err != nil {
		t.Fatalf("compare peers: %v", err)
	}
	if err := compareValidators(validators); err != nil {
		t.Fatalf("compare validators: %v", err)
	}
}

func TestCompareNetworkRejectsDivergence(t *testing.T) {
	t.Run("head", func(t *testing.T) {
		statuses, infos, heads, _, _ := healthyFixtures()
		heads[3].Root[0] ^= 1
		if _, err := compareHeads(statuses, infos, heads); err == nil {
			t.Fatal("accepted divergent C++ head")
		}
	})
	t.Run("peer", func(t *testing.T) {
		statuses, _, _, networks, _ := healthyFixtures()
		networks[2].Peers = networks[2].Peers[:2]
		networks[2].NPeers = "2"
		if err := comparePeers(statuses, networks); err == nil {
			t.Fatal("accepted incomplete peer set")
		}
	})
	t.Run("validator", func(t *testing.T) {
		_, _, _, _, validators := healthyFixtures()
		validators[1].Validators[0].VotingPower = "11"
		if err := compareValidators(validators); err == nil {
			t.Fatal("accepted unequal validator power")
		}
	})
}

func TestBroadcastRejectsInvalidInputsBeforeRPC(t *testing.T) {
	ctx := t.Context()
	for _, values := range []struct {
		node        int
		transaction []byte
	}{
		{-1, []byte{1}},
		{nodeconfig.DevnetNodeCount, []byte{1}},
		{0, nil},
		{0, make([]byte, 1_048_577)},
	} {
		if _, err := Broadcast(
			ctx, nodeconfig.Devnet{}, values.node, values.transaction,
		); err == nil {
			t.Fatalf("accepted node=%d size=%d",
				values.node, len(values.transaction))
		}
	}
}
