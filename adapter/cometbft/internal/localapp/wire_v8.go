package localapp

import (
	"bytes"
	"errors"
)

// Version eight's finalized block. Its shape is version seven's -- a state
// root, the block identifier, and one result per raw input -- because version
// eight changed what a block *does* and not what a finalized block *is*.
type FinalizedBlockV8 struct {
	StateRoot          Hash
	BlockID            Hash
	TransactionResults []TransactionResult
}

const (
	receiptBytesV8 = 56
	// The receipt version, which is the last octet of the magic prefix below.
	// **It is named rather than written into the array**, because it is the
	// figure that moves with the ledger version while looking like framing:
	// version seven's prefix is a bare literal, and rebinding that literal is
	// what broke every finalized block the first time the C++ encoder was
	// rebound. Naming it here puts the two copies one line apart.
	receiptVersionV8 = 8
	// Version eight's `Result` enumeration. Codes 0 through 32 keep their exact
	// version-seven meanings and twelve are added, so a value at or above this
	// means the two sides disagree about the contract.
	resultCodeCountV8 = 45
)

var receiptPrefixV8 = []byte{
	'P', 'S', 'R', 'C', receiptVersionV8 >> 8, receiptVersionV8 & 0xFF,
}

// The declared code and the encoded receipt must be the same fact. A rejected
// admission carries its own small code and no receipt; anything else must be a
// version-eight receipt whose own result byte produces exactly the declared
// code. Version eight's admission failures are version one's, so the small
// codes are unchanged; what differs is the receipt version and the result range.
func validTransactionResultV8(result TransactionResult) bool {
	if result.Code >= 1 && result.Code <= 3 {
		return len(result.Data) == 0
	}
	if len(result.Data) != receiptBytesV8 ||
		!bytes.Equal(result.Data[:len(receiptPrefixV8)], receiptPrefixV8) {
		return false
	}
	rawResult := result.Data[receiptResultOffset]
	if rawResult == 0 {
		return result.Code == 0
	}
	return rawResult < resultCodeCountV8 && result.Code == 256+uint32(rawResult)
}

func decodeFinalizeV8(
	payload []byte,
	expectedCount int,
) (FinalizedBlockV8, error) {
	input := reader{value: payload}
	root, err := readHash(&input)
	if err != nil {
		return FinalizedBlockV8{}, err
	}
	blockID, err := readHash(&input)
	if err != nil {
		return FinalizedBlockV8{}, err
	}
	count, err := input.u32()
	if err != nil {
		return FinalizedBlockV8{}, err
	}
	if count > MaximumBlockInputs || int(count) != expectedCount ||
		int(count) > input.remaining()/8 {
		return FinalizedBlockV8{}, errors.New("invalid FinalizeBlock result count")
	}
	results := make([]TransactionResult, 0, int(count))
	for range count {
		code, err := input.u32()
		if err != nil {
			return FinalizedBlockV8{}, err
		}
		data, err := input.blob(receiptBytesV8)
		if err != nil {
			return FinalizedBlockV8{}, err
		}
		result := TransactionResult{Code: code, Data: data}
		if !validTransactionResultV8(result) {
			return FinalizedBlockV8{}, errors.New("invalid FinalizeBlock result")
		}
		results = append(results, result)
	}
	if err := input.finish(); err != nil {
		return FinalizedBlockV8{}, err
	}
	return FinalizedBlockV8{
		StateRoot:          root,
		BlockID:            blockID,
		TransactionResults: results,
	}, nil
}
