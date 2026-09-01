package localapp

import (
	"encoding/binary"
	"testing"
)

// One version-seven receipt carrying `result`, in the shape the encoder on the
// other side validates before it writes: the prefix names the version, and the
// result byte at offset 39 must produce exactly the declared code.
func receiptV7(result byte) []byte {
	receipt := make([]byte, receiptBytesV7)
	copy(receipt, receiptPrefixV7)
	receipt[receiptResultOffset] = result
	return receipt
}

func resultCodeV7(result byte) uint32 {
	if result == 0 {
		return 0
	}
	return 256 + uint32(result)
}

// Every result a version-seven block can report: the three admission failures
// that carry no receipt, and all thirty-three execution results.
func finalizeBodyV7(root, blockID Hash) []byte {
	body := append([]byte(nil), root[:]...)
	body = append(body, blockID[:]...)
	body = appendU32(body, 3+resultCodeCountV7)
	for code := uint32(1); code <= 3; code++ {
		body = appendU32(body, code)
		body = appendU32(body, 0)
	}
	for result := byte(0); result < resultCodeCountV7; result++ {
		body = appendU32(body, resultCodeV7(result))
		body = appendBlob(body, receiptV7(result))
	}
	return body
}

func TestDecodeAllVersionSevenFinalizeResults(t *testing.T) {
	root := Hash{0: 0xa5, 31: 0x5a}
	blockID := Hash{0: 0x5a, 31: 0xa5}
	body := finalizeBodyV7(root, blockID)
	expected := 3 + resultCodeCountV7

	block, err := decodeFinalizeV7(body, expected)
	if err != nil {
		t.Fatal(err)
	}
	if block.StateRoot != root || block.BlockID != blockID ||
		len(block.TransactionResults) != expected {
		t.Fatalf("unexpected finalized block: %#v", block)
	}
	for index, result := range block.TransactionResults {
		if index < 3 {
			if result.Code != uint32(index+1) || len(result.Data) != 0 {
				t.Fatalf("admission result %d: %#v", index, result)
			}
			continue
		}
		raw := byte(index - 3)
		if result.Code != resultCodeV7(raw) ||
			len(result.Data) != receiptBytesV7 ||
			result.Data[receiptResultOffset] != raw {
			t.Fatalf("execution result %d: %#v", index, result)
		}
	}
}

// The block identifier is not optional. A payload without it is version one's
// shape, and reading it as version seven's must fail rather than silently
// return the identifier's first thirty-two octets as a result count.
func TestVersionSevenRefusesVersionOnesFinalizeShape(t *testing.T) {
	root := Hash{0: 7}
	body := append([]byte(nil), root[:]...)
	body = appendU32(body, 1)
	body = appendU32(body, 0)
	body = appendBlob(body, receiptV7(0))
	if _, err := decodeFinalizeV7(body, 1); err == nil {
		t.Fatal("a finalized block with no identifier was accepted")
	}
}

// And the converse, which is what makes a client dialled at the wrong version
// fail closed: version one's decoder must refuse version seven's payload.
func TestVersionOneRefusesVersionSevensFinalizeShape(t *testing.T) {
	body := finalizeBodyV7(Hash{0: 1}, Hash{0: 2})
	if _, err := decodeFinalize(body, 3+resultCodeCountV7); err == nil {
		t.Fatal("version one accepted a version-seven finalized block")
	}
}

func TestVersionSevenFinalizeRefusals(t *testing.T) {
	root := Hash{0: 0xa5}
	blockID := Hash{31: 0x5a}
	body := finalizeBodyV7(root, blockID)
	expected := 3 + resultCodeCountV7
	// Where the fourth result -- the first that carries a receipt -- begins:
	// the root, the identifier, the count, and three eight-octet admission
	// results. Its own octets are a four-octet code, a four-octet blob length,
	// and then the receipt.
	firstReceipt := 32 + 32 + 4 + 3*8
	firstReceiptBody := firstReceipt + 8

	corrupt := func(mutate func([]byte) []byte) []byte {
		return mutate(append([]byte(nil), body...))
	}
	invalid := map[string][]byte{
		"count": corrupt(func(value []byte) []byte {
			binary.BigEndian.PutUint32(
				value[64:68], uint32(expected-1))
			return value
		}),
		"truncated identifier": append([]byte(nil), body[:60]...),
		"trailing":             append(append([]byte(nil), body...), 0),
		// A version-one receipt under a version-seven declared code.
		"receipt version": corrupt(func(value []byte) []byte {
			value[firstReceiptBody+5] = 1
			return value
		}),
		// A result byte at the count, which is one past the last defined
		// result and is what a wider table on one side would look like.
		"result out of range": corrupt(func(value []byte) []byte {
			value[firstReceiptBody+receiptResultOffset] = resultCodeCountV7
			binary.BigEndian.PutUint32(
				value[firstReceipt:firstReceipt+4],
				resultCodeV7(resultCodeCountV7))
			return value
		}),
		// The declared code and the receipt's own result byte disagreeing is
		// the one thing the encoder on the other side promises never to write.
		"code disagrees with receipt": corrupt(func(value []byte) []byte {
			binary.BigEndian.PutUint32(
				value[firstReceipt:firstReceipt+4], 256+1)
			return value
		}),
		// A version-one receipt length under a version-seven prefix.
		"receipt length": corrupt(func(value []byte) []byte {
			binary.BigEndian.PutUint32(
				value[firstReceipt+4:firstReceipt+8], 47)
			return value
		}),
		// An admission failure may not carry a receipt.
		"admission data": corrupt(func(value []byte) []byte {
			binary.BigEndian.PutUint32(value[72:76], 1)
			return append(value[:76], append([]byte{0}, value[76:]...)...)
		}),
	}
	for name, value := range invalid {
		t.Run(name, func(t *testing.T) {
			if _, err := decodeFinalizeV7(value, expected); err == nil {
				t.Fatal("invalid FinalizeBlock response accepted")
			}
		})
	}
}

func FuzzVersionSevenFinalizeDecoder(f *testing.F) {
	f.Add(make([]byte, 68))
	f.Add(finalizeBodyV7(Hash{}, Hash{}))
	f.Fuzz(func(_ *testing.T, input []byte) {
		_, _ = decodeFinalizeV7(input, 0)
		_, _ = decodeFinalizeV7(input, 36)
	})
}
