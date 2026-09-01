package main

import (
	"errors"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/cometbft/cometbft/abci/server"
	cmtlog "github.com/cometbft/cometbft/libs/log"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/bridge"
	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/localapp"
)

func run() error {
	abciAddress := flag.String(
		"abci-listen", "tcp://127.0.0.1:26658",
		"CometBFT ABCI socket listen address")
	applicationSocket := flag.String(
		"application-socket", "",
		"absolute path to the C++ application Unix socket")
	protocolVersion := flag.Uint(
		"protocol-version", 1,
		"protocol ledger version to bridge (1 or 7)")
	flag.Parse()
	if *applicationSocket == "" {
		return errors.New("-application-socket is required")
	}

	application, closeClient, err := dial(
		*protocolVersion, *applicationSocket)
	if err != nil {
		return err
	}
	defer closeClient()

	abciServer := server.NewSocketServer(*abciAddress, application)
	logger := cmtlog.NewTMLogger(cmtlog.NewSyncWriter(os.Stderr))
	abciServer.SetLogger(logger.With("module", "protocol-cometbft-bridge"))
	if err := abciServer.Start(); err != nil {
		return fmt.Errorf("start ABCI server: %w", err)
	}

	signals := make(chan os.Signal, 1)
	signal.Notify(signals, os.Interrupt, syscall.SIGTERM)
	<-signals
	signal.Stop(signals)
	if err := abciServer.Stop(); err != nil {
		return fmt.Errorf("stop ABCI server: %w", err)
	}
	return nil
}

// One binary, one supervisor, one flag. The ABCI server, the signal handling,
// and the connection are the same whichever ledger version is underneath; the
// two things that are not are which response decoder reads the finalized block
// and which codespace names its result codes.
func dial(
	protocolVersion uint,
	socketPath string,
) (*bridge.Application, func(), error) {
	switch protocolVersion {
	case 1:
		client, err := localapp.Dial(socketPath)
		if err != nil {
			return nil, nil, err
		}
		return bridge.New(bridge.LocalV1{Client: client}),
			func() { _ = client.Close() }, nil
	case 7:
		client, err := localapp.DialV7(socketPath)
		if err != nil {
			return nil, nil, err
		}
		return bridge.NewV7(bridge.LocalV7{ClientV7: client}),
			func() { _ = client.Close() }, nil
	}
	return nil, nil, fmt.Errorf(
		"unsupported protocol version %d", protocolVersion)
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "protocol-cometbft-bridge:", err)
		os.Exit(1)
	}
}
