package devnet

import (
	"errors"
	"fmt"
	"net"
	"path/filepath"
	"strings"
	"testing"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

func TestParseControlLine(t *testing.T) {
	for _, accepted := range []struct {
		line   string
		action controlAction
		index  int
	}{
		{"stop 0\n", controlStop, 0},
		{"start 3\n", controlStart, 3},
		{"stop 2", controlStop, 2},
	} {
		action, index, err := parseControlLine(accepted.line)
		if err != nil {
			t.Fatalf("parse %q: %v", accepted.line, err)
		}
		if action != accepted.action || index != accepted.index {
			t.Fatalf("parse %q = %v %d", accepted.line, action, index)
		}
	}
	for _, refused := range []string{
		"", "\n", "stop\n", "stop \n", "halt 0\n", "stop 4\n", "stop -1\n",
		"stop 0 0\n", " stop 0\n", "STOP 0\n", "stop x\n",
	} {
		if _, _, err := parseControlLine(refused); err == nil {
			t.Fatalf("accepted %q", refused)
		}
	}
}

func TestFormatControlResponse(t *testing.T) {
	if answer := formatControlResponse(nil); answer != "ok\n" {
		t.Fatalf("success answer = %q", answer)
	}
	// A multi-line error must stay one answer line, or a client reading one
	// line would take the first fragment for the whole result.
	answer := formatControlResponse(errors.New("stop failed:\nchild hung"))
	if strings.Count(answer, "\n") != 1 ||
		answer != "error stop failed:; child hung\n" {
		t.Fatalf("failure answer = %q", answer)
	}
}

func TestControlSocketPathIsBounded(t *testing.T) {
	path, err := controlSocketPath("/tmp/sockets")
	if err != nil || path != filepath.Join("/tmp/sockets", "control.sock") {
		t.Fatalf("control socket path = %q, %v", path, err)
	}
	deep := "/" + strings.Repeat("d", maximumControlSocketPath)
	if _, err := controlSocketPath(deep); err == nil {
		t.Fatal("accepted a control socket path over the platform bound")
	}
}

// TestControlRoundTrip drives the real wire in both directions.
//
// The supervisor's main loop is stood in for by a goroutine that answers
// whatever the accept loop hands it, which is exactly the contract: the accept
// loop parses and forwards, and the answer a client reads is the one the loop
// produced.
func TestControlRoundTrip(t *testing.T) {
	directory := t.TempDir()
	path, err := controlSocketPath(directory)
	if err != nil {
		t.Fatal(err)
	}
	listener, err := net.Listen("unix", path)
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	ctx := t.Context()
	requests := make(chan controlRequest)
	go serveControl(ctx, listener, requests)

	var seen []string
	done := make(chan struct{})
	go func() {
		defer close(done)
		for request := range requests {
			seen = append(
				seen, fmt.Sprintf("%s %d", request.action, request.index))
			if request.index == 3 {
				request.reply <- errors.New("replica 3 is already stopped")
				continue
			}
			request.reply <- nil
		}
	}()

	topology := nodeconfig.Devnet{SocketRoot: directory}
	if err := SendControl(ctx, topology, "stop", 2); err != nil {
		t.Fatalf("stop 2: %v", err)
	}
	if err := SendControl(ctx, topology, "start", 2); err != nil {
		t.Fatalf("start 2: %v", err)
	}
	err = SendControl(ctx, topology, "stop", 3)
	if err == nil || err.Error() != "replica 3 is already stopped" {
		t.Fatalf("stop 3 = %v", err)
	}
	// A client's own mistakes are refused before anything is dialled, so a
	// typo cannot reach a running supervisor as an unparsable line.
	for _, refused := range []struct {
		action string
		index  int
	}{{"halt", 0}, {"stop", -1}, {"stop", nodeconfig.DevnetNodeCount}} {
		if err := SendControl(
			ctx, topology, refused.action, refused.index,
		); err == nil {
			t.Fatalf("accepted %s %d", refused.action, refused.index)
		}
	}

	close(requests)
	<-done
	if strings.Join(seen, ",") != "stop 2,start 2,stop 3" {
		t.Fatalf("the loop saw %v", seen)
	}
}

// TestControlRejectsAnUnreadableRequest keeps the accept loop answering.
//
// A connection that sends no newline, or a verb the supervisor does not know,
// gets one error line and is closed — it must not reach the main loop and it
// must not leave the listener stuck.
func TestControlRejectsAnUnreadableRequest(t *testing.T) {
	directory := t.TempDir()
	path, err := controlSocketPath(directory)
	if err != nil {
		t.Fatal(err)
	}
	listener, err := net.Listen("unix", path)
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	requests := make(chan controlRequest)
	go serveControl(t.Context(), listener, requests)

	for _, sent := range []string{
		"halt 0\n",
		strings.Repeat("s", controlRequestLimit+8) + "\n",
	} {
		connection, err := net.Dial("unix", path)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := connection.Write([]byte(sent)); err != nil {
			t.Fatal(err)
		}
		answer := make([]byte, 256)
		read, err := connection.Read(answer)
		connection.Close()
		if err != nil {
			t.Fatalf("read the answer to %d octets: %v", len(sent), err)
		}
		if !strings.HasPrefix(string(answer[:read]), "error ") {
			t.Fatalf("answer to %d octets = %q", len(sent), answer[:read])
		}
	}

	// And the accept loop is still serving.
	go func() {
		request := <-requests
		request.reply <- nil
	}()
	if err := SendControl(
		t.Context(), nodeconfig.Devnet{SocketRoot: directory}, "stop", 1,
	); err != nil {
		t.Fatalf("stop 1 after two bad requests: %v", err)
	}
}
