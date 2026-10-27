package localapp

import (
	"errors"
	"fmt"
)

// The version-two frame's pieces that every ledger version speaking it shares:
// versions nine and ten, under `consensus-application-v2` and `-v3`. The frame
// is version one's with its version octet at 2, three request payloads that
// carry a timestamp, four response payloads that differ, and two statuses more.
// Version ten changes no payload shape, so it reads this frame unchanged (ADR
// 0110). These moved here from `wire_v9.go` so that ADR 0104's step 7 can
// delete that file whole.
//
// **Statuses 7 and 8 are reachable only on kind 6**, and that is a decoder
// rule here rather than a comment. They report a decided block whose stamp this
// machine's rules refuse, and a halt is the right answer only where the network
// has already decided. Kind 5 reports the same two conditions as decisions 2
// and 3 under status zero, because there the right answer is a vote. So a 7 or
// an 8 on any other kind, or on a version-one connection, is not an answer this
// client can hold. It is a protocol failure.
const (
	wireVersionV2 = 2
	// The two statuses version two adds, for C1 and C2 on a decided block.
	statusDecidedBlockFailedRange        = 7
	statusDecidedBlockFailedMonotonicity = 8

	// The result byte's position in the receipt. Versions nine and ten keep
	// the receipt layout versions seven and eight used, so this offset is
	// theirs; it moved here from `wire_v9.go`, as it had moved there from
	// `wire_v8.go` when ADR 0092 deleted that file.
	receiptResultOffset = 39
)

// The highest status a response to `kind` may carry at frame `version`.
func maximumStatus(version uint16, kind Kind) uint16 {
	if version == wireVersionV2 && kind == KindFinalizeBlock {
		return statusDecidedBlockFailedMonotonicity
	}
	return maximumStatusV1
}

// Decision is `ProcessProposal`'s eight-value answer under status zero. Values
// 0 through 5 are `calendar-v1`'s ordered conditions in its own numbering; 6
// and 7 are the application contract's own.
type Decision uint8

const (
	DecisionAccepted Decision = iota
	DecisionHeightNotNext
	DecisionTimestampRange
	DecisionTimestampNotMonotonic
	DecisionTimestampAheadOfTolerance
	DecisionTimestampBehindTolerance
	DecisionResourceBound
	DecisionNotExecutable
)

// One octet, and one of the eight. A ninth value would still vote REJECT and
// would report an outcome the contract does not name, so it is refused.
func decodeDecision(payload []byte) (Decision, error) {
	if len(payload) != 1 || payload[0] > byte(DecisionNotExecutable) {
		return 0, errors.New("invalid ProcessProposal decision")
	}
	return Decision(payload[0]), nil
}

var decisionNames = [...]string{
	"ACCEPTED",
	"HEIGHT_NOT_NEXT",
	"TIMESTAMP_RANGE",
	"TIMESTAMP_NOT_MONOTONIC",
	"TIMESTAMP_AHEAD_OF_TOLERANCE",
	"TIMESTAMP_BEHIND_TOLERANCE",
	"RESOURCE_BOUND",
	"NOT_EXECUTABLE",
}

// String is the decision's name in `consensus-application-v2`'s table, which is
// what an operator reads in the bridge's log.
func (d Decision) String() string {
	if int(d) < len(decisionNames) {
		return decisionNames[d]
	}
	return fmt.Sprintf("DECISION_%d", uint8(d))
}
