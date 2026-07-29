package nodeconfig

import (
	"bytes"
	"crypto/sha256"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	cfg "github.com/cometbft/cometbft/config"
	"github.com/cometbft/cometbft/p2p"
	"github.com/cometbft/cometbft/privval"
	"github.com/cometbft/cometbft/types"
)

const (
	// DevnetNodeCount is the fixed M1 validator count.
	DevnetNodeCount = 4
	// DefaultDevnetBaseP2PPort is node zero's default P2P port.
	DefaultDevnetBaseP2PPort = 27656
	devnetPortStride         = 10
	devnetLastPortOffset     = 32
	validatorPower           = 10
	maximumUnixSocketPath    = 107
)

// DevnetNode contains the fixed paths and endpoints for one local replica.
type DevnetNode struct {
	Index             int
	Root              string
	Home              string
	Database          string
	ApplicationSocket string
	LogDirectory      string
	Endpoints         Endpoints
	P2PPort           int
	RPCPort           int
	ABCIPort          int
}

// Devnet is the fixed four-validator M1 local topology.
type Devnet struct {
	Root        string
	SocketRoot  string
	BaseP2PPort int
	Nodes       [DevnetNodeCount]DevnetNode
}

// NewDevnet validates and derives a loopback-only four-validator topology.
func NewDevnet(root string, baseP2PPort int) (Devnet, error) {
	cleanRoot := filepath.Clean(root)
	digest := sha256.Sum256([]byte(cleanRoot))
	socketRoot := filepath.Join(
		os.TempDir(), fmt.Sprintf("protocol-stack-devnet-%x", digest[:8]))
	return NewDevnetWithSocketRoot(root, socketRoot, baseP2PPort)
}

// NewDevnetWithSocketRoot uses an explicit short-lived Unix-socket directory.
func NewDevnetWithSocketRoot(
	root string,
	socketRoot string,
	baseP2PPort int,
) (Devnet, error) {
	cleanRoot := filepath.Clean(root)
	if !filepath.IsAbs(root) || cleanRoot == string(filepath.Separator) {
		return Devnet{}, errors.New("devnet root must be an absolute non-root path")
	}
	cleanSocketRoot := filepath.Clean(socketRoot)
	if !filepath.IsAbs(socketRoot) ||
		cleanSocketRoot == string(filepath.Separator) {
		return Devnet{}, errors.New(
			"devnet socket root must be an absolute non-root path")
	}
	if baseP2PPort < 1 || baseP2PPort > 65535-devnetLastPortOffset {
		return Devnet{}, errors.New("devnet base P2P port is out of range")
	}
	result := Devnet{
		Root:        cleanRoot,
		SocketRoot:  cleanSocketRoot,
		BaseP2PPort: baseP2PPort,
	}
	for index := range DevnetNodeCount {
		nodeRoot := filepath.Join(cleanRoot, fmt.Sprintf("node%d", index))
		p2pPort := baseP2PPort + devnetPortStride*index
		applicationSocket := filepath.Join(
			cleanSocketRoot, fmt.Sprintf("node%d.sock", index))
		if len(applicationSocket) > maximumUnixSocketPath {
			return Devnet{}, fmt.Errorf(
				"node %d application socket path exceeds %d bytes",
				index, maximumUnixSocketPath)
		}
		result.Nodes[index] = DevnetNode{
			Index:             index,
			Root:              nodeRoot,
			Home:              filepath.Join(nodeRoot, "cometbft"),
			Database:          filepath.Join(nodeRoot, "ledger.db"),
			ApplicationSocket: applicationSocket,
			LogDirectory:      filepath.Join(nodeRoot, "logs"),
			Endpoints: Endpoints{
				ProxyApp: loopbackEndpoint(p2pPort + 2),
				RPC:      loopbackEndpoint(p2pPort + 1),
				P2P:      loopbackEndpoint(p2pPort),
			},
			P2PPort:  p2pPort,
			RPCPort:  p2pPort + 1,
			ABCIPort: p2pPort + 2,
		}
	}
	return result, nil
}

func loopbackEndpoint(port int) string {
	return fmt.Sprintf("tcp://127.0.0.1:%d", port)
}

// Ensure initializes or exact-validates every home in the topology.
func (devnet Devnet) Ensure(identity Identity) error {
	_, err := devnet.preflight()
	if err != nil {
		return err
	}
	configs := make([]*cfg.Config, DevnetNodeCount)
	validators := make([]*privval.FilePV, DevnetNodeCount)
	nodeKeys := make([]*p2p.NodeKey, DevnetNodeCount)

	for index, node := range devnet.Nodes {
		config, err := nodeConfig(node.Home, node.Endpoints, nodeOptions{
			moniker: fmt.Sprintf("protocol-stack-m1-validator-%d", index),
		})
		if err != nil {
			return fmt.Errorf("node %d: %w", index, err)
		}
		if err := ensureDirectories(node.Home); err != nil {
			return fmt.Errorf("node %d: %w", index, err)
		}
		validator, err := ensureValidator(config)
		if err != nil {
			return fmt.Errorf("node %d: %w", index, err)
		}
		nodeKey, err := ensureNodeKey(config)
		if err != nil {
			return fmt.Errorf("node %d: %w", index, err)
		}
		configs[index] = config
		validators[index] = validator
		nodeKeys[index] = nodeKey
	}
	if err := requireDistinctKeys(validators, nodeKeys); err != nil {
		return err
	}

	genesis, err := devnetGenesis(identity, validators)
	if err != nil {
		return err
	}
	for index, config := range configs {
		if err := ensureGenesis(config.GenesisFile(), genesis); err != nil {
			return fmt.Errorf("node %d: %w", index, err)
		}
		config.P2P.PersistentPeers = persistentPeers(
			index, devnet.Nodes, nodeKeys)
		config.P2P.AllowDuplicateIP = true
		if err := ensureConfig(config); err != nil {
			return fmt.Errorf("node %d: %w", index, err)
		}
	}
	return devnet.requireCommonGenesis()
}

func (devnet Devnet) preflight() (bool, error) {
	if err := os.MkdirAll(devnet.Root, 0o700); err != nil {
		return false, fmt.Errorf("create devnet root: %w", err)
	}
	if err := os.Chmod(devnet.Root, 0o700); err != nil {
		return false, fmt.Errorf("protect devnet root: %w", err)
	}
	existingCount := 0
	databaseCount := 0
	for _, node := range devnet.Nodes {
		config := cfg.DefaultConfig().SetRoot(node.Home)
		paths := []string{
			config.PrivValidatorKeyFile(),
			config.PrivValidatorStateFile(),
			config.NodeKeyFile(),
			config.GenesisFile(),
			filepath.Join(
				node.Home, cfg.DefaultConfigDir, cfg.DefaultConfigFileName),
		}
		present := 0
		for _, path := range paths {
			exists, err := regularFileExists(path)
			if err != nil {
				return false, fmt.Errorf("node %d: %w", node.Index, err)
			}
			if exists {
				present++
			}
		}
		if present != 0 && present != len(paths) {
			return false, fmt.Errorf("node %d home is incomplete", node.Index)
		}
		if present == len(paths) {
			existingCount++
		}
		databaseExists, err := regularFileExists(node.Database)
		if err != nil {
			return false, fmt.Errorf("node %d: %w", node.Index, err)
		}
		if databaseExists {
			databaseCount++
			if present == 0 {
				return false, fmt.Errorf(
					"node %d has a ledger without a validator home", node.Index)
			}
		}
	}
	if existingCount != 0 && existingCount != DevnetNodeCount {
		return false, errors.New("devnet contains a mixture of fresh and existing homes")
	}
	if databaseCount != 0 && databaseCount != DevnetNodeCount {
		return false, errors.New(
			"devnet contains an incomplete set of replica ledgers")
	}
	return existingCount == DevnetNodeCount, nil
}

func regularFileExists(path string) (bool, error) {
	info, err := os.Lstat(path)
	if errors.Is(err, os.ErrNotExist) {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("inspect %s: %w", path, err)
	}
	if !info.Mode().IsRegular() {
		return false, fmt.Errorf("%s is not a regular file", path)
	}
	return true, nil
}

func requireDistinctKeys(
	validators []*privval.FilePV,
	nodeKeys []*p2p.NodeKey,
) error {
	validatorIDs := make(map[string]struct{}, DevnetNodeCount)
	nodeIDs := make(map[p2p.ID]struct{}, DevnetNodeCount)
	for index := range DevnetNodeCount {
		publicKey, err := validators[index].GetPubKey()
		if err != nil {
			return fmt.Errorf("node %d validator public key: %w", index, err)
		}
		validatorID := string(publicKey.Bytes())
		if _, duplicate := validatorIDs[validatorID]; duplicate {
			return errors.New("devnet validator keys are not distinct")
		}
		validatorIDs[validatorID] = struct{}{}
		nodeID := nodeKeys[index].ID()
		if _, duplicate := nodeIDs[nodeID]; duplicate {
			return errors.New("devnet node keys are not distinct")
		}
		nodeIDs[nodeID] = struct{}{}
	}
	return nil
}

func devnetGenesis(
	identity Identity,
	validators []*privval.FilePV,
) (*types.GenesisDoc, error) {
	genesisValidators := make(
		[]types.GenesisValidator, DevnetNodeCount)
	for index, validator := range validators {
		publicKey, err := validator.GetPubKey()
		if err != nil {
			return nil, fmt.Errorf(
				"node %d validator public key: %w", index, err)
		}
		genesisValidators[index] = types.GenesisValidator{
			Address: publicKey.Address(),
			PubKey:  publicKey,
			Power:   validatorPower,
			Name:    fmt.Sprintf("protocol-stack-m1-validator-%d", index),
		}
	}
	document := &types.GenesisDoc{
		GenesisTime:     time.Unix(0, 0).UTC(),
		ChainID:         identity.CometChainID(),
		InitialHeight:   1,
		ConsensusParams: types.DefaultConsensusParams(),
		Validators:      genesisValidators,
		AppHash:         identity.AppHash[:],
		AppState:        []byte(appState),
	}
	if err := document.ValidateAndComplete(); err != nil {
		return nil, fmt.Errorf("devnet genesis: %w", err)
	}
	return document, nil
}

func persistentPeers(
	self int,
	nodes [DevnetNodeCount]DevnetNode,
	nodeKeys []*p2p.NodeKey,
) string {
	peers := make([]string, 0, DevnetNodeCount-1)
	for index := range DevnetNodeCount {
		if index == self {
			continue
		}
		address := fmt.Sprintf("127.0.0.1:%d", nodes[index].P2PPort)
		peers = append(
			peers, p2p.IDAddressString(nodeKeys[index].ID(), address))
	}
	return strings.Join(peers, ",")
}

func (devnet Devnet) requireCommonGenesis() error {
	var expected []byte
	for _, node := range devnet.Nodes {
		path := filepath.Join(
			node.Home, cfg.DefaultConfigDir, cfg.DefaultGenesisJSONName)
		actual, err := os.ReadFile(path)
		if err != nil {
			return fmt.Errorf("read node %d genesis: %w", node.Index, err)
		}
		if expected == nil {
			expected = actual
		} else if !bytes.Equal(actual, expected) {
			return errors.New("devnet genesis files differ")
		}
	}
	return nil
}
