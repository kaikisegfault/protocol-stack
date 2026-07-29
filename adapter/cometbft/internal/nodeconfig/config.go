package nodeconfig

import (
	"bytes"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"time"

	cfg "github.com/cometbft/cometbft/config"
	cmtjson "github.com/cometbft/cometbft/libs/json"
	"github.com/cometbft/cometbft/p2p"
	"github.com/cometbft/cometbft/privval"
	"github.com/cometbft/cometbft/types"
)

const (
	appState = `"protocol-stack-v1"`
	// CometBFTVersion is the exact accepted module release.
	CometBFTVersion = "0.39.4"
)

type Hash [32]byte

type Identity struct {
	ChainID Hash
	AppHash Hash
}

type Endpoints struct {
	ProxyApp string
	RPC      string
	P2P      string
}

type nodeOptions struct {
	moniker          string
	persistentPeers  string
	allowDuplicateIP bool
}

func ParseIdentity(chainID, appHash string) (Identity, error) {
	chain, err := parseHash(chainID)
	if err != nil {
		return Identity{}, fmt.Errorf("chain ID: %w", err)
	}
	root, err := parseHash(appHash)
	if err != nil {
		return Identity{}, fmt.Errorf("application hash: %w", err)
	}
	return Identity{ChainID: chain, AppHash: root}, nil
}

func parseHash(value string) (Hash, error) {
	var result Hash
	if len(value) != hex.EncodedLen(len(result)) {
		return result, errors.New("must contain exactly 64 hexadecimal characters")
	}
	decoded, err := hex.DecodeString(value)
	if err != nil {
		return result, errors.New("must be hexadecimal")
	}
	copy(result[:], decoded)
	return result, nil
}

func (i Identity) CometChainID() string {
	return "ps-" + base64.RawURLEncoding.EncodeToString(i.ChainID[:])
}

func Ensure(home string, identity Identity, endpoints Endpoints) error {
	if !filepath.IsAbs(home) || filepath.Clean(home) == string(filepath.Separator) {
		return errors.New("home must be an absolute non-root path")
	}
	config, err := nodeConfig(home, endpoints, nodeOptions{
		moniker: "protocol-stack-m1",
	})
	if err != nil {
		return err
	}
	if err := ensureDirectories(home); err != nil {
		return err
	}
	validator, err := ensureValidator(config)
	if err != nil {
		return err
	}
	if _, err := ensureNodeKey(config); err != nil {
		return err
	}
	expected, err := singleValidatorGenesis(identity, validator)
	if err != nil {
		return err
	}
	if err := ensureGenesis(config.GenesisFile(), expected); err != nil {
		return err
	}
	if err := ensureConfig(config); err != nil {
		return err
	}
	return nil
}

func nodeConfig(
	home string,
	endpoints Endpoints,
	options nodeOptions,
) (*cfg.Config, error) {
	if endpoints.ProxyApp == "" || endpoints.RPC == "" || endpoints.P2P == "" {
		return nil, errors.New("proxy, RPC, and P2P addresses are required")
	}
	if options.moniker == "" {
		return nil, errors.New("moniker is required")
	}
	config := cfg.DefaultConfig().SetRoot(home)
	config.Version = CometBFTVersion
	config.Moniker = options.moniker
	config.ProxyApp = endpoints.ProxyApp
	config.ABCI = "socket"
	config.RPC.ListenAddress = endpoints.RPC
	config.RPC.GRPCListenAddress = ""
	config.RPC.Unsafe = false
	config.P2P.ListenAddress = endpoints.P2P
	config.P2P.PexReactor = false
	config.P2P.AddrBookStrict = false
	config.P2P.PersistentPeers = options.persistentPeers
	config.P2P.AllowDuplicateIP = options.allowDuplicateIP
	config.P2P.LibP2PConfig.Enabled = false
	config.Mempool.Type = cfg.MempoolTypeFlood
	config.StateSync.Enable = false
	config.Consensus.TimeoutCommit = 3 * time.Second
	config.Consensus.SkipTimeoutCommit = false
	config.Consensus.CreateEmptyBlocks = false
	if err := config.ValidateBasic(); err != nil {
		return nil, fmt.Errorf("configuration: %w", err)
	}
	return config, nil
}

func ensureDirectories(home string) error {
	for _, path := range []string{
		home,
		filepath.Join(home, cfg.DefaultConfigDir),
		filepath.Join(home, cfg.DefaultDataDir),
	} {
		if err := os.MkdirAll(path, cfg.DefaultDirPerm); err != nil {
			return fmt.Errorf("create %s: %w", path, err)
		}
		if err := os.Chmod(path, cfg.DefaultDirPerm); err != nil {
			return fmt.Errorf("protect %s: %w", path, err)
		}
	}
	return nil
}

func ensureValidator(config *cfg.Config) (_ *privval.FilePV, err error) {
	keyPath := config.PrivValidatorKeyFile()
	statePath := config.PrivValidatorStateFile()
	keyExists := fileExists(keyPath)
	stateExists := fileExists(statePath)
	if keyExists != stateExists {
		return nil, errors.New("private validator key/state pair is incomplete")
	}
	if keyExists {
		return loadValidator(keyPath, statePath)
	}
	validator := privval.GenFilePV(keyPath, statePath)
	defer recoverError("save private validator", &err)
	validator.Save()
	return validator, nil
}

func ensureNodeKey(config *cfg.Config) (*p2p.NodeKey, error) {
	nodeKey, err := p2p.LoadOrGenNodeKey(config.NodeKeyFile())
	if err != nil {
		return nil, fmt.Errorf("node key: %w", err)
	}
	if nodeKey.PrivKey == nil || nodeKey.PubKey() == nil ||
		len(nodeKey.ID()) != p2p.IDByteLength*2 {
		return nil, errors.New("node key is inconsistent")
	}
	return nodeKey, nil
}

func loadValidator(keyPath, statePath string) (*privval.FilePV, error) {
	keyBytes, err := os.ReadFile(keyPath)
	if err != nil {
		return nil, fmt.Errorf("read private validator key: %w", err)
	}
	var key privval.FilePVKey
	if err := cmtjson.Unmarshal(keyBytes, &key); err != nil {
		return nil, fmt.Errorf("decode private validator key: %w", err)
	}
	if key.PrivKey == nil || key.PubKey == nil ||
		!bytes.Equal(key.PrivKey.PubKey().Bytes(), key.PubKey.Bytes()) ||
		!bytes.Equal(key.PubKey.Address(), key.Address) {
		return nil, errors.New("private validator key is inconsistent")
	}
	stateBytes, err := os.ReadFile(statePath)
	if err != nil {
		return nil, fmt.Errorf("read private validator state: %w", err)
	}
	var state privval.FilePVLastSignState
	if err := cmtjson.Unmarshal(stateBytes, &state); err != nil {
		return nil, fmt.Errorf("decode private validator state: %w", err)
	}
	if state.Height < 0 || state.Round < 0 || state.Step < 0 {
		return nil, errors.New("private validator state is invalid")
	}
	return &privval.FilePV{Key: key, LastSignState: state}, nil
}

func ensureGenesis(path string, expected *types.GenesisDoc) error {
	if fileExists(path) {
		actual, err := readGenesis(path)
		if err != nil {
			return err
		}
		if !reflect.DeepEqual(*actual, *expected) {
			return errors.New("existing CometBFT genesis differs from protocol identity")
		}
		return nil
	}
	if err := expected.SaveAs(path); err != nil {
		return fmt.Errorf("write genesis: %w", err)
	}
	return nil
}

func singleValidatorGenesis(
	identity Identity,
	validator *privval.FilePV,
) (*types.GenesisDoc, error) {
	publicKey, err := validator.GetPubKey()
	if err != nil {
		return nil, fmt.Errorf("validator public key: %w", err)
	}
	document := &types.GenesisDoc{
		GenesisTime:     time.Unix(0, 0).UTC(),
		ChainID:         identity.CometChainID(),
		InitialHeight:   1,
		ConsensusParams: types.DefaultConsensusParams(),
		Validators: []types.GenesisValidator{{
			Address: publicKey.Address(),
			PubKey:  publicKey,
			Power:   10,
		}},
		AppHash:  identity.AppHash[:],
		AppState: []byte(appState),
	}
	if err := document.ValidateAndComplete(); err != nil {
		return nil, fmt.Errorf("genesis: %w", err)
	}
	return document, nil
}

func readGenesis(path string) (*types.GenesisDoc, error) {
	encoded, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read genesis: %w", err)
	}
	var document types.GenesisDoc
	if err := cmtjson.Unmarshal(encoded, &document); err != nil {
		return nil, fmt.Errorf("decode genesis: %w", err)
	}
	if document.InitialHeight != 1 ||
		document.GenesisTime.IsZero() ||
		document.ConsensusParams == nil {
		return nil, errors.New("genesis omits required protocol values")
	}
	if err := document.ValidateAndComplete(); err != nil {
		return nil, fmt.Errorf("validate genesis: %w", err)
	}
	return &document, nil
}

func ensureConfig(config *cfg.Config) error {
	expected, err := configBytes(config)
	if err != nil {
		return err
	}
	path := filepath.Join(
		config.RootDir, cfg.DefaultConfigDir, cfg.DefaultConfigFileName)
	if fileExists(path) {
		actual, err := os.ReadFile(path)
		if err != nil {
			return fmt.Errorf("read configuration: %w", err)
		}
		if !bytes.Equal(actual, expected) {
			return errors.New("existing CometBFT configuration differs")
		}
		return nil
	}
	if err := os.WriteFile(path, expected, 0o644); err != nil {
		return fmt.Errorf("write configuration: %w", err)
	}
	return nil
}

func configBytes(config *cfg.Config) (_ []byte, err error) {
	path := filepath.Join(config.RootDir, ".protocol-stack-config.tmp")
	if _, statErr := os.Lstat(path); statErr == nil {
		return nil, errors.New("temporary configuration path is occupied")
	} else if !errors.Is(statErr, os.ErrNotExist) {
		return nil, fmt.Errorf("inspect temporary configuration path: %w", statErr)
	}
	defer func() {
		removeErr := os.Remove(path)
		if removeErr != nil && !errors.Is(removeErr, os.ErrNotExist) && err == nil {
			err = fmt.Errorf("remove temporary configuration: %w", removeErr)
		}
	}()
	defer recoverError("render configuration", &err)
	cfg.WriteConfigFile(path, config)
	encoded, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read rendered configuration: %w", err)
	}
	return encoded, nil
}

func recoverError(operation string, target *error) {
	if recovered := recover(); recovered != nil {
		*target = fmt.Errorf("%s: %v", operation, recovered)
	}
}

func fileExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.Mode().IsRegular()
}
