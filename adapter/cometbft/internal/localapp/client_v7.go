package localapp

// The version-seven client is version one's client and one different answer.
//
// The connection, the request-identifier discipline, the terminal latch, the
// frame codec, and the request payloads carry no ledger-version meaning, so a
// second copy of them would be a second place for a framing rule to be wrong.
// Six of the seven operations are byte-for-byte version one's. `FinalizeBlock`
// is not, so `ClientV7` declares its own and nothing else.
type ClientV7 struct {
	*Client
}

func DialV7(path string) (*ClientV7, error) {
	client, err := Dial(path)
	if err != nil {
		return nil, err
	}
	return &ClientV7{Client: client}, nil
}

func newClientV7(client *Client) *ClientV7 {
	return &ClientV7{Client: client}
}

// FinalizeBlock shadows version one's on purpose: the payload it decodes is
// version seven's, and version one's decoder would refuse it at the result
// count because the block identifier displaces every field after the root.
func (c *ClientV7) FinalizeBlock(
	height uint64,
	transactions [][]byte,
) (FinalizedBlockV7, error) {
	payload, err := blockPayload(height, transactions)
	if err != nil {
		return FinalizedBlockV7{}, err
	}
	response, err := c.call(KindFinalizeBlock, payload)
	if err != nil {
		return FinalizedBlockV7{}, err
	}
	block, err := decodeFinalizeV7(response, len(transactions))
	if err != nil {
		return FinalizedBlockV7{}, c.protocolFailure(err)
	}
	return block, nil
}
