package devnet

import (
	"context"
	"errors"
	"fmt"
	"net"
	"time"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

// Waiting for something to come up, and failing fast when a child dies first.
//
// **Every function here reads from the `events` channel**, which is why they
// may only be called from the supervisor's main loop: a second reader would
// take a child exit the watch loop needed, or the other way round, and the
// network would either hang or be torn down for the wrong reason.

const networkReadinessTimeout = 90 * time.Second

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
			if event.child.stopped {
				continue
			}
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
	replicas Replicas,
) (NetworkHealth, error) {
	timer := time.NewTimer(networkReadinessTimeout)
	defer timer.Stop()
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()
	var lastError error
	for {
		probeContext, cancel := context.WithTimeout(ctx, healthProbeTimeout)
		health, err := CheckHealth(probeContext, devnet, replicas)
		cancel()
		if err == nil {
			return health, nil
		}
		lastError = err
		select {
		case <-ctx.Done():
			return NetworkHealth{}, ctx.Err()
		case event := <-events:
			if event.child.stopped {
				continue
			}
			return NetworkHealth{}, fmt.Errorf(
				"%s exited: %v", event.child.name, event.err)
		case <-timer.C:
			return NetworkHealth{}, fmt.Errorf(
				"devnet readiness timeout: %v", lastError)
		case <-ticker.C:
		}
	}
}
