package devnet

import (
	"errors"
	"fmt"
	"strconv"
	"strings"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/nodeconfig"
)

// ApplicationEnvironment holds the variables each replica's application process
// gets on top of the supervisor's own environment, one list per replica.
//
// **It exists so that one machine can differ from its peers.** The case that
// needed it is a clock. `consensus-application-v2` asks for one replica whose
// clock is beyond the tolerance, and the application reads the platform clock
// with no option to move it (ADR 0085). The devnet therefore moves that
// replica's clock from outside the process (ADR 0091), and what the supervisor
// has to supply is an environment the other replicas do not get.
//
// **It reaches the application and nothing else.** The bridge and the node are
// statically linked Go and read no variable a test would put here. Passing it
// to them would make "this replica's application differs" mean something
// wider. It survives `stop-replica` and `start-replica`, because a machine
// keeps its clock across a restart.
type ApplicationEnvironment [nodeconfig.DevnetNodeCount][]string

// Set adds one `index:NAME=VALUE` entry, which makes the type a repeatable
// command-line flag.
//
// The index is split off at the first colon and the name at the first equals
// sign after it, so the value may contain both. That matters because
// `ASAN_OPTIONS` values are colon-separated lists of `key=value` pairs.
func (environment *ApplicationEnvironment) Set(text string) error {
	indexText, variable, found := strings.Cut(text, ":")
	if !found {
		return fmt.Errorf(
			"application environment %q is not index:NAME=VALUE", text)
	}
	index, err := strconv.Atoi(indexText)
	if err != nil || strconv.Itoa(index) != indexText {
		return fmt.Errorf(
			"application environment index %q is not a decimal integer",
			indexText)
	}
	if index < 0 || index >= nodeconfig.DevnetNodeCount {
		return fmt.Errorf(
			"application environment index %d is out of range", index)
	}
	name, value, found := strings.Cut(variable, "=")
	if !found {
		return fmt.Errorf(
			"application environment %q has no value", text)
	}
	if !validVariableName(name) {
		return fmt.Errorf(
			"application environment name %q is invalid", name)
	}
	if strings.ContainsRune(value, 0) {
		return errors.New("application environment value contains NUL")
	}
	// **A repeated name is refused rather than resolved.** Go's `exec` would
	// silently keep the last one, and a run whose skew depends on which of two
	// flags came second is a run nobody can read from its command line.
	for _, existing := range environment[index] {
		if strings.HasPrefix(existing, name+"=") {
			return fmt.Errorf(
				"application environment for replica %d repeats %s",
				index, name)
		}
	}
	environment[index] = append(environment[index], name+"="+value)
	return nil
}

// String lists the entries for display, each in the form `Set` reads.
func (environment *ApplicationEnvironment) String() string {
	if environment == nil {
		return ""
	}
	var entries []string
	for index, variables := range environment {
		for _, variable := range variables {
			entries = append(entries, strconv.Itoa(index)+":"+variable)
		}
	}
	return strings.Join(entries, ",")
}

// validVariableName accepts the portable shell spelling: a letter or
// underscore, then letters, digits, and underscores.
func validVariableName(name string) bool {
	if name == "" {
		return false
	}
	for position, character := range name {
		switch {
		case character == '_',
			character >= 'A' && character <= 'Z',
			character >= 'a' && character <= 'z':
		case character >= '0' && character <= '9' && position > 0:
		default:
			return false
		}
	}
	return true
}
