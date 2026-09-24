package devnet

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestApplicationEnvironmentSet(t *testing.T) {
	var environment ApplicationEnvironment
	for _, entry := range []string{
		"3:LD_PRELOAD=/opt/libprotocol-clock-offset.so",
		// The value keeps every colon and equals sign after the name, which an
		// ASan option list needs.
		"3:ASAN_OPTIONS=detect_leaks=0:verify_asan_link_order=0",
		"0:EMPTY=",
		// The same name on another replica is a different machine's setting.
		"0:LD_PRELOAD=/other.so",
		"1:_private_2=x",
	} {
		if err := environment.Set(entry); err != nil {
			t.Fatalf("set %q: %v", entry, err)
		}
	}
	expected := ApplicationEnvironment{
		{"EMPTY=", "LD_PRELOAD=/other.so"},
		{"_private_2=x"},
		nil,
		{
			"LD_PRELOAD=/opt/libprotocol-clock-offset.so",
			"ASAN_OPTIONS=detect_leaks=0:verify_asan_link_order=0",
		},
	}
	for index := range expected {
		if strings.Join(environment[index], "\n") !=
			strings.Join(expected[index], "\n") {
			t.Fatalf("replica %d environment = %q, want %q",
				index, environment[index], expected[index])
		}
	}
	if rendered := environment.String(); rendered != "0:EMPTY=,"+
		"0:LD_PRELOAD=/other.so,1:_private_2=x,"+
		"3:LD_PRELOAD=/opt/libprotocol-clock-offset.so,"+
		"3:ASAN_OPTIONS=detect_leaks=0:verify_asan_link_order=0" {
		t.Fatalf("rendered environment = %q", rendered)
	}
}

func TestApplicationEnvironmentRefuses(t *testing.T) {
	for _, refused := range []string{
		"",
		"3",
		"3:",
		"3:NAME",
		"3:=value",
		"4:NAME=value",
		"-1:NAME=value",
		"+1:NAME=value",
		"01:NAME=value",
		" 1:NAME=value",
		"x:NAME=value",
		"3:1NAME=value",
		"3:NAME-2=value",
		"3:NA ME=value",
		"3:NAME=val\x00ue",
	} {
		var environment ApplicationEnvironment
		if err := environment.Set(refused); err == nil {
			t.Fatalf("accepted %q as %v", refused, environment)
		}
	}
	// A repeated name for one replica is refused rather than resolved, so no run
	// depends on which of two flags came second.
	var environment ApplicationEnvironment
	if err := environment.Set("2:SKEW=1"); err != nil {
		t.Fatal(err)
	}
	if err := environment.Set("2:SKEW=2"); err == nil {
		t.Fatal("accepted a repeated name for one replica")
	}
	if err := environment.Set("2:SKEWED=2"); err != nil {
		t.Fatalf("refused a name that merely shares a prefix: %v", err)
	}
}

// The child sees the supervisor's environment, the entries on top of it, and an
// entry winning over an inherited variable of the same name.
func TestStartChildAddsEnvironment(t *testing.T) {
	t.Setenv("PROTOCOL_STACK_INHERITED", "inherited")
	t.Setenv("PROTOCOL_STACK_OVERRIDDEN", "inherited")
	directory := t.TempDir()
	logPath := filepath.Join(directory, "child.log")
	events := make(chan childExit, 1)
	child, err := startChild(
		events,
		"environment-child",
		directory,
		logPath,
		[]string{
			"PROTOCOL_STACK_ADDED=added",
			"PROTOCOL_STACK_OVERRIDDEN=overridden",
		},
		"/bin/sh",
		"-c",
		`printf '%s %s %s' "$PROTOCOL_STACK_INHERITED" `+
			`"$PROTOCOL_STACK_ADDED" "$PROTOCOL_STACK_OVERRIDDEN"`,
	)
	if err != nil {
		t.Fatal(err)
	}
	select {
	case exit := <-events:
		if exit.err != nil {
			t.Fatalf("child failed: %v", exit.err)
		}
	case <-time.After(10 * time.Second):
		t.Fatal("child did not exit")
	}
	if err := child.log.Close(); err != nil {
		t.Fatal(err)
	}
	output, err := os.ReadFile(logPath)
	if err != nil {
		t.Fatal(err)
	}
	if string(output) != "inherited added overridden" {
		t.Fatalf("child saw %q", output)
	}
}
