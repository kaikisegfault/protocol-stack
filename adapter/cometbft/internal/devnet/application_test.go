package devnet

import (
	"strings"
	"testing"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

const (
	identityChainID = "000102030405060708090A0B0C0D0E0F" +
		"101112131415161718191A1B1C1D1E1F"
	identityAppHash = "FFFEFDFCFBFAF9F8F7F6F5F4F3F2F1F0" +
		"EFEEEDECEBEAE9E8E7E6E5E4E3E2E1E0"
	identityV8 = "chain_id=" + identityChainID + "\n" +
		"app_hash=" + identityAppHash + "\n"
	identityV9 = identityV8 + "genesis_timestamp=1790000000123\n"
)

func TestParseIdentityReadsEachVersionsKeys(t *testing.T) {
	for _, protocol := range []nodeconfig.ProtocolVersion{
		nodeconfig.ProtocolV1, nodeconfig.ProtocolV8,
	} {
		identity, err := parseIdentity([]byte(identityV8), protocol)
		if err != nil {
			t.Fatalf("version %d: %v", uint8(protocol), err)
		}
		if _, present := identity.GenesisTimestamp.Millis(); present {
			t.Fatalf("version %d identity carries a stamp", uint8(protocol))
		}
		if identity.ChainID[1] != 0x01 || identity.AppHash[0] != 0xFF {
			t.Fatalf("version %d identity mismatch", uint8(protocol))
		}
	}
	identity, err := parseIdentity([]byte(identityV9), nodeconfig.ProtocolV9)
	if err != nil {
		t.Fatalf("version nine: %v", err)
	}
	millis, present := identity.GenesisTimestamp.Millis()
	if !present || millis != 1_790_000_000_123 {
		t.Fatalf("version nine stamp = %d, %v", millis, present)
	}
	// Identity mode's line order is the application's business, not a rule.
	reordered := "genesis_timestamp=1790000000123\n" +
		"app_hash=" + identityAppHash + "\n" +
		"chain_id=" + identityChainID + "\n"
	again, err := parseIdentity([]byte(reordered), nodeconfig.ProtocolV9)
	if err != nil || again != identity {
		t.Fatalf("reordered version-nine identity: %v", err)
	}
}

// **The wrong binary for the version is refused before a home is written.**
// A version-eight application run as version nine omits the stamp, and a
// version-nine application run as version eight prints one it has no use for.
func TestParseIdentityRefusesTheOtherVersionsOutput(t *testing.T) {
	if _, err := parseIdentity(
		[]byte(identityV8), nodeconfig.ProtocolV9); err == nil ||
		!strings.Contains(err.Error(), "omitted") {
		t.Fatalf("a version-eight identity parsed as version nine: %v", err)
	}
	for _, protocol := range []nodeconfig.ProtocolVersion{
		nodeconfig.ProtocolV1, nodeconfig.ProtocolV8,
	} {
		if _, err := parseIdentity([]byte(identityV9), protocol); err == nil ||
			!strings.Contains(err.Error(), "invalid genesis identity") {
			t.Fatalf("a version-nine identity parsed as version %d: %v",
				uint8(protocol), err)
		}
	}
}

func TestParseIdentityRefusesMalformedOutput(t *testing.T) {
	stamp := func(value string) string {
		return identityV8 + "genesis_timestamp=" + value + "\n"
	}
	for name, output := range map[string]string{
		"empty":             "",
		"duplicate stamp":   identityV9 + "genesis_timestamp=1790000000123\n",
		"duplicate chain":   identityV9 + "chain_id=" + identityChainID + "\n",
		"unknown key":       identityV9 + "height=0\n",
		"line without =":    identityV9 + "genesis_timestamp\n",
		"empty stamp":       stamp(""),
		"leading zero":      stamp("01790000000123"),
		"signed stamp":      stamp("+1790000000123"),
		"stamp past range":  stamp("253402300800000"),
		"stamp past u64":    stamp("18446744073709551616"),
		"short chain ID":    "chain_id=00\napp_hash=" + identityAppHash + "\ngenesis_timestamp=0\n",
		"hash is not hex":   "chain_id=" + identityChainID + "\napp_hash=" + strings.Repeat("z", 64) + "\ngenesis_timestamp=0\n",
		"stamp not decimal": stamp("0x10"),
	} {
		if _, err := parseIdentity(
			[]byte(output), nodeconfig.ProtocolV9); err == nil {
			t.Fatalf("%s: malformed version-nine identity accepted", name)
		}
	}
}
