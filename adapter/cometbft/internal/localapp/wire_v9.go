package localapp

import (
	"bytes"
	"errors"
	"fmt"
)

// Version nine speaks the version-two frame. It is version one's frame with its
// version octet at 2, three request payloads that carry a timestamp, four
// response payloads that differ, and two statuses more.
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

	receiptBytesV9 = 56
	// Named rather than written into the prefix, for the reason
	// `receiptVersionV8` records: it is the figure that moves with the ledger
	// version while looking like framing.
	receiptVersionV9 = 9
	// Version nine adds no result code, so its table is version eight's 45.
	resultCodeCountV9 = 45
)

var receiptPrefixV9 = []byte{
	'P', 'S', 'R', 'C', receiptVersionV9 >> 8, receiptVersionV9 & 0xFF,
}

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

// The durable head is two scalars and a root, so Info and Commit report both.
type InfoV9 struct {
	ApplicationVersion uint64
	Height             uint64
	Timestamp          uint64
	StateRoot          Hash
}

type CommittedHeadV9 struct {
	Height    uint64
	Timestamp uint64
	StateRoot Hash
}

// Version nine's finalized block is version eight's shape with version nine's
// receipts.
type FinalizedBlockV9 struct {
	StateRoot          Hash
	BlockID            Hash
	TransactionResults []TransactionResult
}

func blockPayloadV9(
	height uint64,
	timestamp uint64,
	transactions [][]byte,
) ([]byte, error) {
	return appendTransactions(appendU64(appendU64(nil, height), timestamp),
		transactions)
}

// Kind 2. The genesis stamp precedes the one variable-length field, so a
// decoder bounds the frame before it allocates.
func initChainPayloadV9(
	chainID Hash,
	initialHeight uint64,
	genesisTimestamp uint64,
	appState []byte,
) []byte {
	payload := make([]byte, 0, 52+len(appState))
	payload = append(payload, chainID[:]...)
	payload = appendU64(payload, initialHeight)
	payload = appendU64(payload, genesisTimestamp)
	return appendBlob(payload, appState)
}

func decodeInfoV9(payload []byte) (InfoV9, error) {
	input := reader{value: payload}
	var info InfoV9
	var err error
	if info.ApplicationVersion, err = input.u64(); err != nil {
		return InfoV9{}, err
	}
	if info.Height, err = input.u64(); err != nil {
		return InfoV9{}, err
	}
	if info.Timestamp, err = input.u64(); err != nil {
		return InfoV9{}, err
	}
	if info.StateRoot, err = readHash(&input); err != nil {
		return InfoV9{}, err
	}
	return info, input.finish()
}

func decodeCommitV9(payload []byte) (CommittedHeadV9, error) {
	input := reader{value: payload}
	var head CommittedHeadV9
	var err error
	if head.Height, err = input.u64(); err != nil {
		return CommittedHeadV9{}, err
	}
	if head.Timestamp, err = input.u64(); err != nil {
		return CommittedHeadV9{}, err
	}
	if head.StateRoot, err = readHash(&input); err != nil {
		return CommittedHeadV9{}, err
	}
	return head, input.finish()
}

// One octet, and one of the eight. A ninth value would still vote REJECT and
// would report an outcome the contract does not name, so it is refused.
func decodeDecision(payload []byte) (Decision, error) {
	if len(payload) != 1 || payload[0] > byte(DecisionNotExecutable) {
		return 0, errors.New("invalid ProcessProposal decision")
	}
	return Decision(payload[0]), nil
}

// The declared code and the encoded receipt must be the same fact, and the
// receipt must say it is version nine's.
func validTransactionResultV9(result TransactionResult) bool {
	if result.Code >= 1 && result.Code <= 3 {
		return len(result.Data) == 0
	}
	if len(result.Data) != receiptBytesV9 ||
		!bytes.Equal(result.Data[:len(receiptPrefixV9)], receiptPrefixV9) {
		return false
	}
	rawResult := result.Data[receiptResultOffset]
	if rawResult == 0 {
		return result.Code == 0
	}
	return rawResult < resultCodeCountV9 && result.Code == 256+uint32(rawResult)
}

func decodeFinalizeV9(
	payload []byte,
	expectedCount int,
) (FinalizedBlockV9, error) {
	input := reader{value: payload}
	root, err := readHash(&input)
	if err != nil {
		return FinalizedBlockV9{}, err
	}
	blockID, err := readHash(&input)
	if err != nil {
		return FinalizedBlockV9{}, err
	}
	count, err := input.u32()
	if err != nil {
		return FinalizedBlockV9{}, err
	}
	if count > MaximumBlockInputs || int(count) != expectedCount ||
		int(count) > input.remaining()/8 {
		return FinalizedBlockV9{}, errors.New("invalid FinalizeBlock result count")
	}
	results := make([]TransactionResult, 0, int(count))
	for range count {
		code, err := input.u32()
		if err != nil {
			return FinalizedBlockV9{}, err
		}
		data, err := input.blob(receiptBytesV9)
		if err != nil {
			return FinalizedBlockV9{}, err
		}
		result := TransactionResult{Code: code, Data: data}
		if !validTransactionResultV9(result) {
			return FinalizedBlockV9{}, errors.New("invalid FinalizeBlock result")
		}
		results = append(results, result)
	}
	if err := input.finish(); err != nil {
		return FinalizedBlockV9{}, err
	}
	return FinalizedBlockV9{
		StateRoot:          root,
		BlockID:            blockID,
		TransactionResults: results,
	}, nil
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
