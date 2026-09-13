package devnet

import (
	"errors"
	"fmt"
	"strconv"
	"strings"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

// Replicas names the validator replicas an observation covers.
//
// **The subset is the set of replicas expected to be running**, not merely the
// set that happens to be asked. That distinction is what lets `comparePeers`
// stay a real check while one replica is down: each member must see exactly the
// other members and no one else, so a replica that was supposed to be stopped
// and is still gossiping fails the observation rather than passing it.
//
// The head comparison narrows the same way. What does **not** narrow is the
// validator set: it comes from a genesis file that four homes share, and a
// process being down does not remove its validator from the set every running
// replica reports.
type Replicas []int

// AllReplicas is the whole four-validator network.
func AllReplicas() Replicas {
	all := make(Replicas, nodeconfig.DevnetNodeCount)
	for index := range nodeconfig.DevnetNodeCount {
		all[index] = index
	}
	return all
}

// ParseReplicas reads an ascending comma-separated replica list.
func ParseReplicas(text string) (Replicas, error) {
	fields := strings.Split(text, ",")
	result := make(Replicas, 0, len(fields))
	for _, field := range fields {
		index, err := strconv.Atoi(strings.TrimSpace(field))
		if err != nil {
			return nil, fmt.Errorf("replica list entry %q is invalid", field)
		}
		result = append(result, index)
	}
	if err := result.validate(); err != nil {
		return nil, err
	}
	return result, nil
}

// validate requires a non-empty, ascending, distinct, in-range list.
//
// Ascending rather than merely distinct because the order is what every error
// message and every comparison position is read against, so two spellings of
// the same subset would report the same divergence two different ways.
func (replicas Replicas) validate() error {
	if len(replicas) == 0 {
		return errors.New("replica list is empty")
	}
	for position, index := range replicas {
		if index < 0 || index >= nodeconfig.DevnetNodeCount {
			return fmt.Errorf("replica index %d is out of range", index)
		}
		if position > 0 && index <= replicas[position-1] {
			return errors.New("replica list is not ascending and distinct")
		}
	}
	return nil
}

func (replicas Replicas) contains(index int) bool {
	for _, member := range replicas {
		if member == index {
			return true
		}
	}
	return false
}

func (replicas Replicas) String() string {
	fields := make([]string, len(replicas))
	for position, index := range replicas {
		fields[position] = strconv.Itoa(index)
	}
	return strings.Join(fields, ",")
}
