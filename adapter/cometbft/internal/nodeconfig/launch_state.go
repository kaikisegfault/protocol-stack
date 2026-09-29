package nodeconfig

import (
	"fmt"

	cfg "github.com/cometbft/cometbft/config"
	"github.com/cometbft/cometbft/crypto/merkle"
	sm "github.com/cometbft/cometbft/state"
	"github.com/cometbft/cometbft/types"
)

// ensureLaunchState writes a seeded home's genesis state into the engine's
// state store, once, before the engine first starts (ADR 0097).
//
// **CometBFT v0.39.4 writes this state only on the InitChain path.** Its
// handshake sends InitChain when the application reports height zero, and saves
// the genesis state there. An application above zero takes the
// `storeBlockHeight == 0` branch instead. That branch compares app hashes and
// returns, and saves nothing. `NewNodeWithContext` then reloads the state from
// its store, finds it empty, and dereferences a nil validator set. So a seeded
// home is given the state the InitChain path would have saved: the genesis
// document's state, with the empty results hash the handshake records.
//
// **A store that already holds a state is left exactly as it is.** That is
// every restart, and a state written here is replaced by the engine's own at
// its first commit. The function never runs for a launch at the chain's
// genesis, which InitChain initialises as it always has.
func ensureLaunchState(config *cfg.Config, document *types.GenesisDoc) (err error) {
	database, err := cfg.DefaultDBProvider(
		&cfg.DBContext{ID: "state", Config: config})
	if err != nil {
		return fmt.Errorf("open state store: %w", err)
	}
	defer func() {
		if closeErr := database.Close(); closeErr != nil && err == nil {
			err = fmt.Errorf("close state store: %w", closeErr)
		}
	}()
	store := sm.NewStore(database, sm.StoreOptions{
		DiscardABCIResponses: config.Storage.DiscardABCIResponses,
	})
	existing, err := store.Load()
	if err != nil {
		return fmt.Errorf("load state: %w", err)
	}
	if !existing.IsEmpty() {
		return nil
	}
	state, err := sm.MakeGenesisState(document)
	if err != nil {
		return fmt.Errorf("genesis state: %w", err)
	}
	state.LastResultsHash = merkle.HashFromByteSlices(nil)
	if err := store.Save(state); err != nil {
		return fmt.Errorf("save genesis state: %w", err)
	}
	return nil
}
