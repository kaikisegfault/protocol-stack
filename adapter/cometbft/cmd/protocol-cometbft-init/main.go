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
	flag.StringVar(&home, "home", "", "absolute CometBFT home")
	flag.StringVar(&chainID, "chain-id", "", "32-byte protocol chain ID in hex")
	flag.StringVar(&appHash, "app-hash", "", "32-byte height-zero state root in hex")
	flag.StringVar(&proxyApp, "proxy-app", "", "ABCI socket address")
	flag.StringVar(&rpcListen, "rpc-listen", "", "CometBFT RPC listen address")
	flag.StringVar(&p2pListen, "p2p-listen", "", "CometBFT P2P listen address")
	flag.Parse()
	if flag.NArg() != 0 {
		exitWithError(fmt.Errorf("unexpected positional arguments"))
	}
	identity, err := nodeconfig.ParseIdentity(chainID, appHash)
	if err != nil {
		exitWithError(err)
	}
	endpoints := nodeconfig.Endpoints{
		ProxyApp: proxyApp,
		RPC:      rpcListen,
		P2P:      p2pListen,
	}
	if err := nodeconfig.Ensure(home, identity, endpoints); err != nil {
		exitWithError(err)
	}
	fmt.Printf("protocol-cometbft-init: ready %s\n", identity.CometChainID())
}

func exitWithError(err error) {
	fmt.Fprintf(os.Stderr, "protocol-cometbft-init: %v\n", err)
	os.Exit(1)
}
