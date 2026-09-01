package bridge

import (
	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/localapp"
)

// The two local application clients in the shape the bridge consumes.
//
// Six of the seven operations are the same connection, the same frames, and
// the same answers, so both types promote them from the client they embed.
// What differs is the finalized block: version seven names the block it
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

// LocalV7 is a version-seven local application client.
type LocalV7 struct {
	*localapp.ClientV7
}

var _ localApplication = LocalV7{}

func (l LocalV7) FinalizeBlock(
	height uint64,
	transactions [][]byte,
) (FinalizedBlock, error) {
	block, err := l.ClientV7.FinalizeBlock(height, transactions)
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
