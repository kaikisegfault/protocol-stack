package bridge

import (
	"bytes"
	"context"
	"encoding/base64"
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
	codespace          = "protocol-stack-v1"
)

type localApplication interface {
	Info() (localapp.Info, error)
	InitChain(localapp.Hash, uint64, []byte) (localapp.Hash, error)
	CheckTransaction([]byte) (uint32, error)
	PrepareProposal(int64, [][]byte) ([][]byte, error)
	ProcessProposal(uint64, [][]byte) (bool, error)
	FinalizeBlock(uint64, [][]byte) (localapp.FinalizedBlock, error)
	Commit() (localapp.CommittedHead, error)
}

type Application struct {
	abci.BaseApplication
	mutex sync.Mutex
	local localApplication
}

var _ abci.Application = (*Application)(nil)

func New(local localApplication) *Application {
	return &Application{local: local}
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
		response.Codespace = codespace
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

func (a *Application) FinalizeBlock(
	_ context.Context,
	request *abci.RequestFinalizeBlock,
) (*abci.ResponseFinalizeBlock, error) {
	if request == nil || request.Height < 0 || !validateBlock(request.Txs) {
		return nil, errors.New("invalid FinalizeBlock request")
	}
	a.mutex.Lock()
	defer a.mutex.Unlock()
	block, err := a.local.FinalizeBlock(
		uint64(request.Height), request.Txs)
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
			results[index].Codespace = codespace
		}
	}
	return &abci.ResponseFinalizeBlock{
		TxResults: results,
		AppHash:   block.StateRoot[:],
	}, nil
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
	if _, err := a.local.Commit(); err != nil {
		return nil, fmt.Errorf("local Commit: %w", err)
	}
	return &abci.ResponseCommit{RetainHeight: 0}, nil
}
