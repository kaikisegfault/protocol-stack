package bridge

import (
	"context"
	"errors"

	abci "github.com/cometbft/cometbft/abci/types"
)

func (a *Application) Query(
	context.Context,
	*abci.RequestQuery,
) (*abci.ResponseQuery, error) {
	return &abci.ResponseQuery{Code: 1, Codespace: a.codespace}, nil
}

func (a *Application) InsertTx(
	context.Context,
	*abci.RequestInsertTx,
) (*abci.ResponseInsertTx, error) {
	return nil, errors.New("application mempool is disabled")
}

func (a *Application) ReapTxs(
	context.Context,
	*abci.RequestReapTxs,
) (*abci.ResponseReapTxs, error) {
	return nil, errors.New("application mempool is disabled")
}

func (a *Application) ExtendVote(
	context.Context,
	*abci.RequestExtendVote,
) (*abci.ResponseExtendVote, error) {
	return &abci.ResponseExtendVote{}, nil
}

func (a *Application) VerifyVoteExtension(
	_ context.Context,
	request *abci.RequestVerifyVoteExtension,
) (*abci.ResponseVerifyVoteExtension, error) {
	status := abci.ResponseVerifyVoteExtension_REJECT
	if request != nil && len(request.VoteExtension) == 0 {
		status = abci.ResponseVerifyVoteExtension_ACCEPT
	}
	return &abci.ResponseVerifyVoteExtension{Status: status}, nil
}

func (a *Application) ListSnapshots(
	context.Context,
	*abci.RequestListSnapshots,
) (*abci.ResponseListSnapshots, error) {
	return &abci.ResponseListSnapshots{}, nil
}

func (a *Application) OfferSnapshot(
	context.Context,
	*abci.RequestOfferSnapshot,
) (*abci.ResponseOfferSnapshot, error) {
	return &abci.ResponseOfferSnapshot{
		Result: abci.ResponseOfferSnapshot_REJECT,
	}, nil
}

func (a *Application) LoadSnapshotChunk(
	context.Context,
	*abci.RequestLoadSnapshotChunk,
) (*abci.ResponseLoadSnapshotChunk, error) {
	return nil, errors.New("ABCI state sync is disabled")
}

func (a *Application) ApplySnapshotChunk(
	context.Context,
	*abci.RequestApplySnapshotChunk,
) (*abci.ResponseApplySnapshotChunk, error) {
	return &abci.ResponseApplySnapshotChunk{
		Result: abci.ResponseApplySnapshotChunk_REJECT_SNAPSHOT,
	}, nil
}
