package bridge

import (
	"fmt"
	"time"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/localapp"
)

// The local application clients in the shape the bridge consumes.
//
// CheckTransaction and PrepareProposal are the same connection, the same
// frames, and the same answers for every version, so every type promotes them
// from the client it embeds. What differs is the engine's time, which only
// version nine reads; the finalized block, which version eight and nine name and
// version one has nothing to name with; and the vote, which only version nine
// explains.

// LocalV1 is a version-one local application client.
type LocalV1 struct {
	*localapp.Client
}

var _ localApplication = LocalV1{}

// InitChain ignores the genesis time, as version one always has: its genesis
// carries none.
func (l LocalV1) InitChain(
	chainID localapp.Hash,
	initialHeight uint64,
	_ time.Time,
	appState []byte,
) (localapp.Hash, error) {
	return l.Client.InitChain(chainID, initialHeight, appState)
}

func (l LocalV1) ProcessProposal(
	height uint64,
	_ time.Time,
	transactions [][]byte,
) (Vote, error) {
	accept, err := l.Client.ProcessProposal(height, transactions)
	return Vote{Accept: accept}, err
}

func (l LocalV1) FinalizeBlock(
	height uint64,
	_ time.Time,
	transactions [][]byte,
) (FinalizedBlock, error) {
	block, err := l.Client.FinalizeBlock(height, transactions)
	if err != nil {
		return FinalizedBlock{}, err
	}
	return FinalizedBlock{
		StateRoot:          block.StateRoot,
		TransactionResults: block.TransactionResults,
	}, nil
}

// LocalV8 is a version-eight local application client.
type LocalV8 struct {
	*localapp.ClientV8
}

var _ localApplication = LocalV8{}

func (l LocalV8) InitChain(
	chainID localapp.Hash,
	initialHeight uint64,
	_ time.Time,
	appState []byte,
) (localapp.Hash, error) {
	return l.ClientV8.InitChain(chainID, initialHeight, appState)
}

func (l LocalV8) ProcessProposal(
	height uint64,
	_ time.Time,
	transactions [][]byte,
) (Vote, error) {
	accept, err := l.ClientV8.ProcessProposal(height, transactions)
	return Vote{Accept: accept}, err
}

func (l LocalV8) FinalizeBlock(
	height uint64,
	_ time.Time,
	transactions [][]byte,
) (FinalizedBlock, error) {
	block, err := l.ClientV8.FinalizeBlock(height, transactions)
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

// LocalV9 is a version-nine local application client. **It is where the
// engine's times become milliseconds**, because version nine is the only
// version that reads them, and a conversion applied to every version would give
// versions one and eight a refusal they never had.
type LocalV9 struct {
	*localapp.ClientV9
}

var _ localApplication = LocalV9{}

// Info drops the durable stamp: ABCI's Info has no field for it. The stamp is
// still reported by the local application and still committed by the root.
func (l LocalV9) Info() (localapp.Info, error) {
	info, err := l.ClientV9.Info()
	if err != nil {
		return localapp.Info{}, err
	}
	return localapp.Info{
		ApplicationVersion: info.ApplicationVersion,
		Height:             info.Height,
		StateRoot:          info.StateRoot,
	}, nil
}

func (l LocalV9) InitChain(
	chainID localapp.Hash,
	initialHeight uint64,
	genesisTime time.Time,
	appState []byte,
) (localapp.Hash, error) {
	stamp, err := genesisMillis(genesisTime)
	if err != nil {
		return localapp.Hash{}, fmt.Errorf("invalid InitChain request: %w", err)
	}
	return l.ClientV9.InitChain(chainID, initialHeight, stamp, appState)
}

// Every decision is a vote, and only decision 0 is a vote for.
func (l LocalV9) ProcessProposal(
	height uint64,
	blockTime time.Time,
	transactions [][]byte,
) (Vote, error) {
	stamp, err := blockMillis(blockTime)
	if err != nil {
		return Vote{}, fmt.Errorf("invalid ProcessProposal request: %w", err)
	}
	decision, err := l.ClientV9.ProcessProposal(height, stamp, transactions)
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
func (l LocalV9) FinalizeBlock(
	height uint64,
	blockTime time.Time,
	transactions [][]byte,
) (FinalizedBlock, error) {
	stamp, err := blockMillis(blockTime)
	if err != nil {
		return FinalizedBlock{}, fmt.Errorf("invalid FinalizeBlock request: %w", err)
	}
	block, err := l.ClientV9.FinalizeBlock(height, stamp, transactions)
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

func (l LocalV9) Commit() (localapp.CommittedHead, error) {
	head, err := l.ClientV9.Commit()
	if err != nil {
		return localapp.CommittedHead{}, err
	}
	return localapp.CommittedHead{Height: head.Height, StateRoot: head.StateRoot}, nil
}
