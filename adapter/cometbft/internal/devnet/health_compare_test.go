package devnet

import (
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"testing"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

// subsetFixtures builds the RPC results a converged subset would return.
//
// Every member reports the same head and sees exactly the other members, so a
// three-replica subset carries two peers each rather than three. The validator
// set stays at four whatever the subset is, because it comes from a genesis
// file a stopped process does not change.
func subsetFixtures(replicas Replicas) (
	[]statusResult,
	[]abciInfoResult,
	[]netInfoResult,
	[]validatorsResult,
) {
	statuses := make([]statusResult, len(replicas))
	networks := make([]netInfoResult, len(replicas))
	validators := make([]validatorsResult, len(replicas))
	infos := make([]abciInfoResult, len(replicas))
	var root nodeconfig.Hash
	for index := range root {
		root[index] = byte(index)
	}
	for position, index := range replicas {
		statuses[position].NodeInfo.ID = fmt.Sprintf("node-%d", index)
		statuses[position].NodeInfo.Network = "ps-test"
		statuses[position].SyncInfo.LatestBlockHeight = "2"
		statuses[position].SyncInfo.LatestAppHash = hex.EncodeToString(root[:])
		infos[position].Response.LastBlockHeight = "2"
		infos[position].Response.LastBlockAppHash =
			base64.StdEncoding.EncodeToString(root[:])
		networks[position].NPeers = fmt.Sprintf("%d", len(replicas)-1)
		for _, peer := range replicas {
			if peer == index {
				continue
			}
			var entry struct {
				NodeInfo struct {
					ID string `json:"id"`
				} `json:"node_info"`
			}
			entry.NodeInfo.ID = fmt.Sprintf("node-%d", peer)
			networks[position].Peers = append(networks[position].Peers, entry)
		}
		validators[position].BlockHeight = "2"
		for validator := range nodeconfig.DevnetNodeCount {
			var entry struct {
				Address     string `json:"address"`
				VotingPower string `json:"voting_power"`
			}
			entry.Address = fmt.Sprintf("validator-%d", validator)
			entry.VotingPower = "10"
			validators[position].Validators = append(
				validators[position].Validators, entry)
		}
	}
	return statuses, infos, networks, validators
}

func healthyFixtures() (
	[]statusResult,
	[]abciInfoResult,
	[]netInfoResult,
	[]validatorsResult,
) {
	return subsetFixtures(AllReplicas())
}

func TestCompareHealthyNetwork(t *testing.T) {
	all := AllReplicas()
	statuses, infos, networks, validators := healthyFixtures()
	health, err := compareHeads(all, statuses, infos)
	if err != nil {
		t.Fatalf("compare heads: %v", err)
	}
	if health.ChainID != "ps-test" ||
		health.Height != 2 ||
		health.HeaderHeight != 2 ||
		len(health.HeaderAppHash) != len(nodeconfig.Hash{}) {
		t.Fatalf("unexpected health: %#v", health)
	}
	if err := comparePeers(all, statuses, networks); err != nil {
		t.Fatalf("compare peers: %v", err)
	}
	if err := compareValidators(all, validators); err != nil {
		t.Fatalf("compare validators: %v", err)
	}

	for index := range nodeconfig.DevnetNodeCount {
		statuses[index].SyncInfo.LatestBlockHeight = "0"
		statuses[index].SyncInfo.LatestAppHash = ""
		infos[index].Response.LastBlockHeight = "0"
	}
	if health, err := compareHeads(all, statuses, infos); err != nil ||
		health.Height != 0 ||
		len(health.HeaderAppHash) != 0 {
		t.Fatalf("height-zero health = %#v, %v", health, err)
	}
}

// TestCompareThreeRunningReplicas is the M3.14e claim in the comparators.
//
// Three replicas that agree, each seeing the other two, is a healthy
// observation of the subset `0,1,3` — and it must stay a real check rather than
// a relaxed one, which is why the peer count follows the subset and the
// validator set does not.
func TestCompareThreeRunningReplicas(t *testing.T) {
	running := Replicas{0, 1, 3}
	statuses, infos, networks, validators := subsetFixtures(running)
	if _, err := compareHeads(running, statuses, infos); err != nil {
		t.Fatalf("compare heads: %v", err)
	}
	if err := comparePeers(running, statuses, networks); err != nil {
		t.Fatalf("compare peers: %v", err)
	}
	if err := compareValidators(running, validators); err != nil {
		t.Fatalf("compare validators: %v", err)
	}

	t.Run("errors-name-the-replica-not-the-position", func(t *testing.T) {
		statuses, infos, _, _ := subsetFixtures(running)
		// Both heights move together, so this is a replica that is genuinely
		// ahead rather than one reporting two different heights about itself.
		statuses[2].SyncInfo.LatestBlockHeight = "3"
		infos[2].Response.LastBlockHeight = "3"
		_, err := compareHeads(running, statuses, infos)
		if err == nil {
			t.Fatal("accepted a divergent replica")
		}
		if err.Error() != "validator replicas have not converged" {
			t.Fatalf("divergence error = %v", err)
		}
		statuses, infos, _, _ = subsetFixtures(running)
		statuses[2].SyncInfo.CatchingUp = true
		_, err = compareHeads(running, statuses, infos)
		if err == nil || err.Error() != "node 3 is still catching up" {
			t.Fatalf("catch-up error = %v", err)
		}
	})

	t.Run("a-stopped-replica-that-is-still-gossiping", func(t *testing.T) {
		// Node 2 was supposed to be down, and node 0 can still see it. The
		// subset check must fail: a peer nobody counted is exactly the state
		// this observation exists to rule out.
		statuses, _, networks, _ := subsetFixtures(running)
		var stray struct {
			NodeInfo struct {
				ID string `json:"id"`
			} `json:"node_info"`
		}
		stray.NodeInfo.ID = "node-2"
		networks[0].Peers = append(networks[0].Peers, stray)
		networks[0].NPeers = "3"
		if err := comparePeers(running, statuses, networks); err == nil {
			t.Fatal("accepted a peer outside the running subset")
		}
	})

	t.Run("a-replica-reporting-three-validators", func(t *testing.T) {
		// A stopped process does not retire its validator, so three is a
		// changed validator set rather than a stopped replica.
		_, _, _, validators := subsetFixtures(running)
		validators[1].Validators = validators[1].Validators[:3]
		if err := compareValidators(running, validators); err == nil {
			t.Fatal("accepted three validators while one replica was down")
		}
	})
}

func TestCompareNetworkRejectsDivergence(t *testing.T) {
	all := AllReplicas()
	t.Run("head", func(t *testing.T) {
		statuses, infos, _, _ := healthyFixtures()
		statuses[3].SyncInfo.LatestBlockHeight = "3"
		infos[3].Response.LastBlockHeight = "3"
		if _, err := compareHeads(all, statuses, infos); err == nil {
			t.Fatal("accepted divergent ABCI head")
		}
	})
	t.Run("inconsistent-head-metadata", func(t *testing.T) {
		// One replica reporting two different heights about itself is a
		// separate failure from two replicas disagreeing, and moving only the
		// ABCI height is what produces it.
		statuses, infos, _, _ := healthyFixtures()
		infos[3].Response.LastBlockHeight = "3"
		_, err := compareHeads(all, statuses, infos)
		if err == nil ||
			err.Error() != "node 3 returned inconsistent head metadata" {
			t.Fatalf("inconsistent metadata error = %v", err)
		}
	})
	t.Run("header-hash-length", func(t *testing.T) {
		statuses, infos, _, _ := healthyFixtures()
		statuses[2].SyncInfo.LatestAppHash = "AA"
		if _, err := compareHeads(all, statuses, infos); err == nil {
			t.Fatal("accepted invalid header application hash")
		}
	})
	t.Run("catching-up", func(t *testing.T) {
		statuses, infos, _, _ := healthyFixtures()
		statuses[1].SyncInfo.CatchingUp = true
		if _, err := compareHeads(all, statuses, infos); err == nil {
			t.Fatal("accepted a catching-up validator")
		}
	})
	t.Run("peer", func(t *testing.T) {
		statuses, _, networks, _ := healthyFixtures()
		networks[2].Peers = networks[2].Peers[:2]
		networks[2].NPeers = "2"
		if err := comparePeers(all, statuses, networks); err == nil {
			t.Fatal("accepted incomplete peer set")
		}
	})
	t.Run("validator", func(t *testing.T) {
		_, _, _, validators := healthyFixtures()
		validators[1].Validators[0].VotingPower = "11"
		if err := compareValidators(all, validators); err == nil {
			t.Fatal("accepted unequal validator power")
		}
	})
}

func TestBroadcastRejectsInvalidInputsBeforeRPC(t *testing.T) {
	ctx := t.Context()
	for _, values := range []struct {
		replicas    Replicas
		node        int
		transaction []byte
	}{
		{AllReplicas(), -1, []byte{1}},
		{AllReplicas(), nodeconfig.DevnetNodeCount, []byte{1}},
		{AllReplicas(), 0, nil},
		{AllReplicas(), 0, make([]byte, 1_048_577)},
		// The submitting replica must be one the caller says is running.
		{Replicas{0, 1, 3}, 2, []byte{1}},
		{Replicas{}, 0, []byte{1}},
		{Replicas{1, 0}, 0, []byte{1}},
	} {
		if _, err := Broadcast(
			ctx, nodeconfig.Devnet{}, values.replicas, values.node,
			values.transaction,
		); err == nil {
			t.Fatalf("accepted nodes=%v node=%d size=%d",
				values.replicas, values.node, len(values.transaction))
		}
	}
}
