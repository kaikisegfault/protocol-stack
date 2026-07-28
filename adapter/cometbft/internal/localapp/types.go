package localapp

import "fmt"

const (
	maximumWirePayload     = 33_554_432
	MaximumTransactionSize = 1_048_576
	MaximumBlockInputs     = 65_535
	MaximumBlockSize       = 16_777_216
	MaximumAppStateSize    = 4_096
)

type Kind uint8

const (
	KindInfo Kind = iota + 1
	KindInitChain
	KindCheckTransaction
	KindPrepareProposal
	KindProcessProposal
	KindFinalizeBlock
	KindCommit
)

type Hash [32]byte

type Info struct {
	ApplicationVersion uint64
	Height             uint64
	StateRoot          Hash
}

type TransactionResult struct {
	Code uint32
	Data []byte
}

type FinalizedBlock struct {
	StateRoot          Hash
	TransactionResults []TransactionResult
}

type CommittedHead struct {
	Height    uint64
	StateRoot Hash
}

type ApplicationError struct {
	Status  uint16
	Message string
}

func (e *ApplicationError) Error() string {
	if e.Message == "" {
		return fmt.Sprintf("local application status %d", e.Status)
	}
	return fmt.Sprintf("local application status %d: %s", e.Status, e.Message)
}
