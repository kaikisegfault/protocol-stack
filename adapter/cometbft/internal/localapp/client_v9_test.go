package localapp

import (
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"net"
	"testing"
)

// A request as the server reads it, including the frame version, which the
// version-one helper does not report.
func readRequestV9(connection net.Conn) (Kind, uint64, []byte, error) {
	header := make([]byte, wireHeaderSize)
	if _, err := io.ReadFull(connection, header); err != nil {
		return 0, 0, nil, err
	}
	if string(header[:4]) != "PSAP" || header[6] != 0 ||
		binary.BigEndian.Uint16(header[4:6]) != wireVersionV2 {
		return 0, 0, nil, fmt.Errorf("not a version-two request: %x", header)
	}
	payload := make([]byte, int(binary.BigEndian.Uint32(header[16:20])))
	if _, err := io.ReadFull(connection, payload); err != nil {
		return 0, 0, nil, err
	}
	return Kind(header[7]), binary.BigEndian.Uint64(header[8:16]), payload, nil
}

func responseV9(kind Kind, requestID uint64, status uint16, body []byte) []byte {
	payload := make([]byte, 2, 6+len(body))
	binary.BigEndian.PutUint16(payload, status)
	payload = appendU32(payload, 0)
	payload = append(payload, body...)
	return append(versionTwoHeader(kind, requestID, uint32(len(payload))),
		payload...)
}

// Serve one request with `answer`, after checking it is the one expected. A
// request that is not closes the connection, so the client's call fails at once
// rather than waiting on a pipe for an answer that will never come.
func serveOneV9(
	t *testing.T,
	connection net.Conn,
	kind Kind,
	expected []byte,
	answer func(requestID uint64) []byte,
) chan struct{} {
	done := make(chan struct{})
	go func() {
		defer close(done)
		gotKind, requestID, payload, err := readRequestV9(connection)
		if err != nil {
			t.Error(err)
			_ = connection.Close()
			return
		}
		if gotKind != kind || string(payload) != string(expected) {
			t.Errorf("request = %d/%x, want %d/%x", gotKind, payload, kind, expected)
			_ = connection.Close()
			return
		}
		if _, err := connection.Write(answer(requestID)); err != nil {
			t.Error(err)
		}
	}()
	return done
}

const januaryMillis = 1_768_435_290_000

// The block request's octets written out by hand — height, then stamp, then the
// list — rather than by the encoder under test, so a swapped field fails here.
func handBlockPayload(height, stamp uint64, transactions ...[]byte) []byte {
	payload := make([]byte, 16, 20)
	binary.BigEndian.PutUint64(payload[0:8], height)
	binary.BigEndian.PutUint64(payload[8:16], stamp)
	payload = binary.BigEndian.AppendUint32(payload, uint32(len(transactions)))
	for _, transaction := range transactions {
		payload = binary.BigEndian.AppendUint32(payload, uint32(len(transaction)))
		payload = append(payload, transaction...)
	}
	return payload
}

// The client writes version-two frames with the stamp after the height, and
// reads the block identifier and version-nine receipts back.
func TestVersionNineClientFinalizesWithTheStamp(t *testing.T) {
	clientConnection, serverConnection := net.Pipe()
	defer serverConnection.Close()
	client := newClientV9(newClient(clientConnection))
	defer client.Close()

	transactions := [][]byte{{1, 2, 3}, {4}}
	expected := handBlockPayload(1, januaryMillis, transactions...)
	root, blockID := Hash{0: 1}, Hash{0: 2}
	body := append(append(append([]byte(nil), root[:]...), blockID[:]...),
		appendU32(nil, 2)...)
	body = appendBlob(appendU32(body, 0), receiptV9(0))
	body = appendU32(appendU32(body, 2), 0)
	done := serveOneV9(t, serverConnection, KindFinalizeBlock, expected,
		func(id uint64) []byte { return responseV9(KindFinalizeBlock, id, 0, body) })

	block, err := client.FinalizeBlock(1, januaryMillis, transactions)
	<-done
	if err != nil || block.StateRoot != root || block.BlockID != blockID ||
		len(block.TransactionResults) != 2 {
		t.Fatalf("finalized = %#v, %v", block, err)
	}
}

// A nonzero decision is an answer, not an error, and the connection lives on.
func TestVersionNineProposalAnswersADecision(t *testing.T) {
	clientConnection, serverConnection := net.Pipe()
	defer serverConnection.Close()
	client := newClientV9(newClient(clientConnection))
	defer client.Close()

	expected := handBlockPayload(1, januaryMillis)
	done := serveOneV9(t, serverConnection, KindProcessProposal, expected,
		func(id uint64) []byte {
			return responseV9(KindProcessProposal, id, 0,
				[]byte{byte(DecisionTimestampBehindTolerance)})
		})
	decision, err := client.ProcessProposal(1, januaryMillis, nil)
	<-done
	if err != nil || decision != DecisionTimestampBehindTolerance {
		t.Fatalf("decision = %d, %v", decision, err)
	}

	head := appendU64(appendU64(nil, 1), januaryMillis)
	head = append(head, root9[:]...)
	done = serveOneV9(t, serverConnection, KindCommit, nil,
		func(id uint64) []byte { return responseV9(KindCommit, id, 0, head) })
	committed, err := client.Commit()
	<-done
	if err != nil || committed != (CommittedHeadV9{1, januaryMillis, root9}) {
		t.Fatalf("commit = %#v, %v", committed, err)
	}
}

var root9 = Hash{0: 9, 31: 9}

// Status 8 on a finalize is the application's answer and is returned as one.
// Status 7 on a proposal is not an answer the contract permits, so it ends the
// connection as a protocol failure and every later call fails with it.
func TestVersionNineTimestampStatuses(t *testing.T) {
	clientConnection, serverConnection := net.Pipe()
	defer serverConnection.Close()
	client := newClientV9(newClient(clientConnection))
	defer client.Close()

	expected := handBlockPayload(2, januaryMillis-1)
	done := serveOneV9(t, serverConnection, KindFinalizeBlock, expected,
		func(id uint64) []byte {
			return responseV9(KindFinalizeBlock, id,
				statusDecidedBlockFailedMonotonicity, nil)
		})
	_, err := client.FinalizeBlock(2, januaryMillis-1, nil)
	<-done
	var applicationError *ApplicationError
	if !errors.As(err, &applicationError) ||
		applicationError.Status != statusDecidedBlockFailedMonotonicity {
		t.Fatalf("finalize error = %#v", err)
	}

	expected = handBlockPayload(2, januaryMillis)
	done = serveOneV9(t, serverConnection, KindProcessProposal, expected,
		func(id uint64) []byte {
			return responseV9(KindProcessProposal, id,
				statusDecidedBlockFailedRange, nil)
		})
	_, err = client.ProcessProposal(2, januaryMillis, nil)
	<-done
	if err == nil || errors.As(err, &applicationError) {
		t.Fatalf("status 7 on a proposal was answered: %#v", err)
	}
	if _, err := client.Info(); err == nil {
		t.Fatal("the client continued after a protocol failure")
	}
}

// A version-one response to a version-nine client ends the connection.
func TestVersionNineClientRefusesAVersionOneResponse(t *testing.T) {
	clientConnection, serverConnection := net.Pipe()
	defer serverConnection.Close()
	client := newClientV9(newClient(clientConnection))
	defer client.Close()

	info := appendU64(appendU64(appendU64(nil, 9), 0), januaryMillis)
	info = append(info, root9[:]...)
	done := make(chan struct{})
	go func() {
		defer close(done)
		_, requestID, _, err := readRequestV9(serverConnection)
		if err != nil {
			t.Error(err)
			_ = serverConnection.Close()
			return
		}
		// The client refuses the header and closes before reading the body, so
		// this write is expected to fail part-way; its error is not the test's.
		_, _ = serverConnection.Write(successResponse(KindInfo, requestID, info))
	}()
	if _, err := client.Info(); err == nil {
		t.Fatal("a version-one response was accepted")
	}
	<-done
}

// The two operations version two did not change are version one's, promoted,
// and they still write version two's frame.
func TestVersionNineSharesTheUnchangedOperations(t *testing.T) {
	clientConnection, serverConnection := net.Pipe()
	defer serverConnection.Close()
	client := newClientV9(newClient(clientConnection))
	defer client.Close()

	done := serveOneV9(t, serverConnection, KindCheckTransaction,
		appendBlob(nil, []byte{7}),
		func(id uint64) []byte {
			return responseV9(KindCheckTransaction, id, 0, appendU32(nil, 1))
		})
	code, err := client.CheckTransaction([]byte{7})
	<-done
	if err != nil || code != 1 {
		t.Fatalf("check = %d, %v", code, err)
	}
}

// InitChain carries the genesis stamp between the initial height and the app
// state, and Info reports the stamp between the height and the root.
func TestVersionNineInitChainAndInfo(t *testing.T) {
	clientConnection, serverConnection := net.Pipe()
	defer serverConnection.Close()
	client := newClientV9(newClient(clientConnection))
	defer client.Close()

	chainID := Hash{0: 6, 31: 6}
	appState := []byte(`"protocol-stack-v9"`)
	expected := append([]byte(nil), chainID[:]...)
	expected = binary.BigEndian.AppendUint64(expected, 1)
	expected = binary.BigEndian.AppendUint64(expected, januaryMillis-90_000)
	expected = binary.BigEndian.AppendUint32(expected, uint32(len(appState)))
	expected = append(expected, appState...)
	done := serveOneV9(t, serverConnection, KindInitChain, expected,
		func(id uint64) []byte { return responseV9(KindInitChain, id, 0, root9[:]) })
	root, err := client.InitChain(chainID, 1, januaryMillis-90_000, appState)
	<-done
	if err != nil || root != root9 {
		t.Fatalf("init_chain = %x, %v", root, err)
	}

	info := binary.BigEndian.AppendUint64(nil, 9)
	info = binary.BigEndian.AppendUint64(info, 0)
	info = binary.BigEndian.AppendUint64(info, januaryMillis-90_000)
	info = append(info, root9[:]...)
	done = serveOneV9(t, serverConnection, KindInfo, nil,
		func(id uint64) []byte { return responseV9(KindInfo, id, 0, info) })
	reported, err := client.Info()
	<-done
	if err != nil || reported != (InfoV9{9, 0, januaryMillis - 90_000, root9}) {
		t.Fatalf("info = %#v, %v", reported, err)
	}
}
