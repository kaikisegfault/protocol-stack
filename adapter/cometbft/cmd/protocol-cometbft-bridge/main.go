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
	flag.Parse()
	if *applicationSocket == "" {
		return errors.New("-application-socket is required")
	}

	client, err := localapp.Dial(*applicationSocket)
	if err != nil {
		return err
	}
	defer client.Close()

	abciServer := server.NewSocketServer(
		*abciAddress, bridge.New(client))
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

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "protocol-cometbft-bridge:", err)
		os.Exit(1)
	}
}
