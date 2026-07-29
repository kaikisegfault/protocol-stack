package devnet

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
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
	decoder := json.NewDecoder(io.LimitReader(response.Body, 4_194_304))
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
