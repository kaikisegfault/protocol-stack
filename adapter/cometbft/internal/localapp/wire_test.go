package localapp

import (
	"encoding/binary"
	"testing"
)

func TestFrozenInfoFrame(t *testing.T) {
	frame, err := encodeFrame(KindInfo, 1, nil)
	if err != nil {
		t.Fatal(err)
	}
	expected := []byte{
		'P', 'S', 'A', 'P', 0, 1, 0, 1,
		0, 0, 0, 0, 0, 0, 0, 1,
		0, 0, 0, 0,
	}
	if string(frame) != string(expected) {
		t.Fatalf("Info frame = %x, want %x", frame, expected)
	}
}

func TestDecodeHeaderRejectsInvalidFields(t *testing.T) {
	header := responseHeader(KindInfo, 1, 0)
	cases := map[string]func([]byte){
		"magic":      func(value []byte) { value[0] ^= 1 },
		"version":    func(value []byte) { value[5] = 2 },
		"direction":  func(value []byte) { value[6] = 0 },
		"kind":       func(value []byte) { value[7] = byte(KindCommit) },
		"request ID": func(value []byte) { value[15] = 2 },
		"payload size": func(value []byte) {
			binary.BigEndian.PutUint32(value[16:20], maximumWirePayload+1)
		},
	}
	for name, mutate := range cases {
		t.Run(name, func(t *testing.T) {
			value := append([]byte(nil), header...)
			mutate(value)
			if _, err := decodeHeader(value, KindInfo, 1); err == nil {
				t.Fatal("invalid header accepted")
			}
		})
	}
}

func TestDecodeEnvelope(t *testing.T) {
	success := []byte{0, 0, 0, 0, 0, 0, 7}
	value, err := decodeEnvelope(success)
	if err != nil || len(value) != 1 || value[0] != 7 {
		t.Fatalf("success decode = %x, %v", value, err)
	}

	failure := []byte{0, 3, 0, 0, 0, 4, 's', 't', 'o', 'p'}
	_, err = decodeEnvelope(failure)
	applicationError, ok := err.(*ApplicationError)
	if !ok || applicationError.Status != 3 ||
		applicationError.Message != "stop" {
		t.Fatalf("error decode = %#v", err)
	}

	invalid := [][]byte{
		{0, 0, 0, 0, 0, 1, 'x'},
		{0, 7, 0, 0, 0, 0},
		{0, 1, 0, 0, 0, 1, 0xff},
		{0, 1, 0, 0, 0, 0, 1},
	}
	for _, payload := range invalid {
		if _, err := decodeEnvelope(payload); err == nil {
			t.Fatalf("invalid envelope accepted: %x", payload)
		}
	}
}

func TestDecodeAllFinalizeResults(t *testing.T) {
	root := Hash{0: 0xa5, 31: 0x5a}
	body := append([]byte(nil), root[:]...)
	body = appendU32(body, 12)
	for code := uint32(1); code <= 3; code++ {
		body = appendU32(body, code)
		body = appendU32(body, 0)
	}
	for result := byte(0); result <= 8; result++ {
		receipt := make([]byte, 47)
		copy(receipt, []byte{'P', 'S', 'R', 'C', 0, 1})
		receipt[38] = result
		code := uint32(result)
		if result != 0 {
			code += 256
		}
		body = appendU32(body, code)
		body = appendBlob(body, receipt)
	}
	block, err := decodeFinalize(body, 12)
	if err != nil {
		t.Fatal(err)
	}
	if block.StateRoot != root || len(block.TransactionResults) != 12 {
		t.Fatalf("unexpected finalized block: %#v", block)
	}

	invalid := map[string][]byte{}
	invalid["count"] = append([]byte(nil), body...)
	binary.BigEndian.PutUint32(invalid["count"][32:36], 11)
	invalid["admission data"] = append([]byte(nil), body...)
	invalid["admission data"] = append(
		invalid["admission data"][:44],
		append([]byte{1}, invalid["admission data"][44:]...)...)
	binary.BigEndian.PutUint32(invalid["admission data"][40:44], 1)
	invalid["receipt"] = append([]byte(nil), body...)
	invalid["receipt"][len(invalid["receipt"])-9] = 9
	invalid["trailing"] = append(append([]byte(nil), body...), 0)
	for name, value := range invalid {
		t.Run(name, func(t *testing.T) {
			if _, err := decodeFinalize(value, 12); err == nil {
				t.Fatal("invalid FinalizeBlock response accepted")
			}
		})
	}
}

func TestTransactionBounds(t *testing.T) {
	maximum := make([]byte, MaximumTransactionSize)
	if _, err := appendTransactions(nil, [][]byte{maximum}); err != nil {
		t.Fatal(err)
	}
	if _, err := appendTransactions(
		nil, [][]byte{make([]byte, MaximumTransactionSize+1)}); err == nil {
		t.Fatal("oversized transaction accepted")
	}
	tooMany := make([][]byte, MaximumBlockInputs+1)
	if _, err := appendTransactions(nil, tooMany); err == nil {
		t.Fatal("oversized transaction count accepted")
	}
	tooLarge := make([][]byte, 17)
	for index := range tooLarge {
		tooLarge[index] = maximum
	}
	if _, err := appendTransactions(nil, tooLarge); err == nil {
		t.Fatal("oversized block accepted")
	}
}

func FuzzLocalResponseDecoders(f *testing.F) {
	f.Add([]byte{0, 0, 0, 0, 0, 0})
	f.Add([]byte{0, 1, 0, 0, 0, 0})
	f.Add(make([]byte, 36))
	f.Fuzz(func(t *testing.T, input []byte) {
		_, _ = decodeEnvelope(input)
		_, _ = decodeFinalize(input, 0)
		if len(input) == wireHeaderSize {
			_, _ = decodeHeader(input, KindInfo, 1)
		}
	})
}

func responseHeader(kind Kind, requestID uint64, size uint32) []byte {
	header := make([]byte, wireHeaderSize)
	copy(header, wireMagic[:])
	binary.BigEndian.PutUint16(header[4:6], wireVersion)
	header[6] = 1
	header[7] = byte(kind)
	binary.BigEndian.PutUint64(header[8:16], requestID)
	binary.BigEndian.PutUint32(header[16:20], size)
	return header
}
