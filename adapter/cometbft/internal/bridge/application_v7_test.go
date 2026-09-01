package bridge

import (
	"context"
	"encoding/hex"
	"strings"
	"testing"

	abci "github.com/cometbft/cometbft/abci/types"
	"github.com/cometbft/cometbft/version"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/localapp"
)

func versionSevenReceipt(result byte) []byte {
	receipt := make([]byte, 56)
	copy(receipt, []byte{'P', 'S', 'R', 'C', 0, 7})
	receipt[39] = result
	return receipt
}

// A version-seven finalized block reaches ABCI as version one's does, plus the
// block identifier the ledger names it with and the codespace its result codes
// belong to.
func TestVersionSevenFinalizeCarriesTheBlockIdentifier(t *testing.T) {
	root := localapp.Hash{0: 0xa5, 31: 0x5a}
	identifier := localapp.Hash{0: 0x5a, 31: 0xa5}
	local := &fakeLocal{
		info: localapp.Info{ApplicationVersion: 7, Height: 4, StateRoot: root},
		finalized: FinalizedBlock{
			StateRoot: root,
			BlockID:   &identifier,
			TransactionResults: []localapp.TransactionResult{
				{Code: 0, Data: versionSevenReceipt(0)},
				{Code: 2},
				{Code: 256 + 32, Data: versionSevenReceipt(32)},
			},
		},
	}
	app := NewV7(local)
	ctx := context.Background()

	info, err := app.Info(ctx, &abci.RequestInfo{
		AbciVersion: version.ABCIVersion,
	})
	if err != nil {
		t.Fatal(err)
	}
	if info.AppVersion != 7 || info.LastBlockHeight != 4 {
		t.Fatalf("unexpected Info response: %#v", info)
	}

	finalized, err := app.FinalizeBlock(ctx, &abci.RequestFinalizeBlock{
		Height: 5,
		Txs:    [][]byte{{1}, {2}, {3}},
	})
	if err != nil {
		t.Fatal(err)
	}
	if string(finalized.AppHash) != string(root[:]) ||
		len(finalized.TxResults) != 3 ||
		finalized.TxResults[0].Codespace != "" ||
		finalized.TxResults[1].Codespace != codespaceV7 ||
		finalized.TxResults[2].Code != 256+32 ||
		finalized.TxResults[2].Codespace != codespaceV7 {
		t.Fatalf("unexpected FinalizeBlock response: %#v", finalized)
	}
	if len(finalized.Events) != 1 ||
		finalized.Events[0].Type != "protocol_block" ||
		len(finalized.Events[0].Attributes) != 1 {
		t.Fatalf("unexpected FinalizeBlock events: %#v", finalized.Events)
	}
	attribute := finalized.Events[0].Attributes[0]
	if attribute.Key != "id" || !attribute.Index ||
		attribute.Value != strings.ToUpper(hex.EncodeToString(identifier[:])) {
		t.Fatalf("unexpected block identity attribute: %#v", attribute)
	}
}

// Version one has no identifier to report, so it emits no block event. The
// pointer is what makes the difference legible: a zero hash would be indexed
// as though it named something.
func TestVersionOneFinalizeEmitsNoBlockEvent(t *testing.T) {
	local := &fakeLocal{
		finalized: FinalizedBlock{
			TransactionResults: []localapp.TransactionResult{{Code: 0}},
		},
	}
	finalized, err := New(local).FinalizeBlock(
		context.Background(),
		&abci.RequestFinalizeBlock{Height: 1, Txs: [][]byte{{1}}})
	if err != nil {
		t.Fatal(err)
	}
	if len(finalized.Events) != 0 {
		t.Fatalf("version one emitted block events: %#v", finalized.Events)
	}
}

// **The replay handshake.** A local application refuses a finalize at a height
// it has already committed, and that refusal is terminal, so the request must
// not reach it. CometBFT v0.39.4 replays such a height against a mock built
// from its own saved response and never asks the real application, so nothing
// in the pinned engine reaches this; the guard is what keeps the failure
// legible and restartable if anything ever does.
func TestFinalizeAtAnAlreadyCommittedHeightIsRefused(t *testing.T) {
	root := localapp.Hash{0: 1}
	local := &fakeLocal{
		info:      localapp.Info{ApplicationVersion: 7, Height: 4, StateRoot: root},
		finalized: FinalizedBlock{StateRoot: root, BlockID: &root},
		committed: localapp.CommittedHead{Height: 5, StateRoot: root},
	}
	app := NewV7(local)
	ctx := context.Background()

	if _, err := app.Info(
		ctx, &abci.RequestInfo{AbciVersion: version.ABCIVersion}); err != nil {
		t.Fatal(err)
	}
	for _, height := range []int64{1, 4} {
		if _, err := app.FinalizeBlock(
			ctx, &abci.RequestFinalizeBlock{Height: height}); err == nil {
			t.Fatalf("FinalizeBlock at committed height %d accepted", height)
		}
	}
	if local.finalizeCalls != 0 {
		t.Fatal("a committed height reached the local application")
	}

	if _, err := app.FinalizeBlock(
		ctx, &abci.RequestFinalizeBlock{Height: 5}); err != nil {
		t.Fatal(err)
	}
	if _, err := app.Commit(ctx, &abci.RequestCommit{}); err != nil {
		t.Fatal(err)
	}
	if _, err := app.FinalizeBlock(
		ctx, &abci.RequestFinalizeBlock{Height: 5}); err == nil {
		t.Fatal("FinalizeBlock repeated after its own commit was accepted")
	}
	if local.finalizeCalls != 1 {
		t.Fatalf("local FinalizeBlock ran %d times", local.finalizeCalls)
	}
	if _, err := app.FinalizeBlock(
		ctx, &abci.RequestFinalizeBlock{Height: 6}); err != nil {
		t.Fatal(err)
	}
}

// The height the guard uses is the local application's own answer, so an
// adapter that never asked Info still forwards the first block of a chain.
func TestTheGuardCountsNothingItself(t *testing.T) {
	local := &fakeLocal{
		committed: localapp.CommittedHead{Height: 1},
		finalized: FinalizedBlock{},
	}
	app := NewV7(local)
	ctx := context.Background()
	if _, err := app.FinalizeBlock(
		ctx, &abci.RequestFinalizeBlock{Height: 1}); err != nil {
		t.Fatal(err)
	}
	// Height zero is not a block height and is refused by the same comparison.
	if _, err := app.FinalizeBlock(
		ctx, &abci.RequestFinalizeBlock{Height: 0}); err == nil {
		t.Fatal("FinalizeBlock at height zero accepted")
	}
}

func TestVersionSevenCodespaceNamesItsOwnResultCodes(t *testing.T) {
	local := &fakeLocal{checkCode: 1}
	app := NewV7(local)
	ctx := context.Background()

	checked, err := app.CheckTx(
		ctx, &abci.RequestCheckTx{Tx: []byte{1}, Type: abci.CheckTxType_New})
	if err != nil {
		t.Fatal(err)
	}
	if checked.Code != 1 || checked.Codespace != codespaceV7 {
		t.Fatalf("unexpected CheckTx response: %#v", checked)
	}
	query, err := app.Query(ctx, &abci.RequestQuery{})
	if err != nil || query.Code != 1 || query.Codespace != codespaceV7 {
		t.Fatalf("Query = %#v, %v", query, err)
	}
}
