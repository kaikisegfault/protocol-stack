package bridge

import (
	"bytes"
	"context"
	"encoding/binary"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	abci "github.com/cometbft/cometbft/abci/types"
	cmtlog "github.com/cometbft/cometbft/libs/log"
	"github.com/cometbft/cometbft/version"

	"github.com/kaikisegfault/protocol-stack/adapter/cometbft/internal/localapp"
)

func dialV9(t *testing.T, path string) (*Application, *bytes.Buffer) {
	client, err := localapp.DialV9(path)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = client.Close() })
	application := NewV9(LocalV9{ClientV9: client})
	var log bytes.Buffer
	application.SetLogger(cmtlog.NewTMLogger(cmtlog.NewSyncWriter(&log)))
	return application, &log
}

const (
	genesisMillis9 = 1_768_435_200_000
	// A block time 0.456789 ms past a whole millisecond, which must reach the
	// application truncated to 1,768,435,290,123.
	blockSeconds9 = 1_768_435_290
	blockNanos9   = 123_456_789
)

// InitChain sends the genesis stamp exactly, and refuses one it would have to
// round without sending anything.
func TestVersionNineInitChainSendsTheGenesisStamp(t *testing.T) {
	root := localapp.Hash{0: 9}
	server, path := startFrameServer(t, func(byte, []byte) (uint16, []byte) {
		return 0, root[:]
	})
	application, _ := dialV9(t, path)
	chain, chainID := testChain()
	ctx := context.Background()

	if _, err := application.InitChain(ctx, &abci.RequestInitChain{
		ChainId: chainID, InitialHeight: 1,
		Time: time.UnixMilli(genesisMillis9).Add(time.Microsecond),
	}); err == nil {
		t.Fatal("a genesis time with a sub-millisecond remainder was sent")
	}
	if len(server.sent()) != 0 {
		t.Fatal("a refused InitChain reached the application")
	}

	initialized, err := application.InitChain(ctx, &abci.RequestInitChain{
		ChainId: chainID, InitialHeight: 1,
		Time:          time.UnixMilli(genesisMillis9),
		AppStateBytes: []byte(`"protocol-stack-v9"`),
	})
	if err != nil || !bytes.Equal(initialized.AppHash, root[:]) {
		t.Fatalf("InitChain = %#v, %v", initialized, err)
	}
	request := server.sent()[0]
	if request.kind != byte(localapp.KindInitChain) ||
		!bytes.Equal(request.payload[:32], chain[:]) ||
		stampOf(request.payload, 32) != 1 ||
		stampOf(request.payload, 40) != genesisMillis9 {
		t.Fatalf("InitChain payload = %x", request.payload)
	}
}

// Decision 0 is the only vote for. Decision 5 votes against, and the log names
// it, which is how an operator finds a skewed clock.
func TestVersionNineProposalVotesAndExplains(t *testing.T) {
	// Read on the server's goroutine and changed on this one between calls, and
	// a socket is not a synchronisation edge the race detector can see.
	var decision atomic.Uint32
	decision.Store(uint32(localapp.DecisionTimestampBehindTolerance))
	server, path := startFrameServer(t, func(byte, []byte) (uint16, []byte) {
		return 0, []byte{byte(decision.Load())}
	})
	application, log := dialV9(t, path)
	ctx := context.Background()
	request := &abci.RequestProcessProposal{
		Height: 1, Time: time.Unix(blockSeconds9, blockNanos9), Txs: [][]byte{{7}},
	}

	rejected, err := application.ProcessProposal(ctx, request)
	if err != nil || rejected.Status != abci.ResponseProcessProposal_REJECT {
		t.Fatalf("decision 5 = %#v, %v", rejected, err)
	}
	if !strings.Contains(log.String(), "TIMESTAMP_BEHIND_TOLERANCE") {
		t.Fatalf("the rejection was not logged by name: %q", log.String())
	}
	sent := server.sent()[0]
	if stampOf(sent.payload, 0) != 1 ||
		stampOf(sent.payload, 8) != blockSeconds9*1000+blockNanos9/1_000_000 {
		t.Fatalf("ProcessProposal payload = %x", sent.payload)
	}

	decision.Store(uint32(localapp.DecisionAccepted))
	accepted, err := application.ProcessProposal(ctx, request)
	if err != nil || accepted.Status != abci.ResponseProcessProposal_ACCEPT {
		t.Fatalf("decision 0 = %#v, %v", accepted, err)
	}
}

// A stamp past the calendar reaches the application, and the fatal status it
// answers becomes an ABCI error.
func TestVersionNineFinalizePassesTheStampThrough(t *testing.T) {
	const pastTheCalendar = 253_402_300_799_999 + 1
	server, path := startFrameServer(t, func(byte, []byte) (uint16, []byte) {
		return 7, nil
	})
	application, _ := dialV9(t, path)
	_, err := application.FinalizeBlock(context.Background(),
		&abci.RequestFinalizeBlock{Height: 1, Time: time.UnixMilli(pastTheCalendar)})
	if err == nil || !strings.Contains(err.Error(), "status 7") {
		t.Fatalf("status 7 = %v", err)
	}
	if stampOf(server.sent()[0].payload, 8) != pastTheCalendar {
		t.Fatalf("FinalizeBlock payload = %x", server.sent()[0].payload)
	}
}

// Info reports consensus-application-v2's version string, 9.0.0. The bridge
// sent version one's until ADR 0110 found it.
func TestVersionNineInfoReportsItsVersion(t *testing.T) {
	root := localapp.Hash{0: 3}
	body := binary.BigEndian.AppendUint64(nil, 9)
	body = binary.BigEndian.AppendUint64(body, 4)
	body = binary.BigEndian.AppendUint64(body, genesisMillis9)
	body = append(body, root[:]...)
	_, path := startFrameServer(t, func(byte, []byte) (uint16, []byte) {
		return 0, body
	})
	application, _ := dialV9(t, path)
	info, err := application.Info(context.Background(), &abci.RequestInfo{
		AbciVersion: version.ABCIVersion,
	})
	if err != nil || info.Version != "9.0.0" || info.AppVersion != 9 ||
		info.Data != applicationData || info.LastBlockHeight != 4 ||
		!bytes.Equal(info.LastBlockAppHash, root[:]) {
		t.Fatalf("Info = %#v, %v", info, err)
	}
}

// Version nine's result codes are named in version nine's codespace, and the
// block identifier reaches the event.
func TestVersionNineFinalizeNamesItsCodespace(t *testing.T) {
	root, identifier := localapp.Hash{0: 1}, localapp.Hash{0: 2}
	receipt := make([]byte, 56)
	copy(receipt, []byte{'P', 'S', 'R', 'C', 0, 9})
	receipt[39] = 44
	body := append(append([]byte(nil), root[:]...), identifier[:]...)
	body = binary.BigEndian.AppendUint32(body, 1)
	body = binary.BigEndian.AppendUint32(body, 256+44)
	body = binary.BigEndian.AppendUint32(body, uint32(len(receipt)))
	body = append(body, receipt...)
	_, path := startFrameServer(t, func(byte, []byte) (uint16, []byte) {
		return 0, body
	})
	application, _ := dialV9(t, path)
	finalized, err := application.FinalizeBlock(context.Background(),
		&abci.RequestFinalizeBlock{
			Height: 1, Time: time.UnixMilli(genesisMillis9), Txs: [][]byte{{1}},
		})
	if err != nil || len(finalized.TxResults) != 1 ||
		finalized.TxResults[0].Codespace != codespaceV9 ||
		!bytes.Equal(finalized.AppHash, root[:]) || len(finalized.Events) != 1 {
		t.Fatalf("FinalizeBlock = %#v, %v", finalized, err)
	}
}
