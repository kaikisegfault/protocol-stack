package localapp

// The version-eight client is version one's client and one different answer.
//
// It is version seven's `ClientV7` for the same reason version seven's was
// version one's: the connection, the request-identifier discipline, the
// terminal latch, the frame codec, and the request payloads carry no ledger
// version. Six of the seven operations are byte-for-byte version one's, and
// `FinalizeBlock` is the only one that reads a version-specific payload.
type ClientV8 struct {
	*Client
}

func DialV8(path string) (*ClientV8, error) {
	client, err := Dial(path)
	if err != nil {
		return nil, err
	}
	return &ClientV8{Client: client}, nil
}

func newClientV8(client *Client) *ClientV8 {
	return &ClientV8{Client: client}
}

// FinalizeBlock shadows version one's on purpose: the payload it decodes is
// version eight's, and version one's decoder would refuse it at the result
// count because the block identifier displaces every field after the root.
func (c *ClientV8) FinalizeBlock(
	height uint64,
	transactions [][]byte,
) (FinalizedBlockV8, error) {
	payload, err := blockPayload(height, transactions)
	if err != nil {
		return FinalizedBlockV8{}, err
	}
	response, err := c.call(KindFinalizeBlock, payload)
	if err != nil {
		return FinalizedBlockV8{}, err
	}
	block, err := decodeFinalizeV8(response, len(transactions))
	if err != nil {
		return FinalizedBlockV8{}, c.protocolFailure(err)
	}
	return block, nil
}
