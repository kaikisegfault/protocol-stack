package localapp

import (
	"encoding/binary"
	"testing"
)

func receiptV9(result byte) []byte {
	receipt := make([]byte, receiptBytesV9)
	copy(receipt, receiptPrefixV9)
	receipt[receiptResultOffset] = result
	return receipt
}

// Every result a version-nine block can report: the three admission failures
// that carry no receipt, and all forty-five execution results.
func finalizeBodyV9(root, blockID Hash) []byte {
	body := append([]byte(nil), root[:]...)
	body = append(body, blockID[:]...)
	body = appendU32(body, 3+resultCodeCountV9)
	for code := uint32(1); code <= 3; code++ {
		body = appendU32(body, code)
		body = appendU32(body, 0)
	}
	for result := byte(0); result < resultCodeCountV9; result++ {
		body = appendU32(body, resultCodeV8(result))
		body = appendBlob(body, receiptV9(result))
	}
	return body
}

func versionTwoHeader(kind Kind, requestID uint64, size uint32) []byte {
	header := responseHeader(kind, requestID, size)
	binary.BigEndian.PutUint16(header[4:6], wireVersionV2)
	return header
}

func TestFrozenVersionTwoInfoFrame(t *testing.T) {
	frame, err := encodeFrameAt(wireVersionV2, KindInfo, 1, nil)
	if err != nil {
		t.Fatal(err)
	}
	expected := []byte{
		'P', 'S', 'A', 'P', 0, 2, 0, 1,
		0, 0, 0, 0, 0, 0, 0, 1,
		0, 0, 0, 0,
	}
	if string(frame) != string(expected) {
		t.Fatalf("Info frame = %x, want %x", frame, expected)
	}
}

// Each version's header decoder refuses the other's frame, and each accepts
// its own, so the refusal is about the version octet and nothing else.
func TestEachFrameVersionRefusesTheOther(t *testing.T) {
	one := responseHeader(KindInfo, 1, 0)
	two := versionTwoHeader(KindInfo, 1, 0)
	if _, err := decodeHeaderAt(wireVersionV2, one, KindInfo, 1); err == nil {
		t.Fatal("version two accepted a version-one response")
	}
	if _, err := decodeHeaderAt(wireVersion, two, KindInfo, 1); err == nil {
		t.Fatal("version one accepted a version-two response")
	}
	if _, err := decodeHeaderAt(wireVersionV2, two, KindInfo, 1); err != nil {
		t.Fatalf("version two refused its own response: %v", err)
	}
	if _, err := decodeHeaderAt(wireVersion, one, KindInfo, 1); err != nil {
		t.Fatalf("version one refused its own response: %v", err)
	}
}

// Statuses 7 and 8 on kind 6 over version two, and nowhere else.
func TestTimestampStatusesOnlyOnAFinalize(t *testing.T) {
	envelope := func(status uint16) []byte {
		value := make([]byte, 2, 6)
		binary.BigEndian.PutUint16(value, status)
		return appendU32(value, 0)
	}
	for _, status := range []uint16{
		statusDecidedBlockFailedRange, statusDecidedBlockFailedMonotonicity,
	} {
		_, err := decodeEnvelopeWithin(envelope(status),
			maximumStatus(wireVersionV2, KindFinalizeBlock))
		applicationError, ok := err.(*ApplicationError)
		if !ok || applicationError.Status != status {
			t.Fatalf("status %d on a finalize: %#v", status, err)
		}
		for kind := KindInfo; kind <= KindCommit; kind++ {
			if kind == KindFinalizeBlock {
				continue
			}
			_, err := decodeEnvelopeWithin(envelope(status),
				maximumStatus(wireVersionV2, kind))
			if _, ok := err.(*ApplicationError); ok || err == nil {
				t.Fatalf("status %d accepted on kind %d", status, kind)
			}
		}
		_, err = decodeEnvelopeWithin(envelope(status),
			maximumStatus(wireVersion, KindFinalizeBlock))
		if _, ok := err.(*ApplicationError); ok || err == nil {
			t.Fatalf("status %d accepted over version one", status)
		}
	}
	_, err := decodeEnvelopeWithin(envelope(9),
		maximumStatus(wireVersionV2, KindFinalizeBlock))
	if _, ok := err.(*ApplicationError); ok || err == nil {
		t.Fatal("status 9 accepted")
	}
}

func TestDecisions(t *testing.T) {
	for raw := byte(0); raw <= byte(DecisionNotExecutable); raw++ {
		decision, err := decodeDecision([]byte{raw})
		if err != nil || decision != Decision(raw) {
			t.Fatalf("decision %d = %d, %v", raw, decision, err)
		}
	}
	for name, payload := range map[string][]byte{
		"eight": {8}, "255": {255}, "empty": {}, "two octets": {0, 0},
	} {
		if _, err := decodeDecision(payload); err == nil {
			t.Fatalf("%s accepted as a decision", name)
		}
	}
}

// The two head responses, octet for octet, and refused when cut at any field or
// followed by anything.
func TestHeadResponsesCarryTheStamp(t *testing.T) {
	root := Hash{0: 9, 31: 9}
	info := appendU64(appendU64(appendU64(nil, 9), 4), 1_768_435_290_000)
	info = append(info, root[:]...)
	decoded, err := decodeInfoV9(info)
	if err != nil || decoded != (InfoV9{9, 4, 1_768_435_290_000, root}) {
		t.Fatalf("info = %#v, %v", decoded, err)
	}
	commit := info[8:]
	head, err := decodeCommitV9(commit)
	if err != nil || head != (CommittedHeadV9{4, 1_768_435_290_000, root}) {
		t.Fatalf("commit = %#v, %v", head, err)
	}
	for size := range len(info) {
		if _, err := decodeInfoV9(info[:size]); err == nil {
			t.Fatalf("info truncated to %d octets accepted", size)
		}
	}
	for size := range len(commit) {
		if _, err := decodeCommitV9(commit[:size]); err == nil {
			t.Fatalf("commit truncated to %d octets accepted", size)
		}
	}
	if _, err := decodeInfoV9(append(append([]byte(nil), info...), 0)); err == nil {
		t.Fatal("info with a trailing octet accepted")
	}
	if _, err := decodeCommitV9(append(append([]byte(nil), commit...), 0)); err == nil {
		t.Fatal("commit with a trailing octet accepted")
	}
}

func TestDecodeAllVersionNineFinalizeResults(t *testing.T) {
	root := Hash{0: 0xa5, 31: 0x5a}
	blockID := Hash{0: 0x5a, 31: 0xa5}
	expected := 3 + resultCodeCountV9
	block, err := decodeFinalizeV9(finalizeBodyV9(root, blockID), expected)
	if err != nil {
		t.Fatal(err)
	}
	if block.StateRoot != root || block.BlockID != blockID ||
		len(block.TransactionResults) != expected {
		t.Fatalf("unexpected finalized block: %#v", block)
	}
	for index, result := range block.TransactionResults[3:] {
		if result.Data[receiptResultOffset] != byte(index) ||
			result.Code != resultCodeV8(byte(index)) {
			t.Fatalf("execution result %d: %#v", index, result)
		}
	}
}

func TestVersionNineFinalizeRefusals(t *testing.T) {
	body := finalizeBodyV9(Hash{0: 0xa5}, Hash{31: 0x5a})
	expected := 3 + resultCodeCountV9
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
		"version-eight receipt": corrupt(func(value []byte) []byte {
			value[firstReceiptBody+5] = 8
			return value
		}),
		"result out of range": corrupt(func(value []byte) []byte {
			value[firstReceiptBody+receiptResultOffset] = resultCodeCountV9
			binary.BigEndian.PutUint32(value[firstReceipt:firstReceipt+4],
				resultCodeV8(resultCodeCountV9))
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
			if _, err := decodeFinalizeV9(value, expected); err == nil {
				t.Fatal("invalid FinalizeBlock response accepted")
			}
		})
	}
}

// Versions eight and nine have the same finalized-block shape, so the receipt's
// version octet is the only thing that separates a well-formed block of each.
// The control beside the refusal is what makes it about that octet.
func TestVersionNineRefusesAVersionEightBlock(t *testing.T) {
	body := func(receipt []byte) []byte {
		value := append([]byte(nil), make([]byte, 64)...)
		value = appendU32(value, 1)
		value = appendU32(value, 0)
		return appendBlob(value, receipt)
	}
	if _, err := decodeFinalizeV9(body(receiptV8(0)), 1); err == nil {
		t.Fatal("version nine accepted a version-eight finalized block")
	}
	if _, err := decodeFinalizeV9(body(receiptV9(0)), 1); err != nil {
		t.Fatalf("version nine refused its own finalized block: %v", err)
	}
	if _, err := decodeFinalizeV8(body(receiptV9(0)), 1); err == nil {
		t.Fatal("version eight accepted a version-nine finalized block")
	}
}

// The figures that moved with the version, pinned to their literals, for the
// reason `TestVersionEightFiguresAreTheContracts` records.
func TestVersionNineFiguresAreTheContracts(t *testing.T) {
	if wireVersionV2 != 2 || receiptVersionV9 != 9 || resultCodeCountV9 != 45 {
		t.Fatalf("figures are %d, %d, %d", wireVersionV2, receiptVersionV9,
			resultCodeCountV9)
	}
	if receiptPrefixV9[4] != 0 || receiptPrefixV9[5] != 9 {
		t.Fatalf("receipt prefix does not name version nine: %v", receiptPrefixV9)
	}
	if statusDecidedBlockFailedRange != 7 ||
		statusDecidedBlockFailedMonotonicity != 8 {
		t.Fatal("the timestamp statuses are not 7 and 8")
	}
	if DecisionTimestampBehindTolerance != 5 || DecisionNotExecutable != 7 {
		t.Fatal("the decision numbering is not calendar-v1's")
	}
}

func FuzzVersionNineResponseDecoders(f *testing.F) {
	f.Add(make([]byte, 56))
	f.Add([]byte{5})
	f.Add(finalizeBodyV9(Hash{}, Hash{}))
	f.Fuzz(func(_ *testing.T, input []byte) {
		_, _ = decodeInfoV9(input)
		_, _ = decodeCommitV9(input)
		_, _ = decodeDecision(input)
		_, _ = decodeFinalizeV9(input, 0)
		_, _ = decodeFinalizeV9(input, 48)
		_, _ = decodeEnvelopeWithin(input,
			maximumStatus(wireVersionV2, KindFinalizeBlock))
		if len(input) == wireHeaderSize {
			_, _ = decodeHeaderAt(wireVersionV2, input, KindInfo, 1)
		}
	})
}
