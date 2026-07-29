package devnet

import (
	"context"
	"errors"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"time"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

// Binaries are the three process implementations used by every replica.
type Binaries struct {
	Application string
	Bridge      string
	Node        string
}

// Run initializes and foreground-supervises the complete local network.
func Run(
	ctx context.Context,
	devnet nodeconfig.Devnet,
	genesis string,
	binaries Binaries,
) (runError error) {
	if err := validateInputs(genesis, binaries); err != nil {
		return err
	}
	identity, err := InspectIdentity(ctx, binaries.Application, genesis)
	if err != nil {
		return err
	}
	if err := devnet.Ensure(identity); err != nil {
		return fmt.Errorf("initialize devnet: %w", err)
	}
	if err := ensureSocketRoot(devnet.SocketRoot); err != nil {
		return fmt.Errorf("prepare socket root: %w", err)
	}
	defer func() {
		if err := os.Remove(devnet.SocketRoot); err != nil &&
			!errors.Is(err, os.ErrNotExist) &&
			runError == nil {
			runError = fmt.Errorf("remove socket root: %w", err)
		}
	}()

	events := make(chan childExit, nodeconfig.DevnetNodeCount*3)
	phases := make([][]*childProcess, 3)
	defer func() {
		if err := stopAll(phases); err != nil && runError == nil {
			runError = err
		}
	}()

	for _, node := range devnet.Nodes {
		if err := os.MkdirAll(node.LogDirectory, 0o700); err != nil {
			return fmt.Errorf("create node %d log directory: %w", node.Index, err)
		}
		child, err := startChild(
			events,
			fmt.Sprintf("node%d-application", node.Index),
			node.Root,
			filepath.Join(node.LogDirectory, "application.log"),
			binaries.Application,
			node.Database,
			genesis,
			node.ApplicationSocket,
		)
		if err != nil {
			return err
		}
		phases[0] = append(phases[0], child)
	}
	for _, node := range devnet.Nodes {
		if err := awaitUnix(ctx, events, node.ApplicationSocket); err != nil {
			return fmt.Errorf("node %d application readiness: %w", node.Index, err)
		}
	}

	for _, node := range devnet.Nodes {
		child, err := startChild(
			events,
			fmt.Sprintf("node%d-bridge", node.Index),
			node.Root,
			filepath.Join(node.LogDirectory, "bridge.log"),
			binaries.Bridge,
			"-application-socket",
			node.ApplicationSocket,
			"-abci-listen",
			node.Endpoints.ProxyApp,
		)
		if err != nil {
			return err
		}
		phases[1] = append(phases[1], child)
	}
	for _, node := range devnet.Nodes {
		if err := awaitTCP(ctx, events, node.ABCIPort); err != nil {
			return fmt.Errorf("node %d bridge readiness: %w", node.Index, err)
		}
	}

	for _, node := range devnet.Nodes {
		child, err := startChild(
			events,
			fmt.Sprintf("node%d-cometbft", node.Index),
			node.Root,
			filepath.Join(node.LogDirectory, "cometbft.log"),
			binaries.Node,
			"start",
			"--home",
			node.Home,
		)
		if err != nil {
			return err
		}
		phases[2] = append(phases[2], child)
	}
	health, err := awaitHealthy(ctx, events, devnet)
	if err != nil {
		return err
	}
	fmt.Printf(
		"protocol-cometbft-devnet: ready validators=4 height=%d root=%X\n",
		health.Height,
		health.ApplicationRoot,
	)

	select {
	case <-ctx.Done():
		return nil
	case event := <-events:
		if ctx.Err() != nil {
			return nil
		}
		return fmt.Errorf("%s exited unexpectedly: %v",
			event.child.name, event.err)
	}
}

func ensureSocketRoot(path string) error {
	info, err := os.Lstat(path)
	switch {
	case errors.Is(err, os.ErrNotExist):
		if err := os.Mkdir(path, 0o700); err != nil {
			return err
		}
	case err != nil:
		return err
	case info.Mode()&os.ModeSymlink != 0:
		return errors.New("path is a symbolic link")
	case !info.IsDir():
		return errors.New("path is not a directory")
	case info.Mode().Perm() != 0o700:
		if err := os.Chmod(path, 0o700); err != nil {
			return err
		}
	}
	return nil
}

func validateInputs(genesis string, binaries Binaries) error {
	if !filepath.IsAbs(genesis) {
		return errors.New("canonical genesis path must be absolute")
	}
	if err := requireRegularFile(genesis, false); err != nil {
		return fmt.Errorf("canonical genesis: %w", err)
	}
	for _, binary := range []struct {
		name string
		path string
	}{
		{"application", binaries.Application},
		{"bridge", binaries.Bridge},
		{"node", binaries.Node},
	} {
		if !filepath.IsAbs(binary.path) {
			return fmt.Errorf("%s binary path must be absolute", binary.name)
		}
		if err := requireRegularFile(binary.path, true); err != nil {
			return fmt.Errorf("%s binary: %w", binary.name, err)
		}
	}
	return nil
}

func requireRegularFile(path string, executable bool) error {
	info, err := os.Stat(path)
	if err != nil {
		return err
	}
	if !info.Mode().IsRegular() {
		return errors.New("path is not a regular file")
	}
	if executable && info.Mode().Perm()&0o111 == 0 {
		return errors.New("path is not executable")
	}
	return nil
}

func awaitUnix(
	ctx context.Context,
	events <-chan childExit,
	path string,
) error {
	return awaitEndpoint(ctx, events, func() error {
		connection, err := net.DialTimeout("unix", path, 200*time.Millisecond)
		if err != nil {
			return err
		}
		return connection.Close()
	})
}

func awaitTCP(
	ctx context.Context,
	events <-chan childExit,
	port int,
) error {
	return awaitEndpoint(ctx, events, func() error {
		connection, err := net.DialTimeout(
			"tcp",
			fmt.Sprintf("127.0.0.1:%d", port),
			200*time.Millisecond,
		)
		if err != nil {
			return err
		}
		return connection.Close()
	})
}

func awaitEndpoint(
	ctx context.Context,
	events <-chan childExit,
	probe func() error,
) error {
	timer := time.NewTimer(20 * time.Second)
	defer timer.Stop()
	ticker := time.NewTicker(20 * time.Millisecond)
	defer ticker.Stop()
	for {
		if err := probe(); err == nil {
			return nil
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case event := <-events:
			return fmt.Errorf("%s exited: %v", event.child.name, event.err)
		case <-timer.C:
			return errors.New("readiness timeout")
		case <-ticker.C:
		}
	}
}

func awaitHealthy(
	ctx context.Context,
	events <-chan childExit,
	devnet nodeconfig.Devnet,
) (NetworkHealth, error) {
	timer := time.NewTimer(45 * time.Second)
	defer timer.Stop()
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()
	var lastError error
	for {
		probeContext, cancel := context.WithTimeout(ctx, 3*time.Second)
		health, err := CheckHealth(probeContext, devnet)
		cancel()
		if err == nil {
			return health, nil
		}
		lastError = err
		select {
		case <-ctx.Done():
			return NetworkHealth{}, ctx.Err()
		case event := <-events:
			return NetworkHealth{}, fmt.Errorf(
				"%s exited: %v", event.child.name, event.err)
		case <-timer.C:
			return NetworkHealth{}, fmt.Errorf(
				"devnet readiness timeout: %v", lastError)
		case <-ticker.C:
		}
	}
}
