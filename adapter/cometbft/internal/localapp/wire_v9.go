package localapp

import (
	"bytes"
	"errors"
)

// Version nine speaks the version-two frame, whose shared pieces are in
// `wire_v2.go`. What is version nine's own is its receipts and the types its
// four changed response payloads decode into.
const (
	receiptBytesV9 = 56
	// The receipt version, which is the last octet of the magic prefix below.
	// **It is named rather than written into the array**, because it is the
	// figure that moves with the ledger version while looking like framing:
	// rebinding a bare literal is what broke every finalized block the first
	// time the C++ encoder was rebound.
	receiptVersionV9 = 9
	// Version nine adds no result code, so its table is version eight's 45.
	resultCodeCountV9 = 45
)

var receiptPrefixV9 = []byte{
	'P', 'S', 'R', 'C', receiptVersionV9 >> 8, receiptVersionV9 & 0xFF,
}

// The durable head is two scalars and a root, so Info and Commit report both.
type InfoV9 struct {
	ApplicationVersion uint64
	Height             uint64
	Timestamp          uint64
	StateRoot          Hash
}

type CommittedHeadV9 struct {
	Height    uint64
	Timestamp uint64
	StateRoot Hash
}

// Version nine's finalized block is version eight's shape with version nine's
// receipts.
type FinalizedBlockV9 struct {
	StateRoot          Hash
	BlockID            Hash
	TransactionResults []TransactionResult
}

func blockPayloadV9(
	height uint64,
	timestamp uint64,
	transactions [][]byte,
) ([]byte, error) {
	return appendTransactions(appendU64(appendU64(nil, height), timestamp),
		transactions)
}

// Kind 2. The genesis stamp precedes the one variable-length field, so a
// decoder bounds the frame before it allocates.
func initChainPayloadV9(
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

func decodeInfoV9(payload []byte) (InfoV9, error) {
	input := reader{value: payload}
	var info InfoV9
	var err error
	if info.ApplicationVersion, err = input.u64(); err != nil {
		return InfoV9{}, err
	}
	if info.Height, err = input.u64(); err != nil {
		return InfoV9{}, err
	}
	if info.Timestamp, err = input.u64(); err != nil {
		return InfoV9{}, err
	}
	if info.StateRoot, err = readHash(&input); err != nil {
		return InfoV9{}, err
	}
	return info, input.finish()
}

func decodeCommitV9(payload []byte) (CommittedHeadV9, error) {
	input := reader{value: payload}
	var head CommittedHeadV9
	var err error
	if head.Height, err = input.u64(); err != nil {
		return CommittedHeadV9{}, err
	}
	if head.Timestamp, err = input.u64(); err != nil {
		return CommittedHeadV9{}, err
	}
	if head.StateRoot, err = readHash(&input); err != nil {
		return CommittedHeadV9{}, err
	}
	return head, input.finish()
}

// The declared code and the encoded receipt must be the same fact, and the
// receipt must say it is version nine's.
func validTransactionResultV9(result TransactionResult) bool {
	if result.Code >= 1 && result.Code <= 3 {
		return len(result.Data) == 0
	}
	if len(result.Data) != receiptBytesV9 ||
		!bytes.Equal(result.Data[:len(receiptPrefixV9)], receiptPrefixV9) {
		return false
	}
	rawResult := result.Data[receiptResultOffset]
	if rawResult == 0 {
		return result.Code == 0
	}
	return rawResult < resultCodeCountV9 && result.Code == 256+uint32(rawResult)
}

func decodeFinalizeV9(
	payload []byte,
	expectedCount int,
) (FinalizedBlockV9, error) {
	input := reader{value: payload}
	root, err := readHash(&input)
	if err != nil {
		return FinalizedBlockV9{}, err
	}
	blockID, err := readHash(&input)
	if err != nil {
		return FinalizedBlockV9{}, err
	}
	count, err := input.u32()
	if err != nil {
		return FinalizedBlockV9{}, err
	}
	if count > MaximumBlockInputs || int(count) != expectedCount ||
		int(count) > input.remaining()/8 {
		return FinalizedBlockV9{}, errors.New("invalid FinalizeBlock result count")
	}
	results := make([]TransactionResult, 0, int(count))
	for range count {
		code, err := input.u32()
		if err != nil {
			return FinalizedBlockV9{}, err
		}
		data, err := input.blob(receiptBytesV9)
		if err != nil {
			return FinalizedBlockV9{}, err
		}
		result := TransactionResult{Code: code, Data: data}
		if !validTransactionResultV9(result) {
			return FinalizedBlockV9{}, errors.New("invalid FinalizeBlock result")
		}
		results = append(results, result)
	}
	if err := input.finish(); err != nil {
		return FinalizedBlockV9{}, err
	}
	return FinalizedBlockV9{
		StateRoot:          root,
		BlockID:            blockID,
		TransactionResults: results,
	}, nil
}
