package localapp

import (
	"bytes"
	"errors"
)

// Version seven's finalized block. It carries a block identifier version one's
// does not, because an adapter that could not name the block it just executed
// could not tell a peer which one it agreed to.
type FinalizedBlockV7 struct {
	StateRoot          Hash
	BlockID            Hash
	TransactionResults []TransactionResult
}

const (
	receiptBytesV7      = 56
	receiptResultOffset = 39
	// Version seven's `Result` enumeration. The encoder on the other side
	// refuses a receipt whose result byte is not below this, so a value at or
	// above it means the two sides disagree about the contract.
	resultCodeCountV7 = 33
)

var receiptPrefixV7 = []byte{'P', 'S', 'R', 'C', 0, 7}

// The declared code and the encoded receipt must be the same fact. A rejected
// admission carries its own small code and no receipt; anything else must be a
// version-seven receipt whose own result byte produces exactly the declared
// code. Version seven's admission failures are version one's, so the small
// codes are unchanged; what differs is the receipt and the result range.
func validTransactionResultV7(result TransactionResult) bool {
	if result.Code >= 1 && result.Code <= 3 {
		return len(result.Data) == 0
	}
	if len(result.Data) != receiptBytesV7 ||
		!bytes.Equal(result.Data[:len(receiptPrefixV7)], receiptPrefixV7) {
		return false
	}
	rawResult := result.Data[receiptResultOffset]
	if rawResult == 0 {
		return result.Code == 0
	}
	return rawResult < resultCodeCountV7 && result.Code == 256+uint32(rawResult)
}

func decodeFinalizeV7(
	payload []byte,
	expectedCount int,
) (FinalizedBlockV7, error) {
	input := reader{value: payload}
	root, err := readHash(&input)
	if err != nil {
		return FinalizedBlockV7{}, err
	}
	blockID, err := readHash(&input)
	if err != nil {
		return FinalizedBlockV7{}, err
	}
	count, err := input.u32()
	if err != nil {
		return FinalizedBlockV7{}, err
	}
	if count > MaximumBlockInputs || int(count) != expectedCount ||
		int(count) > input.remaining()/8 {
		return FinalizedBlockV7{}, errors.New("invalid FinalizeBlock result count")
	}
	results := make([]TransactionResult, 0, int(count))
	for range count {
		code, err := input.u32()
		if err != nil {
			return FinalizedBlockV7{}, err
		}
		data, err := input.blob(receiptBytesV7)
		if err != nil {
			return FinalizedBlockV7{}, err
		}
		result := TransactionResult{Code: code, Data: data}
		if !validTransactionResultV7(result) {
			return FinalizedBlockV7{}, errors.New("invalid FinalizeBlock result")
		}
		results = append(results, result)
	}
	if err := input.finish(); err != nil {
		return FinalizedBlockV7{}, err
	}
	return FinalizedBlockV7{
		StateRoot:          root,
		BlockID:            blockID,
		TransactionResults: results,
	}, nil
}
