package localapp

import (
	"encoding/binary"
	"testing"
)

// One version-eight receipt carrying `result`, in the shape the encoder on the
// other side validates before it writes: the prefix names the version, and the
// result byte at offset 39 must produce exactly the declared code.
func receiptV8(result byte) []byte {
	receipt := make([]byte, receiptBytesV8)
	copy(receipt, receiptPrefixV8)
	receipt[receiptResultOffset] = result
	return receipt
}

func resultCodeV8(result byte) uint32 {
	if result == 0 {
		return 0
	}
	return 256 + uint32(result)
}

// Every result a version-eight block can report: the three admission failures
// that carry no receipt, and all forty-five execution results.
func finalizeBodyV8(root, blockID Hash) []byte {
	body := append([]byte(nil), root[:]...)
	body = append(body, blockID[:]...)
	body = appendU32(body, 3+resultCodeCountV8)
	for code := uint32(1); code <= 3; code++ {
		body = appendU32(body, code)
		body = appendU32(body, 0)
	}
	for result := byte(0); result < resultCodeCountV8; result++ {
		body = appendU32(body, resultCodeV8(result))
		body = appendBlob(body, receiptV8(result))
	}
	return body
}

func TestDecodeAllVersionEightFinalizeResults(t *testing.T) {
	root := Hash{0: 0xa5, 31: 0x5a}
	blockID := Hash{0: 0x5a, 31: 0xa5}
	body := finalizeBodyV8(root, blockID)
	expected := 3 + resultCodeCountV8

	block, err := decodeFinalizeV8(body, expected)
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
		if result.Code != resultCodeV8(raw) ||
			len(result.Data) != receiptBytesV8 ||
			result.Data[receiptResultOffset] != raw {
			t.Fatalf("execution result %d: %#v", index, result)
		}
	}
}

// The block identifier is not optional. A payload without it is version one's
// shape, and reading it as version eight's must fail rather than silently
// return the identifier's first thirty-two octets as a result count.
func TestVersionEightRefusesVersionOnesFinalizeShape(t *testing.T) {
	root := Hash{0: 7}
	body := append([]byte(nil), root[:]...)
	body = appendU32(body, 1)
	body = appendU32(body, 0)
	body = appendBlob(body, receiptV8(0))
	if _, err := decodeFinalizeV8(body, 1); err == nil {
		t.Fatal("a finalized block with no identifier was accepted")
	}
}

// And the converse, which is what makes a client dialled at the wrong version
// fail closed: version one's decoder must refuse version eight's payload.
func TestVersionOneRefusesVersionEightsFinalizeShape(t *testing.T) {
	body := finalizeBodyV8(Hash{0: 1}, Hash{0: 2})
	if _, err := decodeFinalize(body, 3+resultCodeCountV8); err == nil {
		t.Fatal("version one accepted a version-eight finalized block")
	}
}

func TestVersionEightFinalizeRefusals(t *testing.T) {
	root := Hash{0: 0xa5}
	blockID := Hash{31: 0x5a}
	body := finalizeBodyV8(root, blockID)
	expected := 3 + resultCodeCountV8
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
		// A version-one receipt under a version-eight declared code.
		"receipt version": corrupt(func(value []byte) []byte {
			value[firstReceiptBody+5] = 1
			return value
		}),
		// A result byte at the count, which is one past the last defined
		// result and is what a wider table on one side would look like.
		"result out of range": corrupt(func(value []byte) []byte {
			value[firstReceiptBody+receiptResultOffset] = resultCodeCountV8
			binary.BigEndian.PutUint32(
				value[firstReceipt:firstReceipt+4],
				resultCodeV8(resultCodeCountV8))
			return value
		}),
		// The declared code and the receipt's own result byte disagreeing is
		// the one thing the encoder on the other side promises never to write.
		"code disagrees with receipt": corrupt(func(value []byte) []byte {
			binary.BigEndian.PutUint32(
				value[firstReceipt:firstReceipt+4], 256+1)
			return value
		}),
		// A version-one receipt length under a version-eight prefix.
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
			if _, err := decodeFinalizeV8(value, expected); err == nil {
				t.Fatal("invalid FinalizeBlock response accepted")
			}
		})
	}
}

func FuzzVersionEightFinalizeDecoder(f *testing.F) {
	f.Add(make([]byte, 68))
	f.Add(finalizeBodyV8(Hash{}, Hash{}))
	f.Fuzz(func(_ *testing.T, input []byte) {
		_, _ = decodeFinalizeV8(input, 0)
		_, _ = decodeFinalizeV8(input, 36)
	})
}

// The two figures that moved with the version, pinned to their literals.
//
// **Neither is checked by anything above**, and they fail differently. A stale
// receipt version breaks the happy path -- the encoder on the other side writes
// 8 and every finalized block would be refused -- so it would be caught by the
// first integration block. A stale result count would not: the codes it would
// cut off are 33 through 44, and no fixture in this repository produces one, so
// the range would silently narrow. Every check above compares the constant to
// itself and would pass at either value.
func TestVersionEightFiguresAreTheContracts(t *testing.T) {
	if receiptVersionV8 != 8 {
		t.Fatalf("receipt version is %d, not version eight's", receiptVersionV8)
	}
	if receiptPrefixV8[5] != 8 || receiptPrefixV8[4] != 0 {
		t.Fatalf("receipt prefix does not name version eight: %v", receiptPrefixV8)
	}
	if resultCodeCountV8 != 45 {
		t.Fatalf("result code count is %d, not version eight's 45",
			resultCodeCountV8)
	}
	// The last defined result and the first undefined one, written out rather
	// than derived, so the boundary is a fact about the contract.
	accepted := TransactionResult{Code: 256 + 44, Data: receiptV8(44)}
	if !validTransactionResultV8(accepted) {
		t.Fatal("result 44 was refused")
	}
	refused := TransactionResult{Code: 256 + 45, Data: receiptV8(45)}
	if validTransactionResultV8(refused) {
		t.Fatal("result 45 was accepted")
	}
}

// The pair that makes `-protocol-version` safe between the two live versions.
//
// Versions seven and eight have the **same finalized-block shape** -- a root,
// an identifier, a count, and one result per input -- so neither the field
// layout nor the result count separates them on a well-formed block. The
// receipt version octet is the only thing that does, which is why a client
// dialled at the wrong one of these two must fail closed on the first block
// rather than on some later result code.
func TestVersionsSevenAndEightRefuseEachOther(t *testing.T) {
	root := Hash{0: 0xa5, 31: 0x5a}
	blockID := Hash{0: 0x5a, 31: 0xa5}
	// One successful result on both sides, so nothing but the receipt's own
	// version octet differs between the two payloads.
	body := func(receipt []byte) []byte {
		value := append([]byte(nil), root[:]...)
		value = append(value, blockID[:]...)
		value = appendU32(value, 1)
		value = appendU32(value, 0)
		return appendBlob(value, receipt)
	}
	if _, err := decodeFinalizeV7(body(receiptV8(0)), 1); err == nil {
		t.Fatal("version seven accepted a version-eight finalized block")
	}
	if _, err := decodeFinalizeV8(body(receiptV7(0)), 1); err == nil {
		t.Fatal("version eight accepted a version-seven finalized block")
	}
}
