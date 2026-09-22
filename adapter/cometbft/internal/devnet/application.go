package devnet

import (
	"bufio"
	"bytes"
	"context"
	"errors"
	"fmt"
	"os/exec"
	"strings"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

const genesisTimestampField = "genesis_timestamp"

// InspectIdentity derives deployment identity through the C++ kernel.
func InspectIdentity(
	ctx context.Context,
	application string,
	genesis string,
	protocol nodeconfig.ProtocolVersion,
) (nodeconfig.Identity, error) {
	command := exec.CommandContext(
		ctx, application, "--genesis-identity", genesis)
	output, err := command.Output()
	if err != nil {
		var exitError *exec.ExitError
		if errors.As(err, &exitError) {
			return nodeconfig.Identity{}, fmt.Errorf(
				"inspect genesis identity: %s",
				strings.TrimSpace(string(exitError.Stderr)),
			)
		}
		return nodeconfig.Identity{}, fmt.Errorf(
			"inspect genesis identity: %w", err)
	}
	return parseIdentity(output, protocol)
}

// parseIdentity reads identity mode's output for one protocol version.
//
// **The key set is exact per version**: `chain_id` and `app_hash`, and for a
// version that binds a genesis timestamp, `genesis_timestamp` as well. So a
// version-eight binary run as version nine is refused for the key it omits,
// and a version-nine binary run as version eight for the key it adds, both
// before a home is written. The alternative, reading the stamp whenever it is
// printed, would let the second case through to InitChain.
func parseIdentity(
	output []byte,
	protocol nodeconfig.ProtocolVersion,
) (nodeconfig.Identity, error) {
	expected := map[string]bool{"chain_id": true, "app_hash": true}
	if protocol.BindsGenesisTimestamp() {
		expected[genesisTimestampField] = true
	}
	values := make(map[string]string, len(expected))
	scanner := bufio.NewScanner(bytes.NewReader(output))
	for scanner.Scan() {
		key, value, found := strings.Cut(scanner.Text(), "=")
		if !found || !expected[key] || value == "" {
			return nodeconfig.Identity{}, errors.New(
				"application returned invalid genesis identity")
		}
		if _, duplicate := values[key]; duplicate {
			return nodeconfig.Identity{}, errors.New(
				"application returned duplicate genesis identity field")
		}
		values[key] = value
	}
	if err := scanner.Err(); err != nil {
		return nodeconfig.Identity{}, fmt.Errorf(
			"read genesis identity: %w", err)
	}
	if len(values) != len(expected) {
		return nodeconfig.Identity{}, errors.New(
			"application omitted genesis identity field")
	}
	identity, err := nodeconfig.ParseIdentity(
		values["chain_id"], values["app_hash"])
	if err != nil {
		return nodeconfig.Identity{}, fmt.Errorf(
			"application genesis identity: %w", err)
	}
	if protocol.BindsGenesisTimestamp() {
		stamp, err := nodeconfig.ParseGenesisTimestamp(
			values[genesisTimestampField])
		if err != nil {
			return nodeconfig.Identity{}, fmt.Errorf(
				"application genesis identity: %w", err)
		}
		identity.GenesisTimestamp = stamp
	}
	return identity, nil
}
