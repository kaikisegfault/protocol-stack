package main

import (
	"fmt"
	"os"
	"path/filepath"

	cmd "github.com/cometbft/cometbft/cmd/cometbft/commands"
	cfg "github.com/cometbft/cometbft/config"
	"github.com/cometbft/cometbft/libs/cli"
	nm "github.com/cometbft/cometbft/node"
	"github.com/spf13/cobra"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

var versionCommand = &cobra.Command{
	Use:   "version",
	Short: "Show the pinned CometBFT module version",
	Args:  cobra.NoArgs,
	Run: func(*cobra.Command, []string) {
		fmt.Println(nodeconfig.CometBFTVersion)
	},
}

func main() {
	root := cmd.RootCmd
	root.AddCommand(
		versionCommand,
		cmd.NewRunNodeCmd(nm.DefaultNewNode),
		cli.NewCompletionCmd(root, true),
	)
	command := cli.PrepareBaseCmd(
		root,
		"CMT",
		os.ExpandEnv(filepath.Join("$HOME", cfg.DefaultCometDir)),
	)
	if err := command.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "protocol-cometbft-node: %v\n", err)
		os.Exit(1)
	}
}
