package devnet

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"os/exec"
	"strings"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

// InspectIdentity derives deployment identity through the C++ kernel.
func InspectIdentity(
	ctx context.Context,
	application string,
	genesis string,
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
	values := make(map[string]string, 2)
	scanner := bufio.NewScanner(strings.NewReader(string(output)))
	for scanner.Scan() {
		key, value, found := strings.Cut(scanner.Text(), "=")
		if !found || (key != "chain_id" && key != "app_hash") ||
			value == "" {
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
	if len(values) != 2 {
		return nodeconfig.Identity{}, errors.New(
			"application omitted genesis identity field")
	}
	identity, err := nodeconfig.ParseIdentity(
		values["chain_id"], values["app_hash"])
	if err != nil {
		return nodeconfig.Identity{}, fmt.Errorf(
			"application genesis identity: %w", err)
	}
	return identity, nil
}
