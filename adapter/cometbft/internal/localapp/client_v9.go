package localapp

import "errors"

// ClientV9 is version one's client dialled at frame version two, with the five
// operations whose payloads version two changed.
//
// The connection, the request-identifier discipline, the terminal latch, and
// the envelope are version one's, so they are the embedded client's.
// CheckTransaction and PrepareProposal are version one's operations too: their
// payloads did not change. They are promoted and carry version two's frame
// because the embedded client does.
type ClientV9 struct {
	*Client
}

func DialV9(path string) (*ClientV9, error) {
	client, err := Dial(path)
	if err != nil {
		return nil, err
	}
	return newClientV9(client), nil
}

// The version is set before the client is shared and before its first call,
// so no frame this client writes or reads is ever checked at version one.
func newClientV9(client *Client) *ClientV9 {
	client.version = wireVersionV2
	return &ClientV9{Client: client}
}

func (c *ClientV9) Info() (InfoV9, error) {
	payload, err := c.call(KindInfo, nil)
	if err != nil {
		return InfoV9{}, err
	}
	info, err := decodeInfoV9(payload)
	if err != nil {
		return InfoV9{}, c.protocolFailure(err)
	}
	return info, nil
}

// InitChain compares four values on the other side, not three: version nine
// adds the genesis stamp.
func (c *ClientV9) InitChain(
	chainID Hash,
	initialHeight uint64,
	genesisTimestamp uint64,
	appState []byte,
) (Hash, error) {
	if len(appState) > MaximumAppStateSize {
		return Hash{}, errors.New("application state exceeds limit")
	}
	response, err := c.call(KindInitChain, initChainPayloadV9(
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
func (c *ClientV9) ProcessProposal(
	height uint64,
	timestamp uint64,
	transactions [][]byte,
) (Decision, error) {
	payload, err := blockPayloadV9(height, timestamp, transactions)
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
func (c *ClientV9) FinalizeBlock(
	height uint64,
	timestamp uint64,
	transactions [][]byte,
) (FinalizedBlockV9, error) {
	payload, err := blockPayloadV9(height, timestamp, transactions)
	if err != nil {
		return FinalizedBlockV9{}, err
	}
	response, err := c.call(KindFinalizeBlock, payload)
	if err != nil {
		return FinalizedBlockV9{}, err
	}
	block, err := decodeFinalizeV9(response, len(transactions))
	if err != nil {
		return FinalizedBlockV9{}, c.protocolFailure(err)
	}
	return block, nil
}

func (c *ClientV9) Commit() (CommittedHeadV9, error) {
	payload, err := c.call(KindCommit, nil)
	if err != nil {
		return CommittedHeadV9{}, err
	}
	head, err := decodeCommitV9(payload)
	if err != nil {
		return CommittedHeadV9{}, c.protocolFailure(err)
	}
	return head, nil
}
