package devnet

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"syscall"
	"time"
)

type childExit struct {
	child *childProcess
	err   error
}

type childProcess struct {
	name string
	cmd  *exec.Cmd
	log  *os.File
	done chan error
	// stopped marks a child the supervisor deliberately terminated, and it is
	// written and read only on the supervisor's main loop. Two things read it.
	// The watch loop skips this child's exit event instead of treating it as a
	// fatal crash; and `stopPhase` skips it at teardown, because its `done`
	// value has already been consumed and its log already closed, so reaping it
	// a second time would block until the shutdown timeout.
	stopped bool
}

// startChild starts one child in `directory`, logging to `logPath`.
//
// `environment` is added to the supervisor's own, and an entry wins over an
// inherited variable of the same name. An empty list leaves the child exactly
// as it always was: inheriting everything and adding nothing.
func startChild(
	events chan<- childExit,
	name string,
	directory string,
	logPath string,
	environment []string,
	command string,
	arguments ...string,
) (*childProcess, error) {
	if err := os.MkdirAll(directory, 0o700); err != nil {
		return nil, fmt.Errorf("create process directory: %w", err)
	}
	logFile, err := os.OpenFile(
		logPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err != nil {
		return nil, fmt.Errorf("open %s log: %w", name, err)
	}
	cmd := exec.Command(command, arguments...)
	cmd.Dir = directory
	if len(environment) != 0 {
		// `exec` keeps the last value of a repeated name, so appending is
		// what makes an entry here override an inherited one.
		cmd.Env = append(os.Environ(), environment...)
	}
	cmd.Stdout = logFile
	cmd.Stderr = logFile
	process := &childProcess{
		name: name,
		cmd:  cmd,
		log:  logFile,
		done: make(chan error, 1),
	}
	if err := cmd.Start(); err != nil {
		logFile.Close()
		return nil, fmt.Errorf("start %s: %w", name, err)
	}
	go func() {
		waitError := cmd.Wait()
		process.done <- waitError
		events <- childExit{child: process, err: waitError}
	}()
	return process, nil
}

func stopPhase(all []*childProcess, timeout time.Duration) error {
	children := make([]*childProcess, 0, len(all))
	for _, child := range all {
		// A nil entry is a phase slot the supervisor never filled, which is
		// what teardown finds when startup failed partway through.
		if child != nil && !child.stopped {
			children = append(children, child)
		}
	}
	if len(children) == 0 {
		return nil
	}
	for _, child := range children {
		if err := child.cmd.Process.Signal(syscall.SIGTERM); err != nil &&
			!errors.Is(err, os.ErrProcessDone) {
			_ = child.cmd.Process.Kill()
		}
	}
	deadline := time.Now().Add(timeout)
	var firstError error
	for index, child := range children {
		timer := time.NewTimer(time.Until(deadline))
		select {
		case <-child.done:
			if !timer.Stop() {
				select {
				case <-timer.C:
				default:
				}
			}
		case <-timer.C:
			for _, remaining := range children[index:] {
				_ = remaining.cmd.Process.Kill()
			}
			for _, remaining := range children[index:] {
				<-remaining.done
				if err := remaining.log.Close(); err != nil &&
					firstError == nil {
					firstError = fmt.Errorf(
						"close %s log: %w", remaining.name, err)
				}
			}
			if firstError == nil {
				firstError = fmt.Errorf(
					"process phase exceeded %s shutdown timeout", timeout)
			}
			return firstError
		}
		if err := child.log.Close(); err != nil && firstError == nil {
			firstError = fmt.Errorf("close %s log: %w", child.name, err)
		}
	}
	return firstError
}

func stopAll(phases [][]*childProcess) error {
	var firstError error
	for index := len(phases) - 1; index >= 0; index-- {
		if err := stopPhase(phases[index], 15*time.Second); err != nil &&
			firstError == nil {
			firstError = err
		}
	}
	return firstError
}
