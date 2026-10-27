package localapp

import (
	"bytes"
	"errors"
	"fmt"
)

// Version ten speaks the version-two frame unchanged, whose shared pieces are
// in `wire_v2.go` (ADR 0110). What is version ten's own is its receipts, its
// fifty result codes, the protocol version its Info must report, and the types
// its responses decode into. They are version nine's, rebound rather than
// shared, so that ADR 0104's step 7 deletes version nine's files whole.
const (
	receiptBytesV10 = 56
	// The receipt version, which is the last octet of the magic prefix below.
	// **It is named rather than written into the array**, because it is the
	// figure that moves with the ledger version while looking like framing:
	// rebinding a bare literal is what broke every finalized block the first
	// time the C++ encoder was rebound.
	receiptVersionV10 = 10
	// Version nine's 45 and the five version ten adds, so codes 301 to 305
	// decode.
	resultCodeCountV10 = 50
	// **What Info must report**, which `consensus-application-v3` makes the
	// field that names the ledger. The frame does not change between versions
	// nine and ten, so this is the first place a version-nine application on
	// the other end of the socket can be told apart.
	applicationProtocolVersionV10 = 10
)

var receiptPrefixV10 = []byte{
	'P', 'S', 'R', 'C', receiptVersionV10 >> 8, receiptVersionV10 & 0xFF,
}

// The durable head is two scalars and a root, so Info and Commit report both.
type InfoV10 struct {
	ApplicationVersion uint64
	Height             uint64
	Timestamp          uint64
	StateRoot          Hash
}

type CommittedHeadV10 struct {
	Height    uint64
	Timestamp uint64
	StateRoot Hash
}

// Version ten's finalized block is version eight's shape with version ten's
// receipts.
type FinalizedBlockV10 struct {
	StateRoot          Hash
	BlockID            Hash
	TransactionResults []TransactionResult
}

func blockPayloadV10(
	height uint64,
	timestamp uint64,
	transactions [][]byte,
) ([]byte, error) {
	return appendTransactions(appendU64(appendU64(nil, height), timestamp),
		transactions)
}

// Kind 2. The genesis stamp precedes the one variable-length field, so a
// decoder bounds the frame before it allocates.
func initChainPayloadV10(
	chainID Hash,
	initialHeight uint64,
	genesisTimestamp uint64,
	appState []byte,
) []byte {
	payload := make([]byte, 0, 52+len(appState))
	payload = append(payload, chainID[:]...)
	payload = appendU64(payload, initialHeight)
	payload = appendU64(payload, genesisTimestamp)
	return appendBlob(payload, appState)
}

// **An Info from any other ledger is refused**, as a protocol failure, on the
// first frame of every start. That is the refusal the frame version made for
// version nine and cannot make for version ten.
func decodeInfoV10(payload []byte) (InfoV10, error) {
	input := reader{value: payload}
	var info InfoV10
	var err error
	if info.ApplicationVersion, err = input.u64(); err != nil {
		return InfoV10{}, err
	}
	if info.ApplicationVersion != applicationProtocolVersionV10 {
		return InfoV10{}, fmt.Errorf(
			"application protocol version %d is not version ten's",
			info.ApplicationVersion)
	}
	if info.Height, err = input.u64(); err != nil {
		return InfoV10{}, err
	}
	if info.Timestamp, err = input.u64(); err != nil {
		return InfoV10{}, err
	}
	if info.StateRoot, err = readHash(&input); err != nil {
		return InfoV10{}, err
	}
	return info, input.finish()
}

func decodeCommitV10(payload []byte) (CommittedHeadV10, error) {
	input := reader{value: payload}
	var head CommittedHeadV10
	var err error
	if head.Height, err = input.u64(); err != nil {
		return CommittedHeadV10{}, err
	}
	if head.Timestamp, err = input.u64(); err != nil {
		return CommittedHeadV10{}, err
	}
	if head.StateRoot, err = readHash(&input); err != nil {
		return CommittedHeadV10{}, err
	}
	return head, input.finish()
}

// The declared code and the encoded receipt must be the same fact, and the
// receipt must say it is version ten's.
func validTransactionResultV10(result TransactionResult) bool {
	if result.Code >= 1 && result.Code <= 3 {
		return len(result.Data) == 0
	}
	if len(result.Data) != receiptBytesV10 ||
		!bytes.Equal(result.Data[:len(receiptPrefixV10)], receiptPrefixV10) {
		return false
	}
	rawResult := result.Data[receiptResultOffset]
	if rawResult == 0 {
		return result.Code == 0
	}
	return rawResult < resultCodeCountV10 && result.Code == 256+uint32(rawResult)
}

func decodeFinalizeV10(
	payload []byte,
	expectedCount int,
) (FinalizedBlockV10, error) {
	input := reader{value: payload}
	root, err := readHash(&input)
	if err != nil {
		return FinalizedBlockV10{}, err
	}
	blockID, err := readHash(&input)
	if err != nil {
		return FinalizedBlockV10{}, err
	}
	count, err := input.u32()
	if err != nil {
		return FinalizedBlockV10{}, err
	}
	if count > MaximumBlockInputs || int(count) != expectedCount ||
		int(count) > input.remaining()/8 {
		return FinalizedBlockV10{}, errors.New("invalid FinalizeBlock result count")
	}
	results := make([]TransactionResult, 0, int(count))
	for range count {
		code, err := input.u32()
		if err != nil {
			return FinalizedBlockV10{}, err
		}
		data, err := input.blob(receiptBytesV10)
		if err != nil {
			return FinalizedBlockV10{}, err
		}
		result := TransactionResult{Code: code, Data: data}
		if !validTransactionResultV10(result) {
			return FinalizedBlockV10{}, errors.New("invalid FinalizeBlock result")
		}
		results = append(results, result)
	}
	if err := input.finish(); err != nil {
		return FinalizedBlockV10{}, err
	}
	return FinalizedBlockV10{
		StateRoot:          root,
		BlockID:            blockID,
		TransactionResults: results,
	}, nil
}
