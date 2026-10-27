package localapp

import (
	"encoding/binary"
	"testing"
)

func receiptV10(result byte) []byte {
	receipt := make([]byte, receiptBytesV10)
	copy(receipt, receiptPrefixV10)
	receipt[receiptResultOffset] = result
	return receipt
}

// The declared code an executed result carries: zero for success, and 256 past
// the receipt's own result byte otherwise.
func resultCodeV10(result byte) uint32 {
	if result == 0 {
		return 0
	}
	return 256 + uint32(result)
}

// Every result a version-ten block can report: the three admission failures
// that carry no receipt, and all fifty execution results.
func finalizeBodyV10(root, blockID Hash) []byte {
	body := append([]byte(nil), root[:]...)
	body = append(body, blockID[:]...)
	body = appendU32(body, 3+resultCodeCountV10)
	for code := uint32(1); code <= 3; code++ {
		body = appendU32(body, code)
		body = appendU32(body, 0)
	}
	for result := byte(0); result < resultCodeCountV10; result++ {
		body = appendU32(body, resultCodeV10(result))
		body = appendBlob(body, receiptV10(result))
	}
	return body
}

// The two head responses, octet for octet, and refused when cut at any field or
// followed by anything. **An Info naming any ledger but version ten's is
// refused**, beside its own as the control: that is the one check
// `consensus-application-v3` adds to a version-ten bridge.
func TestVersionTenHeadResponses(t *testing.T) {
	root := Hash{0: 9, 31: 9}
	info := appendU64(appendU64(appendU64(nil, 10), 4), 1_768_435_290_000)
	info = append(info, root[:]...)
	decoded, err := decodeInfoV10(info)
	if err != nil || decoded != (InfoV10{10, 4, 1_768_435_290_000, root}) {
		t.Fatalf("info = %#v, %v", decoded, err)
	}
	for _, version := range []uint64{0, 1, 9, 11} {
		other := append(appendU64(nil, version), info[8:]...)
		if _, err := decodeInfoV10(other); err == nil {
			t.Fatalf("an Info naming protocol version %d was accepted", version)
		}
	}
	commit := info[8:]
	head, err := decodeCommitV10(commit)
	if err != nil || head != (CommittedHeadV10{4, 1_768_435_290_000, root}) {
		t.Fatalf("commit = %#v, %v", head, err)
	}
	for size := range len(info) {
		if _, err := decodeInfoV10(info[:size]); err == nil {
			t.Fatalf("info truncated to %d octets accepted", size)
		}
	}
	for size := range len(commit) {
		if _, err := decodeCommitV10(commit[:size]); err == nil {
			t.Fatalf("commit truncated to %d octets accepted", size)
		}
	}
	if _, err := decodeInfoV10(append(append([]byte(nil), info...), 0)); err == nil {
		t.Fatal("info with a trailing octet accepted")
	}
	if _, err := decodeCommitV10(append(append([]byte(nil), commit...), 0)); err == nil {
		t.Fatal("commit with a trailing octet accepted")
	}
}

func TestDecodeAllVersionTenFinalizeResults(t *testing.T) {
	root := Hash{0: 0xa5, 31: 0x5a}
	blockID := Hash{0: 0x5a, 31: 0xa5}
	expected := 3 + resultCodeCountV10
	block, err := decodeFinalizeV10(finalizeBodyV10(root, blockID), expected)
	if err != nil {
		t.Fatal(err)
	}
	if block.StateRoot != root || block.BlockID != blockID ||
		len(block.TransactionResults) != expected {
		t.Fatalf("unexpected finalized block: %#v", block)
	}
	for index, result := range block.TransactionResults[3:] {
		if result.Data[receiptResultOffset] != byte(index) ||
			result.Code != resultCodeV10(byte(index)) {
			t.Fatalf("execution result %d: %#v", index, result)
		}
	}
}

func TestVersionTenFinalizeRefusals(t *testing.T) {
	body := finalizeBodyV10(Hash{0: 0xa5}, Hash{31: 0x5a})
	expected := 3 + resultCodeCountV10
	firstReceipt := 32 + 32 + 4 + 3*8
	firstReceiptBody := firstReceipt + 8
	corrupt := func(mutate func([]byte) []byte) []byte {
		return mutate(append([]byte(nil), body...))
	}
	invalid := map[string][]byte{
		"count": corrupt(func(value []byte) []byte {
			binary.BigEndian.PutUint32(value[64:68], uint32(expected-1))
			return value
		}),
		"truncated identifier": append([]byte(nil), body[:60]...),
		"trailing":             append(append([]byte(nil), body...), 0),
		"version-nine receipt": corrupt(func(value []byte) []byte {
			value[firstReceiptBody+5] = 9
			return value
		}),
		"result out of range": corrupt(func(value []byte) []byte {
			value[firstReceiptBody+receiptResultOffset] = resultCodeCountV10
			binary.BigEndian.PutUint32(value[firstReceipt:firstReceipt+4],
				resultCodeV10(resultCodeCountV10))
			return value
		}),
		"code disagrees with receipt": corrupt(func(value []byte) []byte {
			binary.BigEndian.PutUint32(value[firstReceipt:firstReceipt+4], 256+1)
			return value
		}),
		"receipt length": corrupt(func(value []byte) []byte {
			binary.BigEndian.PutUint32(value[firstReceipt+4:firstReceipt+8], 47)
			return value
		}),
		"admission data": corrupt(func(value []byte) []byte {
			binary.BigEndian.PutUint32(value[72:76], 1)
			return append(value[:76], append([]byte{0}, value[76:]...)...)
		}),
	}
	for name, value := range invalid {
		t.Run(name, func(t *testing.T) {
			if _, err := decodeFinalizeV10(value, expected); err == nil {
				t.Fatal("invalid FinalizeBlock response accepted")
			}
		})
	}
}

// Versions nine and ten have the same finalized-block shape, so the receipt's
// version octet is the only thing that separates a well-formed block of each.
// The control beside the refusal is what makes it about that octet.
//
// **The version-nine receipt is a literal**, `PSRC` with a version octet of 9,
// rather than a call into the sibling decoder: ADR 0104's step 7 deletes version
// nine, and a pin that dies with the artifact it pins proves nothing afterwards.
// The reverse direction is version nine's test.
func TestVersionTenRefusesAVersionNineBlock(t *testing.T) {
	receiptV9 := make([]byte, receiptBytesV10)
	copy(receiptV9, []byte{'P', 'S', 'R', 'C', 0, 9})
	body := func(receipt []byte) []byte {
		value := append([]byte(nil), make([]byte, 64)...)
		value = appendU32(value, 1)
		value = appendU32(value, 0)
		return appendBlob(value, receipt)
	}
	if _, err := decodeFinalizeV10(body(receiptV9), 1); err == nil {
		t.Fatal("version ten accepted a version-nine finalized block")
	}
	if _, err := decodeFinalizeV10(body(receiptV10(0)), 1); err != nil {
		t.Fatalf("version ten refused its own finalized block: %v", err)
	}
}

// The figures that moved with the version, pinned to their literals.
//
// **Nothing above checks them**, and they fail differently. A stale receipt
// version breaks the happy path, so the first integration block would catch it.
// A stale result count would not: the codes it would cut off are the high ones,
// no fixture produces them, and the range would silently narrow. Every check
// above compares the constant to itself and would pass at either value.
func TestVersionTenFiguresAreTheContracts(t *testing.T) {
	if wireVersionV2 != 2 || receiptVersionV10 != 10 || resultCodeCountV10 != 50 ||
		applicationProtocolVersionV10 != 10 {
		t.Fatalf("figures are %d, %d, %d, %d", wireVersionV2, receiptVersionV10,
			resultCodeCountV10, applicationProtocolVersionV10)
	}
	if receiptPrefixV10[4] != 0 || receiptPrefixV10[5] != 10 {
		t.Fatalf("receipt prefix does not name version ten: %v", receiptPrefixV10)
	}
	if statusDecidedBlockFailedRange != 7 ||
		statusDecidedBlockFailedMonotonicity != 8 {
		t.Fatal("the timestamp statuses are not 7 and 8")
	}
	if DecisionTimestampBehindTolerance != 5 || DecisionNotExecutable != 7 {
		t.Fatal("the decision numbering is not calendar-v1's")
	}
	// The last defined result and the first undefined one, written out rather
	// than derived, so the boundary is a fact about the contract.
	// Version nine's last is still admitted, and so are the five version ten
	// adds, `APPROVAL_LIFETIME_EXCEEDED` at code 305 the last of them.
	for result := byte(44); result <= 49; result++ {
		accepted := TransactionResult{Code: 256 + uint32(result), Data: receiptV10(result)}
		if !validTransactionResultV10(accepted) {
			t.Fatalf("result %d was refused", result)
		}
	}
	refused := TransactionResult{Code: 256 + 50, Data: receiptV10(50)}
	if validTransactionResultV10(refused) {
		t.Fatal("result 50 was accepted")
	}
}

func FuzzVersionTenResponseDecoders(f *testing.F) {
	f.Add(make([]byte, 56))
	f.Add([]byte{5})
	f.Add(finalizeBodyV10(Hash{}, Hash{}))
	f.Fuzz(func(_ *testing.T, input []byte) {
		_, _ = decodeInfoV10(input)
		_, _ = decodeCommitV10(input)
		_, _ = decodeDecision(input)
		_, _ = decodeFinalizeV10(input, 0)
		_, _ = decodeFinalizeV10(input, 53)
		_, _ = decodeEnvelopeWithin(input,
			maximumStatus(wireVersionV2, KindFinalizeBlock))
		if len(input) == wireHeaderSize {
			_, _ = decodeHeaderAt(wireVersionV2, input, KindInfo, 1)
		}
	})
}
