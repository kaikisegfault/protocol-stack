package devnet

import (
	"testing"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

func TestAllReplicas(t *testing.T) {
	all := AllReplicas()
	if len(all) != nodeconfig.DevnetNodeCount || all.String() != "0,1,2,3" {
		t.Fatalf("all replicas = %v", all)
	}
	if err := all.validate(); err != nil {
		t.Fatalf("validate all: %v", err)
	}
	for index := range nodeconfig.DevnetNodeCount {
		if !all.contains(index) {
			t.Fatalf("all replicas omits %d", index)
		}
	}
	if all.contains(nodeconfig.DevnetNodeCount) || all.contains(-1) {
		t.Fatal("all replicas contains an out-of-range index")
	}
}

func TestParseReplicas(t *testing.T) {
	for _, accepted := range []struct {
		text     string
		expected string
	}{
		{"0,1,2,3", "0,1,2,3"},
		{"0,1,3", "0,1,3"},
		{"2", "2"},
		{" 0 , 1 ", "0,1"},
	} {
		replicas, err := ParseReplicas(accepted.text)
		if err != nil {
			t.Fatalf("parse %q: %v", accepted.text, err)
		}
		if replicas.String() != accepted.expected {
			t.Fatalf("parse %q = %q", accepted.text, replicas.String())
		}
	}
	// Descending and repeated spellings are refused rather than sorted: the
	// order is what every comparison position and every error message is read
	// against, so two spellings of one subset would report a divergence two
	// different ways.
	for _, refused := range []string{
		"", "4", "-1", "1,0", "1,1", "0,,1", "0;1", "0x1", "0,1,2,3,3",
	} {
		if replicas, err := ParseReplicas(refused); err == nil {
			t.Fatalf("accepted %q as %v", refused, replicas)
		}
	}
}
