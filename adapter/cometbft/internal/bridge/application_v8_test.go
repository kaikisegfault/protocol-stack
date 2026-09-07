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

func versionEightReceipt(result byte) []byte {
	receipt := make([]byte, 56)
	copy(receipt, []byte{'P', 'S', 'R', 'C', 0, 8})
	receipt[39] = result
	return receipt
}

// A version-eight finalized block reaches ABCI as version seven's does. What
// differs is the codespace, and the difference is only observable on a result
// code version seven does not have: result 44 is inside version eight's range
// of forty-five and outside version seven's thirty-three, so an adapter wired
// to the wrong constructor names it in the wrong vocabulary.
func TestVersionEightFinalizeCarriesTheBlockIdentifier(t *testing.T) {
	root := localapp.Hash{0: 0xa5, 31: 0x5a}
	identifier := localapp.Hash{0: 0x5a, 31: 0xa5}
	local := &fakeLocal{
		info: localapp.Info{ApplicationVersion: 8, Height: 4, StateRoot: root},
		finalized: FinalizedBlock{
			StateRoot: root,
			BlockID:   &identifier,
			TransactionResults: []localapp.TransactionResult{
				{Code: 0, Data: versionEightReceipt(0)},
				{Code: 2},
				{Code: 256 + 44, Data: versionEightReceipt(44)},
			},
		},
	}
	app := NewV8(local)
	ctx := context.Background()

	info, err := app.Info(ctx, &abci.RequestInfo{
		AbciVersion: version.ABCIVersion,
	})
	if err != nil {
		t.Fatal(err)
	}
	if info.AppVersion != 8 || info.LastBlockHeight != 4 {
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
		finalized.TxResults[1].Codespace != codespaceV8 ||
		finalized.TxResults[2].Code != 256+44 ||
		finalized.TxResults[2].Codespace != codespaceV8 {
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

func TestVersionEightCodespaceNamesItsOwnResultCodes(t *testing.T) {
	local := &fakeLocal{checkCode: 1}
	app := NewV8(local)
	ctx := context.Background()

	checked, err := app.CheckTx(
		ctx, &abci.RequestCheckTx{Tx: []byte{1}, Type: abci.CheckTxType_New})
	if err != nil {
		t.Fatal(err)
	}
	if checked.Code != 1 || checked.Codespace != codespaceV8 {
		t.Fatalf("unexpected CheckTx response: %#v", checked)
	}
	query, err := app.Query(ctx, &abci.RequestQuery{})
	if err != nil || query.Code != 1 || query.Codespace != codespaceV8 {
		t.Fatalf("Query = %#v, %v", query, err)
	}
}

// The three codespaces must be three distinct strings, which is the only
// property that makes them useful to an operator reading a rejected result.
// Rebinding a copy of a constructor and forgetting the constant is what this
// catches, and nothing above would: every check there compares a codespace
// against the same constant the constructor used.
func TestTheThreeCodespacesAreDistinct(t *testing.T) {
	expected := map[string]string{
		"v1": "protocol-stack-v1",
		"v7": "protocol-stack-v7",
		"v8": "protocol-stack-v8",
	}
	actual := map[string]string{
		"v1": codespaceV1,
		"v7": codespaceV7,
		"v8": codespaceV8,
	}
	for name, value := range expected {
		if actual[name] != value {
			t.Fatalf("codespace %s is %q, not %q", name, actual[name], value)
		}
	}
}
