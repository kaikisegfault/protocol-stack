package main

import (
	"context"
	"encoding/hex"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/devnet"
	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

type layoutFlags struct {
	root       string
	socketRoot string
	basePort   int
}

func main() {
	if err := run(os.Args[1:]); err != nil {
		fmt.Fprintf(os.Stderr, "protocol-cometbft-devnet: %v\n", err)
		os.Exit(1)
	}
}

func run(arguments []string) error {
	if len(arguments) == 0 {
		return errors.New("expected start, health, or transaction command")
	}
	switch arguments[0] {
	case "start":
		return runStart(arguments[1:])
	case "health":
		return runHealth(arguments[1:])
	case "transaction":
		return runTransaction(arguments[1:])
	default:
		return fmt.Errorf("unknown command %q", arguments[0])
	}
}

func addLayoutFlags(flags *flag.FlagSet) *layoutFlags {
	result := &layoutFlags{}
	flags.StringVar(
		&result.root, "root", "", "absolute persistent devnet root")
	flags.StringVar(
		&result.socketRoot,
		"socket-root",
		"",
		"optional absolute ephemeral Unix-socket root",
	)
	flags.IntVar(
		&result.basePort,
		"base-p2p-port",
		nodeconfig.DefaultDevnetBaseP2PPort,
		"node zero P2P port",
	)
	return result
}

func (values *layoutFlags) devnet() (nodeconfig.Devnet, error) {
	if values.socketRoot != "" {
		return nodeconfig.NewDevnetWithSocketRoot(
			values.root,
			values.socketRoot,
			values.basePort,
		)
	}
	return nodeconfig.NewDevnet(values.root, values.basePort)
}

func runStart(arguments []string) error {
	flags := flag.NewFlagSet("start", flag.ContinueOnError)
	layout := addLayoutFlags(flags)
	var genesis string
	var application string
	var bridge string
	var node string
	flags.StringVar(&genesis, "genesis", "", "absolute canonical genesis file")
	flags.StringVar(&application, "application", "", "application binary")
	flags.StringVar(&bridge, "bridge", "", "ABCI bridge binary")
	flags.StringVar(&node, "node", "", "CometBFT node binary")
	var protocolVersion uint
	flags.UintVar(&protocolVersion, "protocol-version", 1,
		"protocol ledger version every node runs (1 or 7)")
	if err := flags.Parse(arguments); err != nil {
		return err
	}
	if flags.NArg() != 0 {
		return errors.New("start received unexpected positional arguments")
	}
	protocol, err := nodeconfig.ParseProtocolVersion(protocolVersion)
	if err != nil {
		return err
	}
	topology, err := layout.devnet()
	if err != nil {
		return err
	}
	ctx, stop := signal.NotifyContext(
		context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	return devnet.Run(ctx, topology, genesis, devnet.Binaries{
		Application: application,
		Bridge:      bridge,
		Node:        node,
	}, protocol)
}

func runHealth(arguments []string) error {
	flags := flag.NewFlagSet("health", flag.ContinueOnError)
	layout := addLayoutFlags(flags)
	var timeout time.Duration
	flags.DurationVar(&timeout, "timeout", 30*time.Second, "health timeout")
	if err := flags.Parse(arguments); err != nil {
		return err
	}
	if flags.NArg() != 0 || timeout <= 0 {
		return errors.New("health arguments are invalid")
	}
	topology, err := layout.devnet()
	if err != nil {
		return err
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	health, err := devnet.WaitForHealth(ctx, topology)
	if err != nil {
		return err
	}
	fmt.Printf(
		"validators=4\nchain_id=%s\nheight=%d\napp_hash=%X\n"+
			"header_height=%d\nheader_app_hash=%X\n",
		health.ChainID,
		health.Height,
		health.ApplicationRoot,
		health.HeaderHeight,
		health.HeaderAppHash,
	)
	return nil
}

func runTransaction(arguments []string) error {
	flags := flag.NewFlagSet("transaction", flag.ContinueOnError)
	layout := addLayoutFlags(flags)
	var timeout time.Duration
	var transactionPath string
	var nodeIndex int
	flags.DurationVar(
		&timeout, "timeout", 45*time.Second, "commit and convergence timeout")
	flags.StringVar(
		&transactionPath, "tx-file", "", "exact raw transaction byte file")
	flags.IntVar(&nodeIndex, "node-index", 0, "RPC validator index")
	if err := flags.Parse(arguments); err != nil {
		return err
	}
	if flags.NArg() != 0 || timeout <= 0 || transactionPath == "" {
		return errors.New("transaction arguments are invalid")
	}
	topology, err := layout.devnet()
	if err != nil {
		return err
	}
	transactionInfo, err := os.Stat(transactionPath)
	if err != nil {
		return fmt.Errorf("inspect transaction: %w", err)
	}
	if !transactionInfo.Mode().IsRegular() ||
		transactionInfo.Size() < 1 ||
		transactionInfo.Size() > 1_048_576 {
		return errors.New(
			"transaction file must be regular and contain 1..1048576 bytes")
	}
	transaction, err := os.ReadFile(transactionPath)
	if err != nil {
		return fmt.Errorf("read transaction: %w", err)
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	result, err := devnet.Broadcast(
		ctx, topology, nodeIndex, transaction)
	if err != nil {
		if result.Height != 0 {
			fmt.Printf(
				"height=%d\ncheck_code=%d\nfinalize_code=%d\nreceipt=%s\n",
				result.Height,
				result.CheckCode,
				result.FinalizeCode,
				hex.EncodeToString(result.Receipt),
			)
		}
		return err
	}
	fmt.Printf(
		"height=%d\ncheck_code=%d\nfinalize_code=%d\nreceipt=%s\n"+
			"app_hash=%X\n",
		result.Height,
		result.CheckCode,
		result.FinalizeCode,
		hex.EncodeToString(result.Receipt),
		result.Health.ApplicationRoot,
	)
	return nil
}
