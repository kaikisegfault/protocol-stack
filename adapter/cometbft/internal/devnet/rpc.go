package devnet

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"sort"
	"strconv"
	"time"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

type rpcClient struct {
	http *http.Client
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    string `json:"data"`
}

type rpcEnvelope struct {
	Result json.RawMessage `json:"result"`
	Error  *rpcError       `json:"error"`
}

type statusResult struct {
	NodeInfo struct {
		ID      string `json:"id"`
		Network string `json:"network"`
	} `json:"node_info"`
	SyncInfo struct {
		LatestBlockHeight string `json:"latest_block_height"`
		LatestAppHash     string `json:"latest_app_hash"`
	} `json:"sync_info"`
}

type netInfoResult struct {
	NPeers string `json:"n_peers"`
	Peers  []struct {
		NodeInfo struct {
			ID string `json:"id"`
		} `json:"node_info"`
	} `json:"peers"`
}

type validatorsResult struct {
	BlockHeight string `json:"block_height"`
	Validators  []struct {
		Address     string `json:"address"`
		VotingPower string `json:"voting_power"`
	} `json:"validators"`
}

type abciInfoResult struct {
	Response struct {
		LastBlockHeight  string `json:"last_block_height"`
		LastBlockAppHash string `json:"last_block_app_hash"`
	} `json:"response"`
}

// NetworkHealth is the agreed current result of all four replicas.
type NetworkHealth struct {
	ChainID         string
	Height          uint64
	ApplicationRoot nodeconfig.Hash
	HeaderHeight    uint64
	HeaderAppHash   []byte
}

// TransactionResult contains exact committed RPC result fields.
type TransactionResult struct {
	Height       uint64
	CheckCode    uint32
	FinalizeCode uint32
	Receipt      []byte
	Health       NetworkHealth
}

func newRPCClient() rpcClient {
	return rpcClient{http: &http.Client{Timeout: 4 * time.Second}}
}

func (client rpcClient) call(
	ctx context.Context,
	port int,
	method string,
	params any,
	target any,
) error {
	body, err := json.Marshal(map[string]any{
		"jsonrpc": "2.0",
		"id":      "protocol-stack",
		"method":  method,
		"params":  params,
	})
	if err != nil {
		return fmt.Errorf("encode RPC %s: %w", method, err)
	}
	request, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		fmt.Sprintf("http://127.0.0.1:%d", port),
		bytes.NewReader(body),
	)
	if err != nil {
		return fmt.Errorf("create RPC %s: %w", method, err)
	}
	request.Header.Set("Content-Type", "application/json")
	response, err := client.http.Do(request)
	if err != nil {
		return fmt.Errorf("RPC %s: %w", method, err)
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return fmt.Errorf("RPC %s returned HTTP %s", method, response.Status)
	}
	var envelope rpcEnvelope
	decoder := json.NewDecoder(response.Body)
	if err := decoder.Decode(&envelope); err != nil {
		return fmt.Errorf("decode RPC %s: %w", method, err)
	}
	if envelope.Error != nil {
		return fmt.Errorf(
			"RPC %s failed (%d): %s %s",
			method,
			envelope.Error.Code,
			envelope.Error.Message,
			envelope.Error.Data,
		)
	}
	if len(envelope.Result) == 0 {
		return fmt.Errorf("RPC %s omitted result", method)
	}
	if target != nil {
		if err := json.Unmarshal(envelope.Result, target); err != nil {
			return fmt.Errorf("decode RPC %s result: %w", method, err)
		}
	}
	return nil
}

// CheckHealth performs one complete four-replica health observation.
func CheckHealth(
	ctx context.Context,
	devnet nodeconfig.Devnet,
) (NetworkHealth, error) {
	client := newRPCClient()
	statuses := make([]statusResult, nodeconfig.DevnetNodeCount)
	networks := make([]netInfoResult, nodeconfig.DevnetNodeCount)
	heads := make([]ApplicationHead, nodeconfig.DevnetNodeCount)
	validators := make([]validatorsResult, nodeconfig.DevnetNodeCount)
	var infos [nodeconfig.DevnetNodeCount]abciInfoResult

	for index, node := range devnet.Nodes {
		var health map[string]any
		if err := client.call(
			ctx, node.RPCPort, "health", map[string]any{}, &health); err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		if len(health) != 0 {
			return NetworkHealth{}, fmt.Errorf(
				"node %d returned nonempty health result", index)
		}
		if err := client.call(
			ctx, node.RPCPort, "status", map[string]any{},
			&statuses[index],
		); err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		if err := client.call(
			ctx, node.RPCPort, "net_info", map[string]any{},
			&networks[index],
		); err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		if err := client.call(
			ctx, node.RPCPort, "abci_info", map[string]any{},
			&infos[index],
		); err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		head, err := ReadApplicationHead(ctx, node.ApplicationSocket)
		if err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		heads[index] = head
	}

	health, err := compareHeads(statuses, infos, heads)
	if err != nil {
		return NetworkHealth{}, err
	}
	validatorHeight := health.Height
	if validatorHeight == 0 {
		validatorHeight = 1
	}
	for index, node := range devnet.Nodes {
		if err := client.call(
			ctx,
			node.RPCPort,
			"validators",
			map[string]any{
				"height":   strconv.FormatUint(validatorHeight, 10),
				"page":     "1",
				"per_page": "100",
			},
			&validators[index],
		); err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
	}
	if err := comparePeers(statuses, networks); err != nil {
		return NetworkHealth{}, err
	}
	if err := compareValidators(validators); err != nil {
		return NetworkHealth{}, err
	}
	return health, nil
}

func compareHeads(
	statuses []statusResult,
	infos [nodeconfig.DevnetNodeCount]abciInfoResult,
	heads []ApplicationHead,
) (NetworkHealth, error) {
	var expected NetworkHealth
	for index := range nodeconfig.DevnetNodeCount {
		statusHeight, err := parseUint(
			"latest block height", statuses[index].SyncInfo.LatestBlockHeight)
		if err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		headerHash, err := hex.DecodeString(statuses[index].SyncInfo.LatestAppHash)
		if err != nil {
			return NetworkHealth{}, fmt.Errorf(
				"node %d latest application hash: %w", index, err)
		}
		infoHeight, err := parseUint(
			"ABCI height", infos[index].Response.LastBlockHeight)
		if err != nil {
			return NetworkHealth{}, fmt.Errorf("node %d: %w", index, err)
		}
		infoRoot, err := base64.StdEncoding.DecodeString(
			infos[index].Response.LastBlockAppHash)
		if err != nil || len(infoRoot) != len(nodeconfig.Hash{}) {
			return NetworkHealth{}, fmt.Errorf(
				"node %d returned invalid ABCI application root", index)
		}
		if heads[index].Height != infoHeight ||
			!bytes.Equal(heads[index].Root[:], infoRoot) {
			return NetworkHealth{}, fmt.Errorf(
				"node %d ABCI and C++ heads differ", index)
		}
		var root nodeconfig.Hash
		copy(root[:], infoRoot)
		current := NetworkHealth{
			ChainID:         statuses[index].NodeInfo.Network,
			Height:          infoHeight,
			ApplicationRoot: root,
			HeaderHeight:    statusHeight,
			HeaderAppHash:   headerHash,
		}
		if current.ChainID == "" || statuses[index].NodeInfo.ID == "" {
			return NetworkHealth{}, fmt.Errorf(
				"node %d omitted network identity", index)
		}
		if index == 0 {
			expected = current
		} else if current.ChainID != expected.ChainID ||
			current.Height != expected.Height ||
			current.ApplicationRoot != expected.ApplicationRoot ||
			current.HeaderHeight != expected.HeaderHeight ||
			!bytes.Equal(current.HeaderAppHash, expected.HeaderAppHash) {
			return NetworkHealth{}, errors.New(
				"validator replicas have not converged")
		}
	}
	return expected, nil
}

func comparePeers(statuses []statusResult, networks []netInfoResult) error {
	nodeIDs := make(map[string]struct{}, nodeconfig.DevnetNodeCount)
	for index, status := range statuses {
		if _, duplicate := nodeIDs[status.NodeInfo.ID]; duplicate {
			return errors.New("validator RPC node IDs are not distinct")
		}
		if status.NodeInfo.ID == "" {
			return fmt.Errorf("node %d omitted node ID", index)
		}
		nodeIDs[status.NodeInfo.ID] = struct{}{}
	}
	for index, network := range networks {
		count, err := parseUint("peer count", network.NPeers)
		if err != nil || count != nodeconfig.DevnetNodeCount-1 ||
			len(network.Peers) != nodeconfig.DevnetNodeCount-1 {
			return fmt.Errorf("node %d does not have exactly three peers", index)
		}
		expected := make(map[string]struct{}, nodeconfig.DevnetNodeCount-1)
		for id := range nodeIDs {
			if id != statuses[index].NodeInfo.ID {
				expected[id] = struct{}{}
			}
		}
		for _, peer := range network.Peers {
			if _, present := expected[peer.NodeInfo.ID]; !present {
				return fmt.Errorf("node %d reported unexpected peer", index)
			}
			delete(expected, peer.NodeInfo.ID)
		}
		if len(expected) != 0 {
			return fmt.Errorf("node %d omitted a direct peer", index)
		}
	}
	return nil
}

func compareValidators(results []validatorsResult) error {
	var expected []string
	for index, result := range results {
		if len(result.Validators) != nodeconfig.DevnetNodeCount {
			return fmt.Errorf(
				"node %d does not report four validators", index)
		}
		current := make([]string, 0, nodeconfig.DevnetNodeCount)
		for _, validator := range result.Validators {
			power, err := parseUint("validator power", validator.VotingPower)
			if err != nil || power != 10 || validator.Address == "" {
				return fmt.Errorf(
					"node %d returned invalid validator set", index)
			}
			current = append(current, validator.Address)
		}
		sort.Strings(current)
		if index == 0 {
			expected = current
		} else if !equalStrings(current, expected) {
			return errors.New("validator replicas report different validator sets")
		}
	}
	return nil
}

func equalStrings(left, right []string) bool {
	if len(left) != len(right) {
		return false
	}
	for index := range left {
		if left[index] != right[index] {
			return false
		}
	}
	return true
}

func parseUint(name, value string) (uint64, error) {
	result, err := strconv.ParseUint(value, 10, 64)
	if err != nil {
		return 0, fmt.Errorf("%s is invalid: %w", name, err)
	}
	return result, nil
}

// WaitForHealth retries until one complete health observation succeeds.
func WaitForHealth(
	ctx context.Context,
	devnet nodeconfig.Devnet,
) (NetworkHealth, error) {
	var lastError error
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()
	for {
		health, err := CheckHealth(ctx, devnet)
		if err == nil {
			return health, nil
		}
		lastError = err
		select {
		case <-ctx.Done():
			return NetworkHealth{}, fmt.Errorf(
				"devnet health: %w (last observation: %v)",
				ctx.Err(), lastError)
		case <-ticker.C:
		}
	}
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
