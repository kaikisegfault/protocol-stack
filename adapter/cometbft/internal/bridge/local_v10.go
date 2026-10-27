package bridge

import (
	"fmt"
	"time"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/localapp"
)

// LocalV10 is a version-ten local application client: `LocalV9` rebound for
// version ten's ledger (ADR 0110), so that ADR 0104's step 7 deletes version
// nine's whole. The engine's times become milliseconds here, as they do for
// version nine. What differs is underneath it: the client refuses an Info that
// does not name version ten, and its finalized blocks carry version ten's
// receipts.
type LocalV10 struct {
	*localapp.ClientV10
}

var _ localApplication = LocalV10{}

// Info drops the durable stamp: ABCI's Info has no field for it. The stamp is
// still reported by the local application and still committed by the root.
func (l LocalV10) Info() (localapp.Info, error) {
	info, err := l.ClientV10.Info()
	if err != nil {
		return localapp.Info{}, err
	}
	return localapp.Info{
		ApplicationVersion: info.ApplicationVersion,
		Height:             info.Height,
		StateRoot:          info.StateRoot,
	}, nil
}

func (l LocalV10) InitChain(
	chainID localapp.Hash,
	initialHeight uint64,
	genesisTime time.Time,
	appState []byte,
) (localapp.Hash, error) {
	stamp, err := genesisMillis(genesisTime)
	if err != nil {
		return localapp.Hash{}, fmt.Errorf("invalid InitChain request: %w", err)
	}
	return l.ClientV10.InitChain(chainID, initialHeight, stamp, appState)
}

// Every decision is a vote, and only decision 0 is a vote for.
func (l LocalV10) ProcessProposal(
	height uint64,
	blockTime time.Time,
	transactions [][]byte,
) (Vote, error) {
	stamp, err := blockMillis(blockTime)
	if err != nil {
		return Vote{}, fmt.Errorf("invalid ProcessProposal request: %w", err)
	}
	decision, err := l.ClientV10.ProcessProposal(height, stamp, transactions)
	if err != nil {
		return Vote{}, err
	}
	if decision == localapp.DecisionAccepted {
		return Vote{Accept: true}, nil
	}
	return Vote{Reason: decision.String()}, nil
}

// A status 7 or 8 arrives here as an error, and the bridge turns it into an
// ABCI error like every other nonzero status: the network has decided a block
// this machine's rules refuse, and it stops rather than guess.
func (l LocalV10) FinalizeBlock(
	height uint64,
	blockTime time.Time,
	transactions [][]byte,
) (FinalizedBlock, error) {
	stamp, err := blockMillis(blockTime)
	if err != nil {
		return FinalizedBlock{}, fmt.Errorf("invalid FinalizeBlock request: %w", err)
	}
	block, err := l.ClientV10.FinalizeBlock(height, stamp, transactions)
	if err != nil {
		return FinalizedBlock{}, err
	}
	identifier := block.BlockID
	return FinalizedBlock{
		StateRoot:          block.StateRoot,
		BlockID:            &identifier,
		TransactionResults: block.TransactionResults,
	}, nil
}

func (l LocalV10) Commit() (localapp.CommittedHead, error) {
	head, err := l.ClientV10.Commit()
	if err != nil {
		return localapp.CommittedHead{}, err
	}
	return localapp.CommittedHead{Height: head.Height, StateRoot: head.StateRoot}, nil
}
