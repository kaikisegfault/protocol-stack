package bridge

import (
	"bytes"
	"context"
	"encoding/binary"
	"strings"
	"testing"
	"time"

	abci "github.com/cometbft/cometbft/abci/types"
	cmtlog "github.com/cometbft/cometbft/libs/log"
	"github.com/cometbft/cometbft/version"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/localapp"
)

// Version ten's bridge is version nine's under `consensus-application-v3`
// (ADR 0110): the same frame, the same votes, and the same stamps. These cases
// are the ones the contract changes: the version string, the codespace, the
// top of the result range, and an Info that names another ledger.

func dialV10(t *testing.T, path string) (*Application, *bytes.Buffer) {
	client, err := localapp.DialV10(path)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = client.Close() })
	application := NewV10(LocalV10{ClientV10: client})
	var log bytes.Buffer
	application.SetLogger(cmtlog.NewTMLogger(cmtlog.NewSyncWriter(&log)))
	return application, &log
}

const genesisMillis10 = 1_768_435_200_000

func infoBodyV10(protocolVersion uint64, height uint64, root localapp.Hash) []byte {
	body := binary.BigEndian.AppendUint64(nil, protocolVersion)
	body = binary.BigEndian.AppendUint64(body, height)
	body = binary.BigEndian.AppendUint64(body, genesisMillis10)
	return append(body, root[:]...)
}

// Info reports `consensus-application-v3`'s version string and protocol
// version.
func TestVersionTenInfoReportsItsVersion(t *testing.T) {
	root := localapp.Hash{0: 10}
	_, path := startFrameServer(t, func(byte, []byte) (uint16, []byte) {
		return 0, infoBodyV10(10, 4, root)
	})
	application, _ := dialV10(t, path)
	info, err := application.Info(context.Background(), &abci.RequestInfo{
		AbciVersion: version.ABCIVersion,
	})
	if err != nil || info.Version != "10.0.0" || info.AppVersion != 10 ||
		info.Data != applicationData || info.LastBlockHeight != 4 ||
		!bytes.Equal(info.LastBlockAppHash, root[:]) {
		t.Fatalf("Info = %#v, %v", info, err)
	}
}

// **A version-nine application behind a version-ten bridge is refused at the
// engine's first call**, Info, because the frame cannot tell the two apart.
func TestVersionTenInfoRefusesAVersionNineApplication(t *testing.T) {
	_, path := startFrameServer(t, func(byte, []byte) (uint16, []byte) {
		return 0, infoBodyV10(9, 4, localapp.Hash{})
	})
	application, _ := dialV10(t, path)
	if _, err := application.Info(context.Background(), &abci.RequestInfo{
		AbciVersion: version.ABCIVersion,
	}); err == nil {
		t.Fatal("a version-ten bridge accepted a version-nine application")
	}
}

// InitChain sends the genesis stamp and version ten's application state.
func TestVersionTenInitChainSendsTheGenesisStamp(t *testing.T) {
	root := localapp.Hash{0: 10}
	server, path := startFrameServer(t, func(byte, []byte) (uint16, []byte) {
		return 0, root[:]
	})
	application, _ := dialV10(t, path)
	chain, chainID := testChain()
	appState := []byte(`"protocol-stack-v10"`)
	initialized, err := application.InitChain(context.Background(),
		&abci.RequestInitChain{
			ChainId: chainID, InitialHeight: 1,
			Time:          time.UnixMilli(genesisMillis10),
			AppStateBytes: appState,
		})
	if err != nil || !bytes.Equal(initialized.AppHash, root[:]) {
		t.Fatalf("InitChain = %#v, %v", initialized, err)
	}
	request := server.sent()[0]
	if request.kind != byte(localapp.KindInitChain) ||
		!bytes.Equal(request.payload[:32], chain[:]) ||
		stampOf(request.payload, 32) != 1 ||
		stampOf(request.payload, 40) != genesisMillis10 ||
		!bytes.Equal(request.payload[52:], appState) {
		t.Fatalf("InitChain payload = %x", request.payload)
	}
}

// A decision against is a vote against, named in the log.
func TestVersionTenProposalVotesAndExplains(t *testing.T) {
	_, path := startFrameServer(t, func(byte, []byte) (uint16, []byte) {
		return 0, []byte{byte(localapp.DecisionTimestampAheadOfTolerance)}
	})
	application, log := dialV10(t, path)
	rejected, err := application.ProcessProposal(context.Background(),
		&abci.RequestProcessProposal{
			Height: 1, Time: time.UnixMilli(genesisMillis10), Txs: [][]byte{{7}},
		})
	if err != nil || rejected.Status != abci.ResponseProcessProposal_REJECT {
		t.Fatalf("decision 4 = %#v, %v", rejected, err)
	}
	if !strings.Contains(log.String(), "TIMESTAMP_AHEAD_OF_TOLERANCE") {
		t.Fatalf("the rejection was not logged by name: %q", log.String())
	}
}

// **The top of the range, under version ten's codespace.** Result 49 is
// `APPROVAL_LIFETIME_EXCEEDED`, code 305, and its receipt says version ten.
func TestVersionTenFinalizeNamesItsCodespace(t *testing.T) {
	root, identifier := localapp.Hash{0: 1}, localapp.Hash{0: 2}
	receipt := make([]byte, 56)
	copy(receipt, []byte{'P', 'S', 'R', 'C', 0, 10})
	receipt[39] = 49
	body := append(append([]byte(nil), root[:]...), identifier[:]...)
	body = binary.BigEndian.AppendUint32(body, 1)
	body = binary.BigEndian.AppendUint32(body, 256+49)
	body = binary.BigEndian.AppendUint32(body, uint32(len(receipt)))
	body = append(body, receipt...)
	_, path := startFrameServer(t, func(byte, []byte) (uint16, []byte) {
		return 0, body
	})
	application, _ := dialV10(t, path)
	finalized, err := application.FinalizeBlock(context.Background(),
		&abci.RequestFinalizeBlock{
			Height: 1, Time: time.UnixMilli(genesisMillis10), Txs: [][]byte{{1}},
		})
	if err != nil || len(finalized.TxResults) != 1 ||
		finalized.TxResults[0].Code != 305 ||
		finalized.TxResults[0].Codespace != codespaceV10 ||
		!bytes.Equal(finalized.AppHash, root[:]) || len(finalized.Events) != 1 {
		t.Fatalf("FinalizeBlock = %#v, %v", finalized, err)
	}
}
