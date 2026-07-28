package localapp

import (
	"bytes"
	"encoding/binary"
	"errors"
	"unicode/utf8"
)

const (
	wireHeaderSize = 20
	wireVersion    = 1
	maximumMessage = 4_096
)

var wireMagic = [4]byte{'P', 'S', 'A', 'P'}

type reader struct {
	value  []byte
	offset int
}

func (r *reader) remaining() int {
	return len(r.value) - r.offset
}

func (r *reader) take(size int) ([]byte, error) {
	if size < 0 || size > r.remaining() {
		return nil, errors.New("truncated local application payload")
	}
	value := r.value[r.offset : r.offset+size]
	r.offset += size
	return value, nil
}

func (r *reader) u16() (uint16, error) {
	value, err := r.take(2)
	if err != nil {
		return 0, err
	}
	return binary.BigEndian.Uint16(value), nil
}

func (r *reader) u32() (uint32, error) {
	value, err := r.take(4)
	if err != nil {
		return 0, err
	}
	return binary.BigEndian.Uint32(value), nil
}

func (r *reader) u64() (uint64, error) {
	value, err := r.take(8)
	if err != nil {
		return 0, err
	}
	return binary.BigEndian.Uint64(value), nil
}

func (r *reader) blob(maximum int) ([]byte, error) {
	size, err := r.u32()
	if err != nil {
		return nil, err
	}
	if size > uint32(maximum) {
		return nil, errors.New("local application blob exceeds limit")
	}
	return r.take(int(size))
}

func (r *reader) finish() error {
	if r.remaining() != 0 {
		return errors.New("trailing local application payload bytes")
	}
	return nil
}

func appendU32(output []byte, value uint32) []byte {
	var encoded [4]byte
	binary.BigEndian.PutUint32(encoded[:], value)
	return append(output, encoded[:]...)
}

func appendU64(output []byte, value uint64) []byte {
	var encoded [8]byte
	binary.BigEndian.PutUint64(encoded[:], value)
	return append(output, encoded[:]...)
}

func appendBlob(output, value []byte) []byte {
	output = appendU32(output, uint32(len(value)))
	return append(output, value...)
}

func validateTransactions(transactions [][]byte) (int, error) {
	if len(transactions) > MaximumBlockInputs {
		return 0, errors.New("transaction count exceeds limit")
	}
	total := 0
	for _, transaction := range transactions {
		if len(transaction) > MaximumTransactionSize {
			return 0, errors.New("transaction exceeds size limit")
		}
		if len(transaction) > MaximumBlockSize-total {
			return 0, errors.New("transaction bytes exceed block limit")
		}
		total += len(transaction)
	}
	return total, nil
}

func appendTransactions(output []byte, transactions [][]byte) ([]byte, error) {
	total, err := validateTransactions(transactions)
	if err != nil {
		return nil, err
	}
	output = appendU32(output, uint32(len(transactions)))
	if len(output)+4*len(transactions)+total > maximumWirePayload {
		return nil, errors.New("local application payload exceeds limit")
	}
	for _, transaction := range transactions {
		output = appendBlob(output, transaction)
	}
	return output, nil
}

func (r *reader) transactions() ([][]byte, error) {
	count, err := r.u32()
	if err != nil {
		return nil, err
	}
	if count > MaximumBlockInputs || int(count) > r.remaining()/4 {
		return nil, errors.New("invalid transaction list count")
	}
	transactions := make([][]byte, 0, int(count))
	total := 0
	for range count {
		transaction, err := r.blob(MaximumTransactionSize)
		if err != nil {
			return nil, err
		}
		if len(transaction) > MaximumBlockSize-total {
			return nil, errors.New("transaction bytes exceed block limit")
		}
		total += len(transaction)
		transactions = append(transactions, transaction)
	}
	return transactions, nil
}

func encodeFrame(kind Kind, requestID uint64, payload []byte) ([]byte, error) {
	if kind < KindInfo || kind > KindCommit || requestID == 0 {
		return nil, errors.New("invalid local application frame identity")
	}
	if len(payload) > maximumWirePayload {
		return nil, errors.New("local application payload exceeds limit")
	}
	frame := make([]byte, wireHeaderSize, wireHeaderSize+len(payload))
	copy(frame[:4], wireMagic[:])
	binary.BigEndian.PutUint16(frame[4:6], wireVersion)
	frame[6] = 0
	frame[7] = byte(kind)
	binary.BigEndian.PutUint64(frame[8:16], requestID)
	binary.BigEndian.PutUint32(frame[16:20], uint32(len(payload)))
	return append(frame, payload...), nil
}

func decodeHeader(header []byte, kind Kind, requestID uint64) (uint32, error) {
	if len(header) != wireHeaderSize || !bytes.Equal(header[:4], wireMagic[:]) {
		return 0, errors.New("invalid local application response magic")
	}
	if binary.BigEndian.Uint16(header[4:6]) != wireVersion {
		return 0, errors.New("unsupported local application response version")
	}
	if header[6] != 1 || header[7] != byte(kind) ||
		binary.BigEndian.Uint64(header[8:16]) != requestID {
		return 0, errors.New("mismatched local application response")
	}
	size := binary.BigEndian.Uint32(header[16:20])
	if size > maximumWirePayload {
		return 0, errors.New("local application response exceeds limit")
	}
	return size, nil
}

func decodeEnvelope(payload []byte) ([]byte, error) {
	input := reader{value: payload}
	status, err := input.u16()
	if err != nil {
		return nil, err
	}
	message, err := input.blob(maximumMessage)
	if err != nil {
		return nil, err
	}
	if status == 0 {
		if len(message) != 0 {
			return nil, errors.New("successful local response has a message")
		}
		return input.value[input.offset:], nil
	}
	if status > 6 || !utf8.Valid(message) {
		return nil, errors.New("invalid local application error response")
	}
	if err := input.finish(); err != nil {
		return nil, err
	}
	return nil, &ApplicationError{Status: status, Message: string(message)}
}

func readHash(input *reader) (Hash, error) {
	value, err := input.take(32)
	if err != nil {
		return Hash{}, err
	}
	var result Hash
	copy(result[:], value)
	return result, nil
}

func validTransactionResult(result TransactionResult) bool {
	if result.Code >= 1 && result.Code <= 3 {
		return len(result.Data) == 0
	}
	if len(result.Data) != 47 ||
		!bytes.Equal(result.Data[:6], []byte{'P', 'S', 'R', 'C', 0, 1}) {
		return false
	}
	rawResult := result.Data[38]
	if rawResult == 0 {
		return result.Code == 0
	}
	return rawResult <= 8 && result.Code == 256+uint32(rawResult)
}

func decodeFinalize(payload []byte, expectedCount int) (FinalizedBlock, error) {
	input := reader{value: payload}
	root, err := readHash(&input)
	if err != nil {
		return FinalizedBlock{}, err
	}
	count, err := input.u32()
	if err != nil {
		return FinalizedBlock{}, err
	}
	if count > MaximumBlockInputs || int(count) != expectedCount ||
		int(count) > input.remaining()/8 {
		return FinalizedBlock{}, errors.New("invalid FinalizeBlock result count")
	}
	results := make([]TransactionResult, 0, int(count))
	for range count {
		code, err := input.u32()
		if err != nil {
			return FinalizedBlock{}, err
		}
		data, err := input.blob(47)
		if err != nil {
			return FinalizedBlock{}, err
		}
		result := TransactionResult{Code: code, Data: data}
		if !validTransactionResult(result) {
			return FinalizedBlock{}, errors.New("invalid FinalizeBlock result")
		}
		results = append(results, result)
	}
	if err := input.finish(); err != nil {
		return FinalizedBlock{}, err
	}
	return FinalizedBlock{StateRoot: root, TransactionResults: results}, nil
}
