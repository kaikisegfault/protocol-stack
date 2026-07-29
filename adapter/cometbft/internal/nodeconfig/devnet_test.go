package nodeconfig

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	cfg "github.com/cometbft/cometbft/config"
	"github.com/cometbft/cometbft/p2p"
)

func TestNewDevnet(t *testing.T) {
	root := filepath.Join(t.TempDir(), "devnet")
	devnet, err := NewDevnet(root, DefaultDevnetBaseP2PPort)
	if err != nil {
		t.Fatalf("new devnet: %v", err)
	}
	if !filepath.IsAbs(devnet.SocketRoot) ||
		!strings.HasPrefix(
			filepath.Base(devnet.SocketRoot),
			"protocol-stack-devnet-",
		) {
		t.Fatalf("unexpected socket root %q", devnet.SocketRoot)
	}
	repeated, err := NewDevnet(root, DefaultDevnetBaseP2PPort)
	if err != nil || repeated.SocketRoot != devnet.SocketRoot {
		t.Fatalf("repeated socket root = %q, %v", repeated.SocketRoot, err)
	}
	for index, node := range devnet.Nodes {
		p2pPort := DefaultDevnetBaseP2PPort + index*devnetPortStride
		if node.Index != index ||
			node.Root != filepath.Join(root, fmt.Sprintf("node%d", index)) ||
			node.Home != filepath.Join(node.Root, "cometbft") ||
			node.Database != filepath.Join(node.Root, "ledger.db") ||
			node.ApplicationSocket != filepath.Join(
				devnet.SocketRoot, fmt.Sprintf("node%d.sock", index)) ||
			node.LogDirectory != filepath.Join(node.Root, "logs") ||
			node.P2PPort != p2pPort ||
			node.RPCPort != p2pPort+1 ||
			node.ABCIPort != p2pPort+2 ||
			node.Endpoints.P2P != loopbackEndpoint(p2pPort) ||
			node.Endpoints.RPC != loopbackEndpoint(p2pPort+1) ||
			node.Endpoints.ProxyApp != loopbackEndpoint(p2pPort+2) {
			t.Fatalf("node %d layout mismatch: %#v", index, node)
		}
	}

	overlongSocketRoot := filepath.Join(
		string(filepath.Separator),
		strings.Repeat("s", maximumUnixSocketPath),
	)
	if _, err := NewDevnetWithSocketRoot(
		root,
		overlongSocketRoot,
		DefaultDevnetBaseP2PPort,
	); err == nil || !strings.Contains(err.Error(), "exceeds") {
		t.Fatalf("overlong socket root error = %v", err)
	}
	for _, invalidSocketRoot := range []string{
		"relative",
		string(filepath.Separator),
	} {
		if _, err := NewDevnetWithSocketRoot(
			root,
			invalidSocketRoot,
			DefaultDevnetBaseP2PPort,
		); err == nil {
			t.Fatalf("accepted invalid socket root %q", invalidSocketRoot)
		}
	}

	for _, values := range []struct {
		root string
		port int
	}{
		{"relative", DefaultDevnetBaseP2PPort},
		{string(filepath.Separator), DefaultDevnetBaseP2PPort},
		{root, 0},
		{root, 65535 - devnetLastPortOffset + 1},
	} {
		if _, err := NewDevnet(values.root, values.port); err == nil {
			t.Fatalf("accepted invalid devnet root=%q port=%d",
				values.root, values.port)
		}
	}
}

func TestEnsureDevnetFreshAndRepeated(t *testing.T) {
	devnet := mustDevnet(t)
	identity := testIdentity()
	if err := devnet.Ensure(identity); err != nil {
		t.Fatalf("fresh ensure: %v", err)
	}

	nodeKeys := make([]*p2p.NodeKey, DevnetNodeCount)
	before := make(map[string][]byte)
	var commonGenesis []byte
	for index, node := range devnet.Nodes {
		config := cfg.DefaultConfig().SetRoot(node.Home)
		paths := []string{
			config.PrivValidatorKeyFile(),
			config.PrivValidatorStateFile(),
			config.NodeKeyFile(),
			config.GenesisFile(),
			filepath.Join(
				node.Home, cfg.DefaultConfigDir, cfg.DefaultConfigFileName),
		}
		for _, path := range paths {
			before[path] = readFile(t, path)
		}
		for _, path := range []string{
			devnet.Root,
			node.Root,
			node.Home,
			filepath.Join(node.Home, cfg.DefaultConfigDir),
			filepath.Join(node.Home, cfg.DefaultDataDir),
		} {
			requireMode(t, path, 0o700)
		}
		for _, path := range paths[:3] {
			requireMode(t, path, 0o600)
		}
		requireMode(t, paths[3], 0o644)
		requireMode(t, paths[4], 0o644)

		nodeKey, err := p2p.LoadNodeKey(config.NodeKeyFile())
		if err != nil {
			t.Fatalf("load node %d key: %v", index, err)
		}
		nodeKeys[index] = nodeKey
		genesisBytes := readFile(t, config.GenesisFile())
		if commonGenesis == nil {
			commonGenesis = genesisBytes
		} else if !bytes.Equal(genesisBytes, commonGenesis) {
			t.Fatal("generated genesis files differ")
		}
	}

	document, err := readGenesis(devnet.Nodes[0].Home +
		"/" + cfg.DefaultConfigDir + "/" + cfg.DefaultGenesisJSONName)
	if err != nil {
		t.Fatalf("read common genesis: %v", err)
	}
	if document.ChainID != identity.CometChainID() ||
		document.InitialHeight != 1 ||
		!bytes.Equal(document.AppHash, identity.AppHash[:]) ||
		!bytes.Equal(document.AppState, []byte(appState)) ||
		len(document.Validators) != DevnetNodeCount {
		t.Fatal("common genesis identity mismatch")
	}
	validatorKeys := make(map[string]struct{}, DevnetNodeCount)
	for index, validator := range document.Validators {
		config := cfg.DefaultConfig().SetRoot(devnet.Nodes[index].Home)
		fileValidator, err := loadValidator(
			config.PrivValidatorKeyFile(),
			config.PrivValidatorStateFile(),
		)
		if err != nil {
			t.Fatalf("load validator %d: %v", index, err)
		}
		publicKey, err := fileValidator.GetPubKey()
		if err != nil {
			t.Fatalf("validator %d public key: %v", index, err)
		}
		if !bytes.Equal(validator.PubKey.Bytes(), publicKey.Bytes()) ||
			validator.Power != validatorPower ||
			validator.Name != fmt.Sprintf(
				"protocol-stack-m1-validator-%d", index) {
			t.Fatalf("validator %d mismatch", index)
		}
		validatorKeys[string(publicKey.Bytes())] = struct{}{}
	}
	if len(validatorKeys) != DevnetNodeCount {
		t.Fatal("validator keys are not distinct")
	}

	for index, node := range devnet.Nodes {
		configPath := filepath.Join(
			node.Home, cfg.DefaultConfigDir, cfg.DefaultConfigFileName)
		configBytes := readFile(t, configPath)
		expectedPeers := persistentPeers(index, devnet.Nodes, nodeKeys)
		for _, expected := range []string{
			fmt.Sprintf(`moniker = "protocol-stack-m1-validator-%d"`, index),
			fmt.Sprintf(`proxy_app = "%s"`, node.Endpoints.ProxyApp),
			fmt.Sprintf(`laddr = "%s"`, node.Endpoints.RPC),
			fmt.Sprintf(`laddr = "%s"`, node.Endpoints.P2P),
			fmt.Sprintf(`persistent_peers = "%s"`, expectedPeers),
			"allow_duplicate_ip = true",
			"pex = false",
			`type = "flood"`,
			"create_empty_blocks = false",
		} {
			if !bytes.Contains(configBytes, []byte(expected)) {
				t.Fatalf("node %d config lacks %q", index, expected)
			}
		}
	}

	if err := devnet.Ensure(identity); err != nil {
		t.Fatalf("repeated ensure: %v", err)
	}
	for path, expected := range before {
		if actual := readFile(t, path); !bytes.Equal(actual, expected) {
			t.Fatalf("repeated ensure changed %s", path)
		}
	}
}

func TestEnsureDevnetRejectsChangedFiles(t *testing.T) {
	for _, test := range []struct {
		name   string
		change func(*testing.T, Devnet) string
		match  string
	}{
		{
			"configuration",
			func(t *testing.T, devnet Devnet) string {
				path := filepath.Join(
					devnet.Nodes[0].Home,
					cfg.DefaultConfigDir,
					cfg.DefaultConfigFileName,
				)
				original := readFile(t, path)
				changed := bytes.Replace(
					original,
					[]byte("allow_duplicate_ip = true"),
					[]byte("allow_duplicate_ip = false"),
					1,
				)
				if bytes.Equal(changed, original) {
					t.Fatal("configuration mutation did not apply")
				}
				writeTestFile(t, path, changed)
				return path
			},
			"configuration differs",
		},
		{
			"genesis",
			func(t *testing.T, devnet Devnet) string {
				path := filepath.Join(
					devnet.Nodes[0].Home,
					cfg.DefaultConfigDir,
					cfg.DefaultGenesisJSONName,
				)
				original := readFile(t, path)
				changed := bytes.Replace(
					original,
					[]byte(`"power": "10"`),
					[]byte(`"power": "11"`),
					1,
				)
				if bytes.Equal(changed, original) {
					t.Fatal("genesis mutation did not apply")
				}
				writeTestFile(t, path, changed)
				return path
			},
			"genesis differs",
		},
	} {
		t.Run(test.name, func(t *testing.T) {
			devnet := mustDevnet(t)
			identity := testIdentity()
			if err := devnet.Ensure(identity); err != nil {
				t.Fatalf("fresh ensure: %v", err)
			}
			path := test.change(t, devnet)
			changed := readFile(t, path)
			err := devnet.Ensure(identity)
			if err == nil || !strings.Contains(err.Error(), test.match) {
				t.Fatalf("changed-file error = %v", err)
			}
			if actual := readFile(t, path); !bytes.Equal(actual, changed) {
				t.Fatal("refusal replaced the changed file")
			}
		})
	}
}

func TestEnsureDevnetRejectsPartialOrDuplicateKeys(t *testing.T) {
	t.Run("partial", func(t *testing.T) {
		devnet := mustDevnet(t)
		path := filepath.Join(
			devnet.Nodes[0].Home,
			cfg.DefaultConfigDir,
			cfg.DefaultPrivValKeyName,
		)
		if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
			t.Fatal(err)
		}
		writeTestFile(t, path, []byte("{}"))
		err := devnet.Ensure(testIdentity())
		if err == nil || !strings.Contains(err.Error(), "incomplete") {
			t.Fatalf("partial-home error = %v", err)
		}
	})
	t.Run("ledger-without-home", func(t *testing.T) {
		devnet := mustDevnet(t)
		if err := os.MkdirAll(devnet.Nodes[0].Root, 0o700); err != nil {
			t.Fatal(err)
		}
		writeTestFile(t, devnet.Nodes[0].Database, []byte("not-a-ledger"))
		err := devnet.Ensure(testIdentity())
		if err == nil || !strings.Contains(
			err.Error(), "ledger without a validator home") {
			t.Fatalf("orphan-ledger error = %v", err)
		}
	})
	t.Run("incomplete-ledger-set", func(t *testing.T) {
		devnet := mustDevnet(t)
		identity := testIdentity()
		if err := devnet.Ensure(identity); err != nil {
			t.Fatalf("fresh ensure: %v", err)
		}
		writeTestFile(t, devnet.Nodes[0].Database, []byte("not-a-ledger"))
		err := devnet.Ensure(identity)
		if err == nil || !strings.Contains(
			err.Error(), "incomplete set of replica ledgers") {
			t.Fatalf("incomplete-ledger error = %v", err)
		}
	})

	for _, test := range []struct {
		name       string
		sourcePath func(*cfg.Config) string
		targetPath func(*cfg.Config) string
		match      string
	}{
		{
			"validator",
			func(config *cfg.Config) string {
				return config.PrivValidatorKeyFile()
			},
			func(config *cfg.Config) string {
				return config.PrivValidatorKeyFile()
			},
			"validator keys are not distinct",
		},
		{
			"node",
			func(config *cfg.Config) string {
				return config.NodeKeyFile()
			},
			func(config *cfg.Config) string {
				return config.NodeKeyFile()
			},
			"node keys are not distinct",
		},
	} {
		t.Run(test.name, func(t *testing.T) {
			devnet := mustDevnet(t)
			identity := testIdentity()
			if err := devnet.Ensure(identity); err != nil {
				t.Fatalf("fresh ensure: %v", err)
			}
			source := cfg.DefaultConfig().SetRoot(devnet.Nodes[0].Home)
			target := cfg.DefaultConfig().SetRoot(devnet.Nodes[1].Home)
			writeTestFile(
				t,
				test.targetPath(target),
				readFile(t, test.sourcePath(source)),
			)
			err := devnet.Ensure(identity)
			if err == nil || !strings.Contains(err.Error(), test.match) {
				t.Fatalf("duplicate-key error = %v", err)
			}
		})
	}
}

func mustDevnet(t *testing.T) Devnet {
	t.Helper()
	devnet, err := NewDevnet(
		filepath.Join(t.TempDir(), "devnet"),
		DefaultDevnetBaseP2PPort,
	)
	if err != nil {
		t.Fatal(err)
	}
	return devnet
}

func writeTestFile(t *testing.T, path string, value []byte) {
	t.Helper()
	if err := os.WriteFile(path, value, 0o600); err != nil {
		t.Fatalf("write %s: %v", path, err)
	}
}
