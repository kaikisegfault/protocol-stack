package localapp

import (
	"encoding/binary"
	"testing"
)

// The version-two frame's shared pieces, which versions nine and ten both read.
// These moved here from `wire_v9_test.go` with the code they test.

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

// The names an operator reads in the bridge's log are the contract's, and a
// value past the eight is named by number rather than mistaken for one of them.
func TestDecisionNamesAreTheContracts(t *testing.T) {
	names := map[Decision]string{
		DecisionAccepted:                  "ACCEPTED",
		DecisionHeightNotNext:             "HEIGHT_NOT_NEXT",
		DecisionTimestampRange:            "TIMESTAMP_RANGE",
		DecisionTimestampNotMonotonic:     "TIMESTAMP_NOT_MONOTONIC",
		DecisionTimestampAheadOfTolerance: "TIMESTAMP_AHEAD_OF_TOLERANCE",
		DecisionTimestampBehindTolerance:  "TIMESTAMP_BEHIND_TOLERANCE",
		DecisionResourceBound:             "RESOURCE_BOUND",
		DecisionNotExecutable:             "NOT_EXECUTABLE",
		Decision(8):                       "DECISION_8",
	}
	for decision, name := range names {
		if decision.String() != name {
			t.Fatalf("decision %d is named %q, not %q", decision, decision.String(), name)
		}
	}
}
