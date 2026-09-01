package bridge

import (
	"context"
	"encoding/base64"
	"math"
	"sync/atomic"
	"testing"
	"time"

	abci "github.com/cometbft/cometbft/abci/types"
	"github.com/cometbft/cometbft/version"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/localapp"
)

type fakeLocal struct {
	info          localapp.Info
	initRoot      localapp.Hash
	checkCode     uint32
	prepared      [][]byte
	processAccept bool
	finalized     FinalizedBlock
	committed     localapp.CommittedHead
	lastChain     localapp.Hash
	lastHeight    uint64
	lastState     []byte
	lastTxs       [][]byte
	finalizeCalls int
	infoEntered   chan struct{}
	releaseInfo   chan struct{}
	active        atomic.Int32
	maximumActive atomic.Int32
}

func (f *fakeLocal) enter() {
	active := f.active.Add(1)
	for {
		maximum := f.maximumActive.Load()
		if active <= maximum || f.maximumActive.CompareAndSwap(maximum, active) {
			break
		}
	}
}

func (f *fakeLocal) leave() {
	f.active.Add(-1)
}

func (f *fakeLocal) Info() (localapp.Info, error) {
	f.enter()
	defer f.leave()
	if f.infoEntered != nil {
		f.infoEntered <- struct{}{}
		<-f.releaseInfo
	}
	return f.info, nil
}

func (f *fakeLocal) InitChain(
	chain localapp.Hash,
	height uint64,
	state []byte,
) (localapp.Hash, error) {
	f.enter()
	defer f.leave()
	f.lastChain = chain
	f.lastHeight = height
	f.lastState = append([]byte(nil), state...)
	return f.initRoot, nil
}

func (f *fakeLocal) CheckTransaction(tx []byte) (uint32, error) {
	f.enter()
	defer f.leave()
	f.lastState = append([]byte(nil), tx...)
	return f.checkCode, nil
}

func (f *fakeLocal) PrepareProposal(
	_ int64,
	txs [][]byte,
) ([][]byte, error) {
	f.enter()
	defer f.leave()
	f.lastTxs = txs
	if f.prepared != nil {
		return f.prepared, nil
	}
	return txs, nil
}

func (f *fakeLocal) ProcessProposal(
	height uint64,
	txs [][]byte,
) (bool, error) {
	f.enter()
	defer f.leave()
	f.lastHeight = height
	f.lastTxs = txs
	return f.processAccept, nil
}

func (f *fakeLocal) FinalizeBlock(
	height uint64,
	txs [][]byte,
) (FinalizedBlock, error) {
	f.enter()
	defer f.leave()
	f.finalizeCalls++
	f.lastHeight = height
	f.lastTxs = txs
	return f.finalized, nil
}

func (f *fakeLocal) Commit() (localapp.CommittedHead, error) {
	f.enter()
	defer f.leave()
	return f.committed, nil
}

func testChain() (localapp.Hash, string) {
	var chain localapp.Hash
	for index := range chain {
		chain[index] = byte(index)
	}
	return chain, "ps-" + base64.RawURLEncoding.EncodeToString(chain[:])
}

func TestExactABCIConversions(t *testing.T) {
	root := localapp.Hash{0: 0xa5, 31: 0x5a}
	local := &fakeLocal{
		info: localapp.Info{
			ApplicationVersion: 1,
			Height:             7,
			StateRoot:          root,
		},
		initRoot:      root,
		processAccept: true,
		committed:     localapp.CommittedHead{Height: 8, StateRoot: root},
	}
	app := New(local)
	ctx := context.Background()

	info, err := app.Info(ctx, &abci.RequestInfo{
		AbciVersion: version.ABCIVersion,
	})
	if err != nil {
		t.Fatal(err)
	}
	if info.Data != applicationData || info.Version != applicationVersion ||
		info.AppVersion != 1 || info.LastBlockHeight != 7 ||
		string(info.LastBlockAppHash) != string(root[:]) {
		t.Fatalf("unexpected Info response: %#v", info)
	}
	if _, err := app.Info(ctx, &abci.RequestInfo{
		AbciVersion: "1.0.0",
	}); err == nil {
		t.Fatal("incompatible ABCI version accepted")
	}
	local.info.Height = math.MaxInt64 + 1
	if _, err := app.Info(ctx, &abci.RequestInfo{
		AbciVersion: version.ABCIVersion,
	}); err == nil {
		t.Fatal("unrepresentable application height accepted")
	}
	local.info.Height = 7

	chain, chainText := testChain()
	state := []byte(`"protocol-stack-v1"`)
	initialized, err := app.InitChain(ctx, &abci.RequestInitChain{
		ChainId:       chainText,
		AppStateBytes: state,
		InitialHeight: 1,
	})
	if err != nil {
		t.Fatal(err)
	}
	if local.lastChain != chain || local.lastHeight != 1 ||
		string(local.lastState) != string(state) ||
		string(initialized.AppHash) != string(root[:]) {
		t.Fatal("InitChain was not translated losslessly")
	}

	for code := uint32(0); code <= 3; code++ {
		local.checkCode = code
		for _, checkType := range []abci.CheckTxType{
			abci.CheckTxType_New,
			abci.CheckTxType_Recheck,
		} {
			checked, err := app.CheckTx(ctx, &abci.RequestCheckTx{
				Tx: []byte{1, 2, 3}, Type: checkType,
			})
			if err != nil {
				t.Fatal(err)
			}
			expectedCodespace := ""
			if code != 0 {
				expectedCodespace = codespaceV1
			}
			if checked.Code != code ||
				checked.Codespace != expectedCodespace ||
				len(checked.Data) != 0 || checked.GasWanted != 0 ||
				checked.GasUsed != 0 {
				t.Fatalf("unexpected CheckTx response: %#v", checked)
			}
		}
	}

	prepared, err := app.PrepareProposal(
		ctx,
		&abci.RequestPrepareProposal{
			MaxTxBytes: 3,
			Txs:        [][]byte{{1, 2}, {3}, {4}},
		})
	if err != nil {
		t.Fatal(err)
	}
	if len(prepared.Txs) != 2 || len(local.lastTxs) != 2 {
		t.Fatalf("unexpected prepared prefix: %#v", prepared.Txs)
	}

	processed, err := app.ProcessProposal(
		ctx, &abci.RequestProcessProposal{Height: 8, Txs: [][]byte{{9}}})
	if err != nil || processed.Status != abci.ResponseProcessProposal_ACCEPT {
		t.Fatalf("ProcessProposal = %#v, %v", processed, err)
	}

	receipt := make([]byte, 47)
	copy(receipt, []byte{'P', 'S', 'R', 'C', 0, 1})
	local.finalized = FinalizedBlock{
		StateRoot: root,
		TransactionResults: []localapp.TransactionResult{
			{Code: 0, Data: receipt},
			{Code: 1},
			{Code: 264, Data: append([]byte(nil), receipt...)},
		},
	}
	local.finalized.TransactionResults[2].Data[38] = 8
	finalized, err := app.FinalizeBlock(
		ctx,
		&abci.RequestFinalizeBlock{
			Height: 8,
			Txs:    [][]byte{{1}, {2}, {3}},
		})
	if err != nil {
		t.Fatal(err)
	}
	if string(finalized.AppHash) != string(root[:]) ||
		len(finalized.TxResults) != 3 ||
		finalized.TxResults[0].Codespace != "" ||
		finalized.TxResults[1].Codespace != codespaceV1 ||
		finalized.TxResults[2].Code != 264 ||
		len(finalized.Events) != 0 ||
		len(finalized.ValidatorUpdates) != 0 ||
		finalized.ConsensusParamUpdates != nil {
		t.Fatalf("unexpected FinalizeBlock response: %#v", finalized)
	}

	committed, err := app.Commit(ctx, &abci.RequestCommit{})
	if err != nil || committed.RetainHeight != 0 {
		t.Fatalf("Commit = %#v, %v", committed, err)
	}
}

func TestRequestRejectionAndUnsupportedMethods(t *testing.T) {
	local := &fakeLocal{}
	app := New(local)
	ctx := context.Background()

	_, chainText := testChain()
	for _, value := range []string{
		"", chainText + "=", "xs-" + chainText[3:],
		chainText[:45] + "+",
	} {
		if _, err := app.InitChain(ctx, &abci.RequestInitChain{
			ChainId: value,
		}); err == nil {
			t.Fatalf("invalid chain ID accepted: %q", value)
		}
	}
	if _, err := app.CheckTx(ctx, &abci.RequestCheckTx{
		Type: abci.CheckTxType(2),
	}); err == nil {
		t.Fatal("unknown CheckTx type accepted")
	}
	if _, err := app.PrepareProposal(
		ctx, &abci.RequestPrepareProposal{MaxTxBytes: -1}); err == nil {
		t.Fatal("negative proposal limit accepted")
	}
	if _, err := app.FinalizeBlock(
		ctx, &abci.RequestFinalizeBlock{Height: -1}); err == nil {
		t.Fatal("negative FinalizeBlock height accepted")
	}

	query, err := app.Query(ctx, &abci.RequestQuery{})
	if err != nil || query.Code != 1 || query.Codespace != codespaceV1 ||
		len(query.Value) != 0 {
		t.Fatalf("Query = %#v, %v", query, err)
	}
	if _, err := app.InsertTx(ctx, &abci.RequestInsertTx{}); err == nil {
		t.Fatal("InsertTx accepted")
	}
	if _, err := app.ReapTxs(ctx, &abci.RequestReapTxs{}); err == nil {
		t.Fatal("ReapTxs accepted")
	}
	extended, err := app.ExtendVote(ctx, &abci.RequestExtendVote{})
	if err != nil || len(extended.VoteExtension) != 0 {
		t.Fatalf("ExtendVote = %#v, %v", extended, err)
	}
	for _, test := range []struct {
		value []byte
		want  abci.ResponseVerifyVoteExtension_VerifyStatus
	}{
		{nil, abci.ResponseVerifyVoteExtension_ACCEPT},
		{[]byte{1}, abci.ResponseVerifyVoteExtension_REJECT},
	} {
		verified, err := app.VerifyVoteExtension(
			ctx,
			&abci.RequestVerifyVoteExtension{VoteExtension: test.value})
		if err != nil || verified.Status != test.want {
			t.Fatalf("VerifyVoteExtension = %#v, %v", verified, err)
		}
	}
	listed, err := app.ListSnapshots(ctx, &abci.RequestListSnapshots{})
	if err != nil || len(listed.Snapshots) != 0 {
		t.Fatalf("ListSnapshots = %#v, %v", listed, err)
	}
	offered, err := app.OfferSnapshot(ctx, &abci.RequestOfferSnapshot{})
	if err != nil || offered.Result != abci.ResponseOfferSnapshot_REJECT {
		t.Fatalf("OfferSnapshot = %#v, %v", offered, err)
	}
	if _, err := app.LoadSnapshotChunk(
		ctx, &abci.RequestLoadSnapshotChunk{}); err == nil {
		t.Fatal("LoadSnapshotChunk accepted")
	}
	applied, err := app.ApplySnapshotChunk(
		ctx, &abci.RequestApplySnapshotChunk{})
	if err != nil ||
		applied.Result != abci.ResponseApplySnapshotChunk_REJECT_SNAPSHOT {
		t.Fatalf("ApplySnapshotChunk = %#v, %v", applied, err)
	}
}

func TestProposalBoundaries(t *testing.T) {
	maximum := make([]byte, localapp.MaximumTransactionSize)
	local := &fakeLocal{}
	app := New(local)
	ctx := context.Background()

	response, err := app.PrepareProposal(
		ctx,
		&abci.RequestPrepareProposal{
			MaxTxBytes: math.MaxInt64,
			Txs: [][]byte{
				maximum, maximum, maximum, maximum,
				maximum, maximum, maximum, maximum,
				maximum, maximum, maximum, maximum,
				maximum, maximum, maximum, maximum,
				{1},
			},
		})
	if err != nil || len(response.Txs) != 16 {
		t.Fatalf("PrepareProposal boundary = %d, %v", len(response.Txs), err)
	}

	rejected, err := app.ProcessProposal(
		ctx,
		&abci.RequestProcessProposal{
			Height: 1,
			Txs:    [][]byte{make([]byte, localapp.MaximumTransactionSize+1)},
		})
	if err != nil || rejected.Status != abci.ResponseProcessProposal_REJECT {
		t.Fatalf("oversized ProcessProposal = %#v, %v", rejected, err)
	}
}

func TestCrossConnectionSerialization(t *testing.T) {
	local := &fakeLocal{
		info:        localapp.Info{},
		infoEntered: make(chan struct{}, 2),
		releaseInfo: make(chan struct{}),
	}
	app := New(local)
	request := &abci.RequestInfo{AbciVersion: version.ABCIVersion}
	done := make(chan error, 2)
	for range 2 {
		go func() {
			_, err := app.Info(context.Background(), request)
			done <- err
		}()
	}
	select {
	case <-local.infoEntered:
	case <-time.After(time.Second):
		t.Fatal("first request did not cross local boundary")
	}
	select {
	case <-local.infoEntered:
		t.Fatal("requests crossed local boundary concurrently")
	case <-time.After(20 * time.Millisecond):
	}
	local.releaseInfo <- struct{}{}
	select {
	case <-local.infoEntered:
	case <-time.After(time.Second):
		t.Fatal("second request did not cross local boundary")
	}
	local.releaseInfo <- struct{}{}
	for range 2 {
		if err := <-done; err != nil {
			t.Fatal(err)
		}
	}
	if local.maximumActive.Load() != 1 {
		t.Fatalf("maximum concurrent local calls = %d", local.maximumActive.Load())
	}
}

func TestPrepareProposalRefusesChangedBytes(t *testing.T) {
	local := &fakeLocal{prepared: [][]byte{{9}}}
	app := New(local)
	_, err := app.PrepareProposal(
		context.Background(),
		&abci.RequestPrepareProposal{MaxTxBytes: 1, Txs: [][]byte{{1}}},
	)
	if err == nil {
		t.Fatal("changed proposal bytes accepted")
	}
}
