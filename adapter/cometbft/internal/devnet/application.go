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
	output, err := runApplication(ctx, "inspect genesis identity",
		application, "--genesis-identity", genesis)
	if err != nil {
		return nodeconfig.Identity{}, err
	}
	return parseIdentity(output, protocol)
}

// runApplication runs one of the application's print-and-exit modes and
// returns what it printed. A refusal is reported with the application's own
// words, which name the rule that refused.
func runApplication(
	ctx context.Context,
	what string,
	application string,
	arguments ...string,
) ([]byte, error) {
	output, err := exec.CommandContext(ctx, application, arguments...).Output()
	if err != nil {
		var exitError *exec.ExitError
		if errors.As(err, &exitError) {
			return nil, fmt.Errorf("%s: %s",
				what, strings.TrimSpace(string(exitError.Stderr)))
		}
		return nil, fmt.Errorf("%s: %w", what, err)
	}
	return output, nil
}

// parseIdentity reads identity mode's output for one protocol version.
//
// **The key set is exact per version**: `chain_id` and `app_hash`, and for a
// version that binds a genesis timestamp, `genesis_timestamp` as well. So a
// version-one binary run as version nine is refused for the key it omits, and a
// version-nine binary run as version one for the key it adds, both before a
// home is written. The alternative, reading the stamp whenever it is
// printed, would let the second case through to InitChain.
func parseIdentity(
	output []byte,
	protocol nodeconfig.ProtocolVersion,
) (nodeconfig.Identity, error) {
	keys := []string{"chain_id", "app_hash"}
	if protocol.BindsGenesisTimestamp() {
		keys = append(keys, genesisTimestampField)
	}
	values, err := readFields(output, "genesis identity", keys...)
	if err != nil {
		return nodeconfig.Identity{}, err
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

// readFields reads `key=value` lines whose key set is exactly `keys`, each
// once and each nonempty, in any order. `what` names the output in errors.
func readFields(
	output []byte,
	what string,
	keys ...string,
) (map[string]string, error) {
	expected := make(map[string]bool, len(keys))
	for _, key := range keys {
		expected[key] = true
	}
	values := make(map[string]string, len(expected))
	scanner := bufio.NewScanner(bytes.NewReader(output))
	for scanner.Scan() {
		key, value, found := strings.Cut(scanner.Text(), "=")
		if !found || !expected[key] || value == "" {
			return nil, fmt.Errorf("application returned invalid %s", what)
		}
		if _, duplicate := values[key]; duplicate {
			return nil, fmt.Errorf(
				"application returned duplicate %s field", what)
		}
		values[key] = value
	}
	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("read %s: %w", what, err)
	}
	if len(values) != len(expected) {
		return nil, fmt.Errorf("application omitted %s field", what)
	}
	return values, nil
}
