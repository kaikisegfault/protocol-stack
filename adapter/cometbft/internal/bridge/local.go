package bridge

import (
	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/localapp"
)

// The two local application clients in the shape the bridge consumes.
//
// Six of the seven operations are the same connection, the same frames, and
// the same answers, so every type promotes them from the client it embeds.
// What differs is the finalized block: version eight names the block it
// executed and version one has nothing to name it with.

// LocalV1 is a version-one local application client.
type LocalV1 struct {
	*localapp.Client
}

var _ localApplication = LocalV1{}

func (l LocalV1) FinalizeBlock(
	height uint64,
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

func (l LocalV8) FinalizeBlock(
	height uint64,
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
