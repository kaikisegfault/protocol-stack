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
	config, err := nodeConfig(home, endpoints)
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
	if _, err := p2p.LoadOrGenNodeKey(config.NodeKeyFile()); err != nil {
		return fmt.Errorf("node key: %w", err)
	}
	if err := ensureGenesis(config.GenesisFile(), identity, validator); err != nil {
		return err
	}
	if err := writeConfig(config); err != nil {
		return err
	}
	return nil
}

func nodeConfig(home string, endpoints Endpoints) (*cfg.Config, error) {
	if endpoints.ProxyApp == "" || endpoints.RPC == "" || endpoints.P2P == "" {
		return nil, errors.New("proxy, RPC, and P2P addresses are required")
	}
	config := cfg.DefaultConfig().SetRoot(home)
	config.Version = CometBFTVersion
	config.Moniker = "protocol-stack-m1"
	config.ProxyApp = endpoints.ProxyApp
	config.ABCI = "socket"
	config.RPC.ListenAddress = endpoints.RPC
	config.RPC.GRPCListenAddress = ""
	config.RPC.Unsafe = false
	config.P2P.ListenAddress = endpoints.P2P
	config.P2P.PexReactor = false
	config.P2P.AddrBookStrict = false
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

func ensureGenesis(path string, identity Identity, validator *privval.FilePV) error {
	expected, err := expectedGenesis(identity, validator)
	if err != nil {
		return err
	}
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

func expectedGenesis(
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

func writeConfig(config *cfg.Config) (err error) {
	defer recoverError("write config", &err)
	path := filepath.Join(
		config.RootDir, cfg.DefaultConfigDir, cfg.DefaultConfigFileName)
	cfg.WriteConfigFile(path, config)
	return nil
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
