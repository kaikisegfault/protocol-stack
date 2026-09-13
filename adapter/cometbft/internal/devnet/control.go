package devnet

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"net"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

// The supervisor's control channel: stop and start one replica while the rest
// of the network keeps committing.
//
// **A request is executed on the supervisor's main loop, never in the accept
// goroutine.** The readiness helpers a restart needs — `awaitUnix`, `awaitTCP`
// — read from the same `events` channel the watch loop reads, so a handler
// running concurrently would race the watch loop for a child exit and one of
// them would silently lose it. The accept goroutine therefore only parses a
// line and hands it over a channel; the loop runs the work inline, and there is
// exactly one reader of `events` at every moment.
//
// **The socket lives in the socket root**, which the supervisor already creates
// at mode 0700 and removes on exit, so the same directory permission that
// protects the four application sockets protects this one. Nothing else guards
// it: any process that can read that directory can stop a replica, which is the
// right bound for a loopback development network and not for anything else.

const (
	controlSocketName = "control.sock"
	// One request is at most this many octets including its newline. A control
	// verb and a single-digit index need eight; the rest is slack, and the
	// bound is what stops a broken or hostile client from making the
	// supervisor buffer without limit.
	controlRequestLimit = 64
	// How long a connection may take to deliver its line and read its answer.
	// A local client writes both in microseconds; this only stops a peer that
	// connects and then says nothing from holding the accept loop.
	controlConnectionTimeout = 10 * time.Second
	// How long a client waits for the supervisor to finish the work. Starting a
	// replica waits for an application socket and an ABCI port, each already
	// bounded at 20 seconds inside the loop.
	controlClientTimeout = 90 * time.Second
)

type controlAction int

const (
	controlStop controlAction = iota
	controlStart
)

func (action controlAction) String() string {
	if action == controlStart {
		return "start"
	}
	return "stop"
}

// controlRequest is one parsed command awaiting execution on the main loop.
type controlRequest struct {
	action controlAction
	index  int
	// reply is buffered, so the loop never blocks on a client that gave up.
	reply chan error
}

// controlSocketPath is the supervisor's control socket inside the socket root.
//
// It is two octets longer than the `node%d.sock` paths `nodeconfig` already
// bounds at the platform's 107-octet limit, so it is checked here rather than
// assumed: a truncated socket path fails as a confusing connection error much
// later, and a devnet root deep enough to overflow is a legitimate thing to
// refuse at startup.
func controlSocketPath(socketRoot string) (string, error) {
	path := filepath.Join(socketRoot, controlSocketName)
	if len(path) > maximumControlSocketPath {
		return "", fmt.Errorf(
			"control socket path exceeds %d bytes", maximumControlSocketPath)
	}
	return path, nil
}

const maximumControlSocketPath = 107

// parseControlLine reads one request line into an action and a replica index.
func parseControlLine(line string) (controlAction, int, error) {
	verb, rest, found := strings.Cut(strings.TrimSuffix(line, "\n"), " ")
	if !found {
		return 0, 0, errors.New("request must be a verb and a replica index")
	}
	var action controlAction
	switch verb {
	case "stop":
		action = controlStop
	case "start":
		action = controlStart
	default:
		return 0, 0, fmt.Errorf("unknown control verb %q", verb)
	}
	index, err := strconv.Atoi(rest)
	if err != nil {
		return 0, 0, fmt.Errorf("replica index %q is invalid", rest)
	}
	if index < 0 || index >= nodeconfig.DevnetNodeCount {
		return 0, 0, fmt.Errorf("replica index %d is out of range", index)
	}
	return action, index, nil
}

// formatControlResponse renders the single answer line a client reads.
func formatControlResponse(err error) string {
	if err == nil {
		return "ok\n"
	}
	// A newline inside an error would make one answer look like two, so the
	// message is flattened rather than trusted to be single-line.
	message := strings.ReplaceAll(err.Error(), "\n", "; ")
	return "error " + message + "\n"
}

// serveControl accepts control connections until the listener is closed.
func serveControl(
	ctx context.Context,
	listener net.Listener,
	requests chan<- controlRequest,
) {
	for {
		connection, err := listener.Accept()
		if err != nil {
			return
		}
		serveControlConnection(ctx, connection, requests)
	}
}

// serveControlConnection reads one request, executes it, and answers.
//
// Connections are served one at a time on purpose. Two concurrent stop requests
// for the same replica would be serialised by the main loop anyway, and doing it
// here means the accept loop has no state to share and nothing to synchronise.
func serveControlConnection(
	ctx context.Context,
	connection net.Conn,
	requests chan<- controlRequest,
) {
	defer connection.Close()
	_ = connection.SetDeadline(time.Now().Add(controlConnectionTimeout))
	reader := bufio.NewReader(io.LimitReader(connection, controlRequestLimit))
	line, err := reader.ReadString('\n')
	if err != nil {
		_, _ = io.WriteString(connection, formatControlResponse(
			errors.New("request was not a complete line")))
		return
	}
	action, index, err := parseControlLine(line)
	if err != nil {
		_, _ = io.WriteString(connection, formatControlResponse(err))
		return
	}
	request := controlRequest{
		action: action,
		index:  index,
		reply:  make(chan error, 1),
	}
	select {
	case requests <- request:
	case <-ctx.Done():
		_, _ = io.WriteString(connection, formatControlResponse(
			errors.New("supervisor is shutting down")))
		return
	}
	select {
	case result := <-request.reply:
		_, _ = io.WriteString(connection, formatControlResponse(result))
	case <-ctx.Done():
		_, _ = io.WriteString(connection, formatControlResponse(
			errors.New("supervisor is shutting down")))
	}
}

// SendControl asks a running supervisor to stop or start one replica.
func SendControl(
	ctx context.Context,
	devnet nodeconfig.Devnet,
	action string,
	index int,
) error {
	if action != "stop" && action != "start" {
		return fmt.Errorf("unknown control action %q", action)
	}
	if index < 0 || index >= nodeconfig.DevnetNodeCount {
		return fmt.Errorf("replica index %d is out of range", index)
	}
	path, err := controlSocketPath(devnet.SocketRoot)
	if err != nil {
		return err
	}
	dialer := net.Dialer{}
	connection, err := dialer.DialContext(ctx, "unix", path)
	if err != nil {
		return fmt.Errorf("connect to the devnet supervisor: %w", err)
	}
	defer connection.Close()
	if deadline, ok := ctx.Deadline(); ok {
		_ = connection.SetDeadline(deadline)
	} else {
		_ = connection.SetDeadline(time.Now().Add(controlClientTimeout))
	}
	if _, err := fmt.Fprintf(connection, "%s %d\n", action, index); err != nil {
		return fmt.Errorf("send %s %d: %w", action, index, err)
	}
	reader := bufio.NewReader(io.LimitReader(connection, 4096))
	answer, err := reader.ReadString('\n')
	if err != nil {
		return fmt.Errorf("read the supervisor's answer: %w", err)
	}
	answer = strings.TrimSuffix(answer, "\n")
	if answer == "ok" {
		return nil
	}
	if message, found := strings.CutPrefix(answer, "error "); found {
		return errors.New(message)
	}
	return fmt.Errorf("supervisor returned an unreadable answer %q", answer)
}
