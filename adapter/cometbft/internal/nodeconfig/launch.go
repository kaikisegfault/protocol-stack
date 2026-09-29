package nodeconfig

import (
	"errors"
	"fmt"
	"math"
	"strconv"
	"time"
)

// SeededHead is the head a seeded network's stores begin at, exactly as the
// application's `--seed` and `--inspect-seed` print it (ADR 0097).
type SeededHead struct {
	ChainID   Hash
	Height    uint64
	Timestamp uint64
	AppHash   Hash
}

// ParseSeededHead accepts the four printed values in their one spelling: the
// two hashes as 64 hexadecimal characters, the height and stamp as canonical
// decimal. It applies the rules a launch needs of a head, and no others:
//
//   - the height is at least one, because a height-zero head is a genesis and
//     the engine would call InitChain for it;
//   - the height plus one fits the engine's signed initial height;
//   - the stamp is inside calendar-v1's C1 range, which is also the last
//     instant CometBFT's genesis encoding can write.
//
// Whether the head is a state the chain can hold is the application's
// question, and its restore gates answered it before anything was printed.
func ParseSeededHead(chainID, height, timestamp, appHash string) (SeededHead, error) {
	chain, err := parseHash(chainID)
	if err != nil {
		return SeededHead{}, fmt.Errorf("seeded chain ID: %w", err)
	}
	root, err := parseHash(appHash)
	if err != nil {
		return SeededHead{}, fmt.Errorf("seeded application hash: %w", err)
	}
	seededHeight, err := parseCanonicalDecimal(height)
	if err != nil {
		return SeededHead{}, fmt.Errorf("seeded height: %w", err)
	}
	stamp, err := parseCanonicalDecimal(timestamp)
	if err != nil {
		return SeededHead{}, fmt.Errorf("seeded timestamp: %w", err)
	}
	head := SeededHead{
		ChainID: chain, Height: seededHeight, Timestamp: stamp, AppHash: root,
	}
	if err := head.validate(); err != nil {
		return SeededHead{}, err
	}
	return head, nil
}

func (head SeededHead) validate() error {
	if head.Height == 0 || head.Height >= math.MaxInt64 {
		return fmt.Errorf("seeded height %d cannot begin a network", head.Height)
	}
	if _, err := NewGenesisTimestamp(head.Timestamp); err != nil {
		return fmt.Errorf("seeded timestamp: %w", err)
	}
	return nil
}

func parseCanonicalDecimal(value string) (uint64, error) {
	parsed, err := strconv.ParseUint(value, 10, 64)
	if err != nil || strconv.FormatUint(parsed, 10) != value {
		return 0, errors.New("must be canonical decimal")
	}
	return parsed, nil
}

// Launch is where a network's engine begins proposing. **Its zero value is the
// chain's own genesis**, at initial height one, which is every launch before
// ADR 0097 and every launch without a snapshot since.
//
// A seeded launch carries one head, and the three genesis values it changes
// are all read from that head. There is no way to set one of them alone, so
// a genesis document naming a height, a root, and a time from different heads
// cannot be written.
type Launch struct {
	head   SeededHead
	seeded bool
}

// SeededLaunch begins a network at the block after `head`.
func SeededLaunch(head SeededHead) Launch {
	return Launch{head: head, seeded: true}
}

// Seed returns the seeded head and whether the launch has one.
func (l Launch) Seed() (SeededHead, bool) {
	return l.head, l.seeded
}

// genesisFields are the values a genesis document takes from the chain's
// identity, its protocol version, and where the network is launched.
type genesisFields struct {
	appState      string
	genesisTime   time.Time
	initialHeight int64
	appHash       []byte
}

// launchFields applies a seeded launch to the chain's own genesis fields.
//
// **Three values change together and nothing else does.** The initial height
// is the seeded height plus one, the application hash is the seeded root, and
// the genesis time is the seeded stamp. The engine stamps its first block with
// the genesis time, so the first block carries the seeded head's stamp, which
// is C2 with equality. The chain ID and the application state stay the chain's,
// because a seed is a later state of this chain and not another chain.
//
// A seed is refused for a version whose genesis binds no stamp, and for a head
// whose chain is not this identity's, before anything is written.
func launchFields(
	fields genesisFields,
	identity Identity,
	protocol ProtocolVersion,
	launch Launch,
) (genesisFields, error) {
	head, seeded := launch.Seed()
	if !seeded {
		return fields, nil
	}
	if !protocol.BindsGenesisTimestamp() {
		return genesisFields{}, fmt.Errorf(
			"protocol version %d cannot launch from a seeded head",
			uint8(protocol))
	}
	if err := head.validate(); err != nil {
		return genesisFields{}, err
	}
	if head.ChainID != identity.ChainID {
		return genesisFields{}, errors.New(
			"the seeded head belongs to another chain")
	}
	fields.initialHeight = int64(head.Height) + 1
	fields.appHash = append([]byte(nil), head.AppHash[:]...)
	fields.genesisTime = time.UnixMilli(int64(head.Timestamp)).UTC()
	return fields, nil
}
