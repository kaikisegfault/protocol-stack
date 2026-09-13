package devnet

import (
	"context"
	"errors"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

// replicaStopTimeout bounds one deliberate stop of one replica's three
// children. Each phase is signalled and reaped separately, so a replica may
// take up to three times this long to go away, which is the same budget the
// whole-network teardown gives each of its phases.
const replicaStopTimeout = 15 * time.Second

// Binaries are the three process implementations used by every replica.
type Binaries struct {
	Application string
	Bridge      string
	Node        string
}

// supervisor is the running network: what it was started from, and the three
// phases of children it owns.
//
// Every field is touched only on the main loop. The control channel does not
// share it; it hands parsed requests over a channel and the loop runs them.
type supervisor struct {
	devnet   nodeconfig.Devnet
	genesis  string
	binaries Binaries
	protocol nodeconfig.ProtocolVersion
	events   chan childExit
	// phases[phase][index] is replica `index`'s child in that phase, so a
	// replica's three processes are addressable without a second index.
	phases [][]*childProcess
}

// Run initializes and foreground-supervises the complete local network.
func Run(
	ctx context.Context,
	devnet nodeconfig.Devnet,
	genesis string,
	binaries Binaries,
	protocol nodeconfig.ProtocolVersion,
) (runError error) {
	if err := validateInputs(genesis, binaries); err != nil {
		return err
	}
	identity, err := InspectIdentity(ctx, binaries.Application, genesis)
	if err != nil {
		return err
	}
	// **The genesis and the bridges must be one choice.** The application state
	// this writes is what the application requires at InitChain, so a home
	// written for one ledger version and bridges started for the other is
	// refused there rather than at the first block. That is why the version
	// reaches both from here rather than being configured twice.
	if err := devnet.Ensure(identity, protocol); err != nil {
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

	network := &supervisor{
		devnet:   devnet,
		genesis:  genesis,
		binaries: binaries,
		protocol: protocol,
		events:   make(chan childExit, nodeconfig.DevnetNodeCount*3),
		phases:   make([][]*childProcess, 3),
	}
	for phase := range network.phases {
		network.phases[phase] = make(
			[]*childProcess, nodeconfig.DevnetNodeCount)
	}
	defer func() {
		if err := stopAll(network.phases); err != nil && runError == nil {
			runError = err
		}
	}()

	if err := network.startAll(ctx); err != nil {
		if ctx.Err() != nil {
			return nil
		}
		return err
	}
	health, err := awaitHealthy(ctx, network.events, devnet, AllReplicas())
	if err != nil {
		if ctx.Err() != nil {
			return nil
		}
		return err
	}
	fmt.Printf(
		"protocol-cometbft-devnet: ready validators=4 height=%d root=%X\n",
		health.Height,
		health.ApplicationRoot,
	)

	controlPath, err := controlSocketPath(devnet.SocketRoot)
	if err != nil {
		return err
	}
	listener, err := net.Listen("unix", controlPath)
	if err != nil {
		return fmt.Errorf("open the control socket: %w", err)
	}
	defer listener.Close()
	requests := make(chan controlRequest)
	go serveControl(ctx, listener, requests)

	return network.supervise(ctx, requests)
}

// supervise is the single reader of child exits and control requests.
func (network *supervisor) supervise(
	ctx context.Context,
	requests <-chan controlRequest,
) error {
	for {
		select {
		case <-ctx.Done():
			return nil
		case event := <-network.events:
			if ctx.Err() != nil {
				return nil
			}
			// A child the supervisor stopped on purpose still reports its exit
			// here, because the goroutine that waits on it does not know why it
			// ended. Skipping it is what lets a replica be down while the
			// network keeps running; every other exit is still fatal.
			if event.child.stopped {
				continue
			}
			return fmt.Errorf("%s exited unexpectedly: %v",
				event.child.name, event.err)
		case request := <-requests:
			request.reply <- network.execute(ctx, request)
		}
	}
}

// execute runs one control request inline on the main loop.
func (network *supervisor) execute(
	ctx context.Context,
	request controlRequest,
) error {
	if request.action == controlStop {
		return network.stopReplica(request.index)
	}
	return network.startReplica(ctx, request.index)
}

// startAll starts the three phases across every replica, in order.
//
// Each phase is started for all four replicas and then awaited for all four,
// rather than one replica at a time, because the bridges must be listening
// before any CometBFT node dials its own and the nodes must be able to find
// each other's P2P ports.
func (network *supervisor) startAll(ctx context.Context) error {
	for _, node := range network.devnet.Nodes {
		child, err := network.startApplication(node)
		if err != nil {
			return err
		}
		network.phases[0][node.Index] = child
	}
	for _, node := range network.devnet.Nodes {
		if err := network.awaitApplication(ctx, node); err != nil {
			return err
		}
	}
	for _, node := range network.devnet.Nodes {
		child, err := network.startBridge(node)
		if err != nil {
			return err
		}
		network.phases[1][node.Index] = child
	}
	for _, node := range network.devnet.Nodes {
		if err := network.awaitBridge(ctx, node); err != nil {
			return err
		}
	}
	for _, node := range network.devnet.Nodes {
		child, err := network.startNode(node)
		if err != nil {
			return err
		}
		network.phases[2][node.Index] = child
	}
	return nil
}

// stopReplica terminates one replica's three children, newest phase first.
//
// The whole replica goes, not just its consensus node: an application left
// holding its socket while its bridge and node are gone is a state no operator
// produces and no restart has to recover from, and the claim being tested is
// that a *machine* left the network.
func (network *supervisor) stopReplica(index int) error {
	if network.phases[0][index].stopped {
		return fmt.Errorf("replica %d is already stopped", index)
	}
	var firstError error
	for phase := len(network.phases) - 1; phase >= 0; phase-- {
		child := network.phases[phase][index]
		if err := stopPhase(
			[]*childProcess{child}, replicaStopTimeout,
		); err != nil && firstError == nil {
			firstError = fmt.Errorf("stop %s: %w", child.name, err)
		}
		// Marked after the stop rather than before it, because `stopPhase`
		// skips children already marked. Nothing reads the flag in between:
		// this runs on the main loop, which is the only reader.
		child.stopped = true
	}
	return firstError
}

// startReplica starts one replica's three children and waits for each.
//
// What it does **not** wait for is the network agreeing again. A replica that
// has just come back is behind, and catching up is the thing worth observing,
// so the caller asks for whole-network health afterwards and that observation
// is where the catch-up is required.
func (network *supervisor) startReplica(ctx context.Context, index int) error {
	if !network.phases[0][index].stopped {
		return fmt.Errorf("replica %d is already running", index)
	}
	node := network.devnet.Nodes[index]
	starters := []struct {
		start func(nodeconfig.DevnetNode) (*childProcess, error)
		await func(context.Context, nodeconfig.DevnetNode) error
	}{
		{network.startApplication, network.awaitApplication},
		{network.startBridge, network.awaitBridge},
		{network.startNode, nil},
	}
	for phase, starter := range starters {
		child, err := starter.start(node)
		if err != nil {
			return err
		}
		network.phases[phase][index] = child
		if starter.await == nil {
			continue
		}
		if err := starter.await(ctx, node); err != nil {
			return err
		}
	}
	return nil
}

func (network *supervisor) startApplication(
	node nodeconfig.DevnetNode,
) (*childProcess, error) {
	if err := os.MkdirAll(node.LogDirectory, 0o700); err != nil {
		return nil, fmt.Errorf(
			"create node %d log directory: %w", node.Index, err)
	}
	return startChild(
		network.events,
		fmt.Sprintf("node%d-application", node.Index),
		node.Root,
		filepath.Join(node.LogDirectory, "application.log"),
		network.binaries.Application,
		node.Database,
		network.genesis,
		node.ApplicationSocket,
	)
}

func (network *supervisor) startBridge(
	node nodeconfig.DevnetNode,
) (*childProcess, error) {
	return startChild(
		network.events,
		fmt.Sprintf("node%d-bridge", node.Index),
		node.Root,
		filepath.Join(node.LogDirectory, "bridge.log"),
		network.binaries.Bridge,
		"-application-socket",
		node.ApplicationSocket,
		"-abci-listen",
		node.Endpoints.ProxyApp,
		"-protocol-version",
		strconv.Itoa(int(network.protocol)),
	)
}

func (network *supervisor) startNode(
	node nodeconfig.DevnetNode,
) (*childProcess, error) {
	return startChild(
		network.events,
		fmt.Sprintf("node%d-cometbft", node.Index),
		node.Root,
		filepath.Join(node.LogDirectory, "cometbft.log"),
		network.binaries.Node,
		"start",
		"--home",
		node.Home,
	)
}

func (network *supervisor) awaitApplication(
	ctx context.Context,
	node nodeconfig.DevnetNode,
) error {
	if err := awaitUnix(
		ctx, network.events, node.ApplicationSocket,
	); err != nil {
		return fmt.Errorf(
			"node %d application readiness: %w", node.Index, err)
	}
	return nil
}

func (network *supervisor) awaitBridge(
	ctx context.Context,
	node nodeconfig.DevnetNode,
) error {
	if err := awaitTCP(ctx, network.events, node.ABCIPort); err != nil {
		return fmt.Errorf("node %d bridge readiness: %w", node.Index, err)
	}
	return nil
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
