package bridge

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"fmt"
	"math"
	"strings"
	"sync"

	abci "github.com/cometbft/cometbft/abci/types"
	"github.com/cometbft/cometbft/version"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/localapp"
)

const (
	applicationData    = "protocol-stack"
	applicationVersion = "1.0.0"
	// The result codes an executed transaction can carry are the ledger
	// version's, so the codespace that names them is too: version one has
	// eight and version seven has thirty-three.
	codespaceV1 = "protocol-stack-v1"
	codespaceV7 = "protocol-stack-v7"
)

// FinalizedBlock is what this bridge needs out of a finalized block, whichever
// ledger version produced it. **Version seven names the block it executed and
// version one has nothing to name it with**, so the identifier is a pointer:
// absent is unmistakable, where a zero hash could be read as a real one.
type FinalizedBlock struct {
	StateRoot          localapp.Hash
	BlockID            *localapp.Hash
	TransactionResults []localapp.TransactionResult
}

type localApplication interface {
	Info() (localapp.Info, error)
	InitChain(localapp.Hash, uint64, []byte) (localapp.Hash, error)
	CheckTransaction([]byte) (uint32, error)
	PrepareProposal(int64, [][]byte) ([][]byte, error)
	ProcessProposal(uint64, [][]byte) (bool, error)
	FinalizeBlock(uint64, [][]byte) (FinalizedBlock, error)
	Commit() (localapp.CommittedHead, error)
}

type Application struct {
	abci.BaseApplication
	mutex     sync.Mutex
	local     localApplication
	codespace string
	// The greatest height the local application has said it has committed,
	// learned from its own answers to Info and Commit and never counted here.
	// A local application refuses a finalize at any height that is not its
	// current plus one -- **including one it has already committed** -- and
	// that refusal is terminal, so forwarding such a request would brick a
	// node that a clear error leaves restartable.
	committedHeight uint64
}

var _ abci.Application = (*Application)(nil)

// New bridges a version-one local application.
func New(local localApplication) *Application {
	return &Application{local: local, codespace: codespaceV1}
}

// NewV7 bridges a version-seven local application. The seven ABCI operations
// are the same operations; what differs is the codespace its result codes
// belong to and the block identifier its finalized block carries.
func NewV7(local localApplication) *Application {
	return &Application{local: local, codespace: codespaceV7}
}

func (a *Application) Info(
	_ context.Context,
	request *abci.RequestInfo,
) (*abci.ResponseInfo, error) {
	if request == nil || request.AbciVersion != version.ABCIVersion {
		return nil, errors.New("ABCI version must be exactly 2.0.0")
	}
	a.mutex.Lock()
	defer a.mutex.Unlock()
	info, err := a.local.Info()
	if err != nil {
		return nil, fmt.Errorf("local Info: %w", err)
	}
	if info.Height > math.MaxInt64 {
		return nil, errors.New("application height exceeds signed ABCI range")
	}
	a.observeCommitted(info.Height)
	return &abci.ResponseInfo{
		Data:             applicationData,
		Version:          applicationVersion,
		AppVersion:       info.ApplicationVersion,
		LastBlockHeight:  int64(info.Height),
		LastBlockAppHash: info.StateRoot[:],
	}, nil
}

func decodeChainID(value string) (localapp.Hash, error) {
	var result localapp.Hash
	if len(value) != 46 || !strings.HasPrefix(value, "ps-") {
		return result, errors.New("invalid protocol chain ID")
	}
	encoded := value[3:]
	decoded, err := base64.RawURLEncoding.DecodeString(encoded)
	if err != nil || len(decoded) != len(result) ||
		base64.RawURLEncoding.EncodeToString(decoded) != encoded {
		return result, errors.New("noncanonical protocol chain ID")
	}
	copy(result[:], decoded)
	return result, nil
}

func (a *Application) InitChain(
	_ context.Context,
	request *abci.RequestInitChain,
) (*abci.ResponseInitChain, error) {
	if request == nil || request.InitialHeight < 0 {
		return nil, errors.New("invalid InitChain request")
	}
	chainID, err := decodeChainID(request.ChainId)
	if err != nil {
		return nil, err
	}
	if len(request.AppStateBytes) > localapp.MaximumAppStateSize {
		return nil, errors.New("InitChain application state exceeds limit")
	}
	a.mutex.Lock()
	defer a.mutex.Unlock()
	root, err := a.local.InitChain(
		chainID, uint64(request.InitialHeight), request.AppStateBytes)
	if err != nil {
		return nil, fmt.Errorf("local InitChain: %w", err)
	}
	return &abci.ResponseInitChain{AppHash: root[:]}, nil
}

func (a *Application) CheckTx(
	_ context.Context,
	request *abci.RequestCheckTx,
) (*abci.ResponseCheckTx, error) {
	if request == nil ||
		(request.Type != abci.CheckTxType_New &&
			request.Type != abci.CheckTxType_Recheck) {
		return nil, errors.New("invalid CheckTx request")
	}
	if len(request.Tx) > localapp.MaximumTransactionSize {
		return nil, errors.New("CheckTx transaction exceeds limit")
	}
	a.mutex.Lock()
	defer a.mutex.Unlock()
	code, err := a.local.CheckTransaction(request.Tx)
	if err != nil {
		return nil, fmt.Errorf("local CheckTx: %w", err)
	}
	response := &abci.ResponseCheckTx{Code: code}
	if code != 0 {
		response.Codespace = a.codespace
	}
	return response, nil
}

func proposalPrefix(transactions [][]byte, maximum int64) ([][]byte, error) {
	if maximum < 0 {
		return nil, errors.New("negative PrepareProposal byte limit")
	}
	limit := maximum
	if limit > localapp.MaximumBlockSize {
		limit = localapp.MaximumBlockSize
	}
	total := int64(0)
	count := len(transactions)
	if count > localapp.MaximumBlockInputs {
		count = localapp.MaximumBlockInputs
	}
	for index := 0; index < count; index++ {
		size := int64(len(transactions[index]))
		if size > localapp.MaximumTransactionSize || size > limit-total {
			return transactions[:index], nil
		}
		total += size
	}
	return transactions[:count], nil
}

func (a *Application) PrepareProposal(
	_ context.Context,
	request *abci.RequestPrepareProposal,
) (*abci.ResponsePrepareProposal, error) {
	if request == nil {
		return nil, errors.New("nil PrepareProposal request")
	}
	prefix, err := proposalPrefix(request.Txs, request.MaxTxBytes)
	if err != nil {
		return nil, err
	}
	a.mutex.Lock()
	defer a.mutex.Unlock()
	prepared, err := a.local.PrepareProposal(request.MaxTxBytes, prefix)
	if err != nil {
		return nil, fmt.Errorf("local PrepareProposal: %w", err)
	}
	if len(prepared) != len(prefix) {
		return nil, errors.New("local PrepareProposal changed prefix length")
	}
	for index := range prepared {
		if !bytes.Equal(prepared[index], prefix[index]) {
			return nil, errors.New("local PrepareProposal changed transaction bytes")
		}
	}
	return &abci.ResponsePrepareProposal{Txs: prepared}, nil
}

func validateBlock(transactions [][]byte) bool {
	if len(transactions) > localapp.MaximumBlockInputs {
		return false
	}
	total := 0
	for _, transaction := range transactions {
		if len(transaction) > localapp.MaximumTransactionSize ||
			len(transaction) > localapp.MaximumBlockSize-total {
			return false
		}
		total += len(transaction)
	}
	return true
}

func (a *Application) ProcessProposal(
	_ context.Context,
	request *abci.RequestProcessProposal,
) (*abci.ResponseProcessProposal, error) {
	if request == nil || request.Height < 0 {
		return nil, errors.New("invalid ProcessProposal height")
	}
	if !validateBlock(request.Txs) {
		return &abci.ResponseProcessProposal{
			Status: abci.ResponseProcessProposal_REJECT,
		}, nil
	}
	a.mutex.Lock()
	defer a.mutex.Unlock()
	accept, err := a.local.ProcessProposal(
		uint64(request.Height), request.Txs)
	if err != nil {
		return nil, fmt.Errorf("local ProcessProposal: %w", err)
	}
	status := abci.ResponseProcessProposal_REJECT
	if accept {
		status = abci.ResponseProcessProposal_ACCEPT
	}
	return &abci.ResponseProcessProposal{Status: status}, nil
}

// The local application has told this adapter which heights it has committed.
// Its own answers are the only source: nothing here counts blocks.
func (a *Application) observeCommitted(height uint64) {
	if height > a.committedHeight {
		a.committedHeight = height
	}
}

// The protocol's own name for the block, carried out to where an operator or a
// peer-facing tool can read it. ABCI has no field for a second block
// identifier, and a value that crosses a process boundary and is then
// discarded is a value the next simplification deletes.
//
// **It is observable rather than consensus-visible.** A block event is not
// hashed into anything CometBFT agrees on; only a transaction result's code
// and data reach `LastResultsHash`.
func blockIdentityEvent(identifier localapp.Hash) abci.Event {
	return abci.Event{
		Type: "protocol_block",
		Attributes: []abci.EventAttribute{{
			Key:   "id",
			Value: strings.ToUpper(hex.EncodeToString(identifier[:])),
			Index: true,
		}},
	}
}

func (a *Application) FinalizeBlock(
	_ context.Context,
	request *abci.RequestFinalizeBlock,
) (*abci.ResponseFinalizeBlock, error) {
	if request == nil || request.Height < 0 || !validateBlock(request.Txs) {
		return nil, errors.New("invalid FinalizeBlock request")
	}
	a.mutex.Lock()
	defer a.mutex.Unlock()
	height := uint64(request.Height)
	// **This is the replay handshake, and it is a guard rather than a
	// reconciliation.** CometBFT v0.39.4 replays an already-committed height
	// against a mock application built from its own saved response, precisely
	// so the real one is not asked to commit a block twice, so no engine this
	// adapter is pinned to reaches this. It is here because the consequence if
	// one ever did is a local application that latches terminally on a
	// contradiction it did not commit, and a legible error the engine can stop
	// on is worth one comparison per block.
	if height <= a.committedHeight {
		return nil, fmt.Errorf(
			"FinalizeBlock at height %d, which the application has committed "+
				"through height %d", height, a.committedHeight)
	}
	block, err := a.local.FinalizeBlock(height, request.Txs)
	if err != nil {
		return nil, fmt.Errorf("local FinalizeBlock: %w", err)
	}
	results := make([]*abci.ExecTxResult, len(block.TransactionResults))
	for index, result := range block.TransactionResults {
		results[index] = &abci.ExecTxResult{
			Code: result.Code,
			Data: result.Data,
		}
		if result.Code != 0 {
			results[index].Codespace = a.codespace
		}
	}
	response := &abci.ResponseFinalizeBlock{
		TxResults: results,
		AppHash:   block.StateRoot[:],
	}
	if block.BlockID != nil {
		response.Events = []abci.Event{blockIdentityEvent(*block.BlockID)}
	}
	return response, nil
}

func (a *Application) Commit(
	_ context.Context,
	request *abci.RequestCommit,
) (*abci.ResponseCommit, error) {
	if request == nil {
		return nil, errors.New("nil Commit request")
	}
	a.mutex.Lock()
	defer a.mutex.Unlock()
	head, err := a.local.Commit()
	if err != nil {
		return nil, fmt.Errorf("local Commit: %w", err)
	}
	a.observeCommitted(head.Height)
	return &abci.ResponseCommit{RetainHeight: 0}, nil
}
