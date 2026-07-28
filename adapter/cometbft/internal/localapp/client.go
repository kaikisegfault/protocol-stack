package localapp

import (
	"errors"
	"fmt"
	"io"
	"math"
	"net"
	"path/filepath"
	"sync"
)

type Client struct {
	mutex      sync.Mutex
	connection net.Conn
	requestID  uint64
	terminal   error
}

func Dial(path string) (*Client, error) {
	if !filepath.IsAbs(path) {
		return nil, errors.New("local application socket path must be absolute")
	}
	connection, err := net.Dial("unix", path)
	if err != nil {
		return nil, fmt.Errorf("connect to local application: %w", err)
	}
	return &Client{connection: connection}, nil
}

func newClient(connection net.Conn) *Client {
	return &Client{connection: connection}
}

func (c *Client) fail(err error) error {
	if c.terminal == nil {
		c.terminal = err
		if closeErr := c.connection.Close(); closeErr != nil {
			c.terminal = errors.Join(c.terminal, closeErr)
		}
	}
	return c.terminal
}

func writeFull(connection net.Conn, value []byte) error {
	for len(value) != 0 {
		count, err := connection.Write(value)
		if count > 0 {
			value = value[count:]
		}
		if err != nil {
			return err
		}
		if count == 0 {
			return io.ErrUnexpectedEOF
		}
	}
	return nil
}

func (c *Client) call(kind Kind, payload []byte) ([]byte, error) {
	c.mutex.Lock()
	defer c.mutex.Unlock()

	if c.terminal != nil {
		return nil, c.terminal
	}
	if c.requestID == math.MaxUint64 {
		return nil, c.fail(errors.New("local application request IDs exhausted"))
	}
	c.requestID++
	frame, err := encodeFrame(kind, c.requestID, payload)
	if err != nil {
		return nil, err
	}
	if err := writeFull(c.connection, frame); err != nil {
		return nil, c.fail(fmt.Errorf("write local application request: %w", err))
	}

	header := make([]byte, wireHeaderSize)
	if _, err := io.ReadFull(c.connection, header); err != nil {
		return nil, c.fail(fmt.Errorf("read local application response header: %w", err))
	}
	size, err := decodeHeader(header, kind, c.requestID)
	if err != nil {
		return nil, c.fail(err)
	}
	payload = make([]byte, int(size))
	if _, err := io.ReadFull(c.connection, payload); err != nil {
		return nil, c.fail(fmt.Errorf("read local application response: %w", err))
	}
	value, err := decodeEnvelope(payload)
	if _, ok := err.(*ApplicationError); err != nil && !ok {
		return nil, c.fail(err)
	}
	return value, err
}

func (c *Client) protocolFailure(err error) error {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	return c.fail(fmt.Errorf("invalid local application response: %w", err))
}

func (c *Client) Close() error {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	if c.terminal != nil {
		return c.terminal
	}
	c.terminal = errors.New("local application client is closed")
	return c.connection.Close()
}

func (c *Client) Info() (Info, error) {
	payload, err := c.call(KindInfo, nil)
	if err != nil {
		return Info{}, err
	}
	input := reader{value: payload}
	version, err := input.u64()
	if err != nil {
		return Info{}, c.protocolFailure(err)
	}
	height, err := input.u64()
	if err != nil {
		return Info{}, c.protocolFailure(err)
	}
	root, err := readHash(&input)
	if err != nil {
		return Info{}, c.protocolFailure(err)
	}
	if err := input.finish(); err != nil {
		return Info{}, c.protocolFailure(err)
	}
	return Info{ApplicationVersion: version, Height: height, StateRoot: root}, nil
}

func (c *Client) InitChain(
	chainID Hash,
	initialHeight uint64,
	appState []byte,
) (Hash, error) {
	if len(appState) > MaximumAppStateSize {
		return Hash{}, errors.New("application state exceeds limit")
	}
	payload := make([]byte, 0, 44+len(appState))
	payload = append(payload, chainID[:]...)
	payload = appendU64(payload, initialHeight)
	payload = appendBlob(payload, appState)
	response, err := c.call(KindInitChain, payload)
	if err != nil {
		return Hash{}, err
	}
	input := reader{value: response}
	root, err := readHash(&input)
	if err != nil {
		return Hash{}, c.protocolFailure(err)
	}
	if err := input.finish(); err != nil {
		return Hash{}, c.protocolFailure(err)
	}
	return root, nil
}

func (c *Client) CheckTransaction(transaction []byte) (uint32, error) {
	if len(transaction) > MaximumTransactionSize {
		return 0, errors.New("transaction exceeds size limit")
	}
	response, err := c.call(
		KindCheckTransaction, appendBlob(nil, transaction))
	if err != nil {
		return 0, err
	}
	input := reader{value: response}
	code, err := input.u32()
	if err != nil {
		return 0, c.protocolFailure(err)
	}
	if code > 3 {
		return 0, c.protocolFailure(errors.New("invalid CheckTx result code"))
	}
	if err := input.finish(); err != nil {
		return 0, c.protocolFailure(err)
	}
	return code, nil
}

func (c *Client) PrepareProposal(
	maximumBytes int64,
	transactions [][]byte,
) ([][]byte, error) {
	payload := appendU64(nil, uint64(maximumBytes))
	payload, err := appendTransactions(payload, transactions)
	if err != nil {
		return nil, err
	}
	response, err := c.call(KindPrepareProposal, payload)
	if err != nil {
		return nil, err
	}
	input := reader{value: response}
	prepared, err := input.transactions()
	if err != nil {
		return nil, c.protocolFailure(err)
	}
	if err := input.finish(); err != nil {
		return nil, c.protocolFailure(err)
	}
	return prepared, nil
}

func (c *Client) ProcessProposal(
	height uint64,
	transactions [][]byte,
) (bool, error) {
	payload, err := blockPayload(height, transactions)
	if err != nil {
		return false, err
	}
	response, err := c.call(KindProcessProposal, payload)
	if err != nil {
		return false, err
	}
	if len(response) != 1 || response[0] > 1 {
		return false, c.protocolFailure(
			errors.New("invalid ProcessProposal response"))
	}
	return response[0] == 1, nil
}

func (c *Client) FinalizeBlock(
	height uint64,
	transactions [][]byte,
) (FinalizedBlock, error) {
	payload, err := blockPayload(height, transactions)
	if err != nil {
		return FinalizedBlock{}, err
	}
	response, err := c.call(KindFinalizeBlock, payload)
	if err != nil {
		return FinalizedBlock{}, err
	}
	block, err := decodeFinalize(response, len(transactions))
	if err != nil {
		return FinalizedBlock{}, c.protocolFailure(err)
	}
	return block, nil
}

func blockPayload(height uint64, transactions [][]byte) ([]byte, error) {
	return appendTransactions(appendU64(nil, height), transactions)
}

func (c *Client) Commit() (CommittedHead, error) {
	payload, err := c.call(KindCommit, nil)
	if err != nil {
		return CommittedHead{}, err
	}
	input := reader{value: payload}
	height, err := input.u64()
	if err != nil {
		return CommittedHead{}, c.protocolFailure(err)
	}
	root, err := readHash(&input)
	if err != nil {
		return CommittedHead{}, c.protocolFailure(err)
	}
	if err := input.finish(); err != nil {
		return CommittedHead{}, c.protocolFailure(err)
	}
	return CommittedHead{Height: height, StateRoot: root}, nil
}
