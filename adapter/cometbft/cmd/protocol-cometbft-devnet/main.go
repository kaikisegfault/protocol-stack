package main

import (
	"context"
	"encoding/hex"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"strings"
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
		return errors.New(
			"expected start, health, transaction, stop-replica, or " +
				"start-replica command")
	}
	switch arguments[0] {
	case "start":
		return runStart(arguments[1:])
	case "health":
		return runHealth(arguments[1:])
	case "transaction":
		return runTransaction(arguments[1:])
	case "stop-replica", "start-replica":
		return runControl(arguments[0], arguments[1:])
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
		"protocol ledger version every node runs (1 or 8)")
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

// addReplicaFlag names the replicas expected to be running.
//
// Every replica named must be up and converged, and every replica *not* named
// must be absent from the others' peer sets, so the default is the whole
// network and a narrower list is a claim about a deliberately stopped replica
// rather than a way to ignore one.
func addReplicaFlag(flags *flag.FlagSet) *string {
	value := flags.String(
		"nodes",
		devnet.AllReplicas().String(),
		"ascending comma-separated indices of the replicas expected to run",
	)
	return value
}

func runHealth(arguments []string) error {
	flags := flag.NewFlagSet("health", flag.ContinueOnError)
	layout := addLayoutFlags(flags)
	nodes := addReplicaFlag(flags)
	var timeout time.Duration
	flags.DurationVar(&timeout, "timeout", 30*time.Second, "health timeout")
	if err := flags.Parse(arguments); err != nil {
		return err
	}
	if flags.NArg() != 0 || timeout <= 0 {
		return errors.New("health arguments are invalid")
	}
	replicas, err := devnet.ParseReplicas(*nodes)
	if err != nil {
		return err
	}
	topology, err := layout.devnet()
	if err != nil {
		return err
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	health, err := devnet.WaitForHealth(ctx, topology, replicas)
	if err != nil {
		return err
	}
	fmt.Printf(
		"validators=%d\nchain_id=%s\nheight=%d\napp_hash=%X\n"+
			"header_height=%d\nheader_app_hash=%X\n",
		len(replicas),
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
	nodes := addReplicaFlag(flags)
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
	replicas, err := devnet.ParseReplicas(*nodes)
	if err != nil {
		return err
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
		ctx, topology, replicas, nodeIndex, transaction)
	if err != nil {
		if result.Height != 0 {
			// A refused transaction is still an operator error, so this command
			// keeps failing. What it now also prints, when the network reached a
			// height and converged, is the root it converged on -- because a
			// caller that provoked the refusal deliberately is asking exactly
			// that question, and a rejection that reports no root cannot answer
			// it.
			fmt.Printf(
				"height=%d\ncheck_code=%d\nfinalize_code=%d\nreceipt=%s\n",
				result.Height,
				result.CheckCode,
				result.FinalizeCode,
				hex.EncodeToString(result.Receipt),
			)
			if result.Health.Height != 0 {
				fmt.Printf("app_hash=%X\n", result.Health.ApplicationRoot)
			}
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

// runControl asks a running supervisor to stop or start one replica.
//
// The supervisor keeps running either way: this is how a replica leaves a
// network that goes on committing without it, and how it comes back. What the
// command does *not* wait for is the network agreeing again — a replica that
// has just started is behind, and `health` is where catching up is required.
func runControl(command string, arguments []string) error {
	action := strings.TrimSuffix(command, "-replica")
	flags := flag.NewFlagSet(command, flag.ContinueOnError)
	layout := addLayoutFlags(flags)
	var index int
	var timeout time.Duration
	flags.IntVar(&index, "index", -1, "replica index to stop or start")
	flags.DurationVar(
		&timeout, "timeout", 90*time.Second, "supervisor response timeout")
	if err := flags.Parse(arguments); err != nil {
		return err
	}
	if flags.NArg() != 0 || timeout <= 0 {
		return fmt.Errorf("%s arguments are invalid", command)
	}
	topology, err := layout.devnet()
	if err != nil {
		return err
	}
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()
	if err := devnet.SendControl(ctx, topology, action, index); err != nil {
		return err
	}
	fmt.Printf("%s=%d\n", action, index)
	return nil
}
