package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

func main() {
	var home string
	var chainID string
	var appHash string
	var proxyApp string
	var rpcListen string
	var p2pListen string
	var genesisTimestamp string
	var protocolVersion uint
	flag.StringVar(&home, "home", "", "absolute CometBFT home")
	flag.StringVar(&chainID, "chain-id", "", "32-byte protocol chain ID in hex")
	flag.StringVar(&appHash, "app-hash", "", "32-byte height-zero state root in hex")
	flag.StringVar(&proxyApp, "proxy-app", "", "ABCI socket address")
	flag.StringVar(&rpcListen, "rpc-listen", "", "CometBFT RPC listen address")
	flag.StringVar(&p2pListen, "p2p-listen", "", "CometBFT P2P listen address")
	flag.StringVar(&genesisTimestamp, "genesis-timestamp", "",
		"canonical genesis timestamp in decimal milliseconds (version 9 only)")
	flag.UintVar(&protocolVersion, "protocol-version", 1,
		"protocol ledger version this home is initialized for (1, 8, or 9)")
	flag.Parse()
	if flag.NArg() != 0 {
		exitWithError(fmt.Errorf("unexpected positional arguments"))
	}
	identity, err := nodeconfig.ParseIdentity(chainID, appHash)
	if err != nil {
		exitWithError(err)
	}
	protocol, err := nodeconfig.ParseProtocolVersion(protocolVersion)
	if err != nil {
		exitWithError(err)
	}
	// An empty flag is the absence of a stamp, which is what versions one and
	// eight bind. Whether this version wants one is Ensure's to refuse, so the
	// rule lives in one place for this command and the devnet alike.
	if genesisTimestamp != "" {
		identity.GenesisTimestamp, err = nodeconfig.ParseGenesisTimestamp(
			genesisTimestamp)
		if err != nil {
			exitWithError(err)
		}
	}
	endpoints := nodeconfig.Endpoints{
		ProxyApp: proxyApp,
		RPC:      rpcListen,
		P2P:      p2pListen,
	}
	if err := nodeconfig.Ensure(home, identity, endpoints, protocol); err != nil {
		exitWithError(err)
	}
	fmt.Printf("protocol-cometbft-init: ready %s\n", identity.CometChainID())
}

func exitWithError(err error) {
	fmt.Fprintf(os.Stderr, "protocol-cometbft-init: %v\n", err)
	os.Exit(1)
}
