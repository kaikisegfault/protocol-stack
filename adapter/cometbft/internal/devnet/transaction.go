package devnet

import (
	"context"
	"encoding/base64"
	"errors"
	"fmt"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

// TransactionResult contains exact committed RPC result fields.
type TransactionResult struct {
	Height       uint64
	CheckCode    uint32
	FinalizeCode uint32
	Receipt      []byte
	Health       NetworkHealth
}

// Broadcast submits exact transaction bytes and waits for replica convergence.
func Broadcast(
	ctx context.Context,
	devnet nodeconfig.Devnet,
	nodeIndex int,
	transaction []byte,
) (TransactionResult, error) {
	if nodeIndex < 0 || nodeIndex >= nodeconfig.DevnetNodeCount {
		return TransactionResult{}, errors.New("transaction node index is invalid")
	}
	if len(transaction) == 0 || len(transaction) > 1_048_576 {
		return TransactionResult{}, errors.New(
			"transaction must contain between 1 and 1048576 bytes")
	}
	var response struct {
		Height  string `json:"height"`
		CheckTx struct {
			Code uint32 `json:"code"`
		} `json:"check_tx"`
		TxResult struct {
			Code uint32 `json:"code"`
			Data string `json:"data"`
		} `json:"tx_result"`
	}
	client := newRPCClient()
	if err := client.call(
		ctx,
		devnet.Nodes[nodeIndex].RPCPort,
		"broadcast_tx_commit",
		map[string]any{
			"tx": base64.StdEncoding.EncodeToString(transaction),
		},
		&response,
	); err != nil {
		return TransactionResult{}, err
	}
	height, err := parseUint("committed height", response.Height)
	if err != nil {
		return TransactionResult{}, err
	}
	receipt, err := base64.StdEncoding.DecodeString(response.TxResult.Data)
	if err != nil {
		return TransactionResult{}, fmt.Errorf("decode receipt: %w", err)
	}
	if response.CheckTx.Code != 0 || response.TxResult.Code != 0 {
		return TransactionResult{
			Height:       height,
			CheckCode:    response.CheckTx.Code,
			FinalizeCode: response.TxResult.Code,
			Receipt:      receipt,
		}, errors.New("transaction was rejected")
	}
	health, err := WaitForHealth(ctx, devnet)
	if err != nil {
		return TransactionResult{}, err
	}
	if health.Height != height {
		return TransactionResult{}, fmt.Errorf(
			"replicas converged at height %d, want %d", health.Height, height)
	}
	return TransactionResult{
		Height:       height,
		CheckCode:    response.CheckTx.Code,
		FinalizeCode: response.TxResult.Code,
		Receipt:      receipt,
		Health:       health,
	}, nil
}
