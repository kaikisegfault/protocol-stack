package localapp

import "errors"

// ClientV10 is version nine's client rebound for version ten's ledger (ADR
// 0110): version one's client dialled at frame version two, with the five
// operations whose payloads version two changed. Its Info refuses any ledger
// but version ten's, and its finalized blocks carry version ten's receipts.
//
// The connection, the request-identifier discipline, the terminal latch, and
// the envelope are version one's, so they are the embedded client's.
// CheckTransaction and PrepareProposal are version one's operations too: their
// payloads did not change. They are promoted and carry version two's frame
// because the embedded client does.
type ClientV10 struct {
	*Client
}

func DialV10(path string) (*ClientV10, error) {
	client, err := Dial(path)
	if err != nil {
		return nil, err
	}
	return newClientV10(client), nil
}

// The version is set before the client is shared and before its first call,
// so no frame this client writes or reads is ever checked at version one.
func newClientV10(client *Client) *ClientV10 {
	client.version = wireVersionV2
	return &ClientV10{Client: client}
}

func (c *ClientV10) Info() (InfoV10, error) {
	payload, err := c.call(KindInfo, nil)
	if err != nil {
		return InfoV10{}, err
	}
	info, err := decodeInfoV10(payload)
	if err != nil {
		return InfoV10{}, c.protocolFailure(err)
	}
	return info, nil
}

// InitChain compares four values on the other side, version nine's four: the
// chain, the initial height, the genesis stamp, and the application state.
func (c *ClientV10) InitChain(
	chainID Hash,
	initialHeight uint64,
	genesisTimestamp uint64,
	appState []byte,
) (Hash, error) {
	if len(appState) > MaximumAppStateSize {
		return Hash{}, errors.New("application state exceeds limit")
	}
	response, err := c.call(KindInitChain, initChainPayloadV10(
		chainID, initialHeight, genesisTimestamp, appState))
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

// ProcessProposal answers a decision, and every decision is a vote. A nonzero
// decision is not an error: it is a peer's bad proposal, which is an ordinary
// event on a live network.
func (c *ClientV10) ProcessProposal(
	height uint64,
	timestamp uint64,
	transactions [][]byte,
) (Decision, error) {
	payload, err := blockPayloadV10(height, timestamp, transactions)
	if err != nil {
		return 0, err
	}
	response, err := c.call(KindProcessProposal, payload)
	if err != nil {
		return 0, err
	}
	decision, err := decodeDecision(response)
	if err != nil {
		return 0, c.protocolFailure(err)
	}
	return decision, nil
}

// FinalizeBlock may answer status 7 or 8 as an `*ApplicationError`. Either is
// fatal on the other side, and the bridge treats every nonzero status as an
// ABCI exception.
func (c *ClientV10) FinalizeBlock(
	height uint64,
	timestamp uint64,
	transactions [][]byte,
) (FinalizedBlockV10, error) {
	payload, err := blockPayloadV10(height, timestamp, transactions)
	if err != nil {
		return FinalizedBlockV10{}, err
	}
	response, err := c.call(KindFinalizeBlock, payload)
	if err != nil {
		return FinalizedBlockV10{}, err
	}
	block, err := decodeFinalizeV10(response, len(transactions))
	if err != nil {
		return FinalizedBlockV10{}, c.protocolFailure(err)
	}
	return block, nil
}

func (c *ClientV10) Commit() (CommittedHeadV10, error) {
	payload, err := c.call(KindCommit, nil)
	if err != nil {
		return CommittedHeadV10{}, err
	}
	head, err := decodeCommitV10(payload)
	if err != nil {
		return CommittedHeadV10{}, c.protocolFailure(err)
	}
	return head, nil
}
