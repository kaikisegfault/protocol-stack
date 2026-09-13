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
//
// `replicas` names the replicas expected to be running, which is what
// convergence is then required of. The submitting node must be one of them: a
// transaction cannot be handed to a replica the caller has stopped, and
// refusing that here reports the caller's mistake instead of a connection
// error from a port nobody is listening on.
func Broadcast(
	ctx context.Context,
	devnet nodeconfig.Devnet,
	replicas Replicas,
	nodeIndex int,
	transaction []byte,
) (TransactionResult, error) {
	if err := replicas.validate(); err != nil {
		return TransactionResult{}, err
	}
	if !replicas.contains(nodeIndex) {
		return TransactionResult{}, fmt.Errorf(
			"transaction node index %d is not among the running replicas %s",
			nodeIndex, replicas)
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
		rejected := TransactionResult{
			Height:       height,
			CheckCode:    response.CheckTx.Code,
			FinalizeCode: response.TxResult.Code,
			Receipt:      receipt,
		}
		// A transaction the kernel refuses is still committed in a block, and
		// every replica must independently produce that refusal and the root it
		// leaves. So convergence is waited for here as it is on the success
		// path: an operator sees a rejection either way, and a caller that
		// deliberately provoked one can still ask what the network agreed on.
		// A CheckTx rejection never reached a block, so it has no height and no
		// convergence to report.
		if response.CheckTx.Code == 0 {
			health, healthErr := WaitForHealth(ctx, devnet, replicas)
			if healthErr != nil {
				return rejected, healthErr
			}
			rejected.Health = health
		}
		return rejected, errors.New("transaction was rejected")
	}
	health, err := WaitForHealth(ctx, devnet, replicas)
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
