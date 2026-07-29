package devnet

import (
	"bufio"
	"context"
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"net"
	"os/exec"
	"strings"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

const (
	applicationHeaderSize = 20
	applicationInfoKind   = 1
	maximumFrameSize      = 33_554_432
)

// ApplicationHead is one directly queried C++ durable head.
type ApplicationHead struct {
	Height uint64
	Root   nodeconfig.Hash
}

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

// ReadApplicationHead queries the adapter-neutral Info operation directly.
func ReadApplicationHead(
	ctx context.Context,
	socketPath string,
) (ApplicationHead, error) {
	connection, err := (&net.Dialer{}).DialContext(ctx, "unix", socketPath)
	if err != nil {
		return ApplicationHead{}, fmt.Errorf("connect application: %w", err)
	}
	defer connection.Close()
	if deadline, present := ctx.Deadline(); present {
		if err := connection.SetDeadline(deadline); err != nil {
			return ApplicationHead{}, fmt.Errorf(
				"set application deadline: %w", err)
		}
	}

	request := make([]byte, applicationHeaderSize)
	copy(request[:4], "PSAP")
	binary.BigEndian.PutUint16(request[4:6], 1)
	request[6] = 0
	request[7] = applicationInfoKind
	binary.BigEndian.PutUint64(request[8:16], 1)
	if _, err := connection.Write(request); err != nil {
		return ApplicationHead{}, fmt.Errorf("write application Info: %w", err)
	}

	header := make([]byte, applicationHeaderSize)
	if _, err := io.ReadFull(connection, header); err != nil {
		return ApplicationHead{}, fmt.Errorf("read application header: %w", err)
	}
	size := binary.BigEndian.Uint32(header[16:20])
	if string(header[:4]) != "PSAP" ||
		binary.BigEndian.Uint16(header[4:6]) != 1 ||
		header[6] != 1 ||
		header[7] != applicationInfoKind ||
		binary.BigEndian.Uint64(header[8:16]) != 1 ||
		size > maximumFrameSize {
		return ApplicationHead{}, errors.New(
			"application returned invalid Info header")
	}
	payload := make([]byte, size)
	if _, err := io.ReadFull(connection, payload); err != nil {
		return ApplicationHead{}, fmt.Errorf("read application Info: %w", err)
	}
	if len(payload) != 54 ||
		binary.BigEndian.Uint16(payload[:2]) != 0 ||
		binary.BigEndian.Uint32(payload[2:6]) != 0 ||
		binary.BigEndian.Uint64(payload[6:14]) != 1 {
		return ApplicationHead{}, errors.New(
			"application returned invalid Info payload")
	}
	var root nodeconfig.Hash
	copy(root[:], payload[22:54])
	return ApplicationHead{
		Height: binary.BigEndian.Uint64(payload[14:22]),
		Root:   root,
	}, nil
}
