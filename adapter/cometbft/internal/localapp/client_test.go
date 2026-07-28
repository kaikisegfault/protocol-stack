package localapp

import (
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"net"
	"sync"
	"testing"
)

func successResponse(kind Kind, requestID uint64, body []byte) []byte {
	payload := []byte{0, 0, 0, 0, 0, 0}
	payload = append(payload, body...)
	return append(responseHeader(kind, requestID, uint32(len(payload))), payload...)
}

func readRequest(connection net.Conn) (Kind, uint64, []byte, error) {
	header := make([]byte, wireHeaderSize)
	if _, err := io.ReadFull(connection, header); err != nil {
		return 0, 0, nil, err
	}
	if string(header[:4]) != "PSAP" || header[6] != 0 {
		return 0, 0, nil, fmt.Errorf("invalid request header: %x", header)
	}
	size := binary.BigEndian.Uint32(header[16:20])
	payload := make([]byte, int(size))
	if _, err := io.ReadFull(connection, payload); err != nil {
		return 0, 0, nil, err
	}
	return Kind(header[7]), binary.BigEndian.Uint64(header[8:16]), payload, nil
}

func TestClientInfoAndRequestIDs(t *testing.T) {
	clientConnection, serverConnection := net.Pipe()
	defer serverConnection.Close()
	client := newClient(clientConnection)
	defer client.Close()

	root := Hash{0: 1, 31: 2}
	serverDone := make(chan struct{})
	go func() {
		defer close(serverDone)
		for requestID := uint64(1); requestID <= 32; requestID++ {
			kind, actualID, payload, err := readRequest(serverConnection)
			if err != nil {
				t.Error(err)
				return
			}
			if kind != KindInfo || actualID != requestID || len(payload) != 0 {
				t.Errorf("request = %d/%d/%x", kind, actualID, payload)
				return
			}
			body := appendU64(nil, 1)
			body = appendU64(body, 9)
			body = append(body, root[:]...)
			if _, err := serverConnection.Write(
				successResponse(kind, actualID, body)); err != nil {
				t.Error(err)
				return
			}
		}
	}()

	var wait sync.WaitGroup
	wait.Add(32)
	for range 32 {
		go func() {
			defer wait.Done()
			info, err := client.Info()
			if err != nil {
				t.Error(err)
				return
			}
			if info.ApplicationVersion != 1 || info.Height != 9 ||
				info.StateRoot != root {
				t.Errorf("unexpected Info: %#v", info)
			}
		}()
	}
	wait.Wait()
	<-serverDone
}

func TestClientWireFailureIsTerminal(t *testing.T) {
	clientConnection, serverConnection := net.Pipe()
	client := newClient(clientConnection)
	defer serverConnection.Close()

	go func() {
		kind, requestID, _, err := readRequest(serverConnection)
		if err != nil {
			t.Error(err)
			return
		}
		_, _ = serverConnection.Write(
			successResponse(kind, requestID+1, nil))
	}()
	if _, err := client.Info(); err == nil {
		t.Fatal("mismatched response accepted")
	}
	if _, err := client.Info(); err == nil {
		t.Fatal("terminal client accepted another request")
	}
}

func exchange(
	t *testing.T,
	connection net.Conn,
	kind Kind,
	expectedPayload []byte,
	responseBody []byte,
	call func() error,
) {
	t.Helper()
	done := make(chan error, 1)
	go func() {
		done <- call()
	}()
	actualKind, requestID, payload, err := readRequest(connection)
	if err != nil {
		t.Fatal(err)
	}
	if actualKind != kind || string(payload) != string(expectedPayload) {
		t.Fatalf(
			"request = kind %d payload %x, want kind %d payload %x",
			actualKind, payload, kind, expectedPayload)
	}
	if err := writeFull(
		connection, successResponse(kind, requestID, responseBody)); err != nil {
		t.Fatal(err)
	}
	if err := <-done; err != nil {
		t.Fatal(err)
	}
}

func TestClientLifecycleTranslation(t *testing.T) {
	clientConnection, serverConnection := net.Pipe()
	defer serverConnection.Close()
	client := newClient(clientConnection)
	defer client.Close()

	chain := Hash{0: 1, 31: 2}
	root := Hash{0: 3, 31: 4}
	state := []byte(`"protocol-stack-v1"`)
	initPayload := append([]byte(nil), chain[:]...)
	initPayload = appendU64(initPayload, 1)
	initPayload = appendBlob(initPayload, state)
	exchange(
		t, serverConnection, KindInitChain, initPayload, root[:],
		func() error {
			actual, err := client.InitChain(chain, 1, state)
			if err == nil && actual != root {
				return errors.New("InitChain root changed")
			}
			return err
		})

	transaction := []byte{0, 1, 2, 3}
	checkPayload := appendBlob(nil, transaction)
	exchange(
		t, serverConnection, KindCheckTransaction, checkPayload,
		[]byte{0, 0, 0, 3},
		func() error {
			code, err := client.CheckTransaction(transaction)
			if err == nil && code != 3 {
				return errors.New("CheckTx code changed")
			}
			return err
		})

	transactions := [][]byte{{1, 2}, {3}}
	preparePayload := appendU64(nil, 3)
	preparePayload, _ = appendTransactions(preparePayload, transactions)
	preparedBody, _ := appendTransactions(nil, transactions)
	exchange(
		t, serverConnection, KindPrepareProposal, preparePayload, preparedBody,
		func() error {
			prepared, err := client.PrepareProposal(3, transactions)
			if err == nil && len(prepared) != 2 {
				return errors.New("PrepareProposal prefix changed")
			}
			return err
		})

	blockPayload, _ := blockPayload(7, transactions)
	exchange(
		t, serverConnection, KindProcessProposal, blockPayload, []byte{1},
		func() error {
			accepted, err := client.ProcessProposal(7, transactions)
			if err == nil && !accepted {
				return errors.New("ProcessProposal result changed")
			}
			return err
		})

	receipt := make([]byte, 47)
	copy(receipt, []byte{'P', 'S', 'R', 'C', 0, 1})
	finalizeBody := append([]byte(nil), root[:]...)
	finalizeBody = appendU32(finalizeBody, 2)
	finalizeBody = appendU32(finalizeBody, 0)
	finalizeBody = appendBlob(finalizeBody, receipt)
	finalizeBody = appendU32(finalizeBody, 1)
	finalizeBody = appendU32(finalizeBody, 0)
	exchange(
		t, serverConnection, KindFinalizeBlock, blockPayload, finalizeBody,
		func() error {
			block, err := client.FinalizeBlock(7, transactions)
			if err == nil &&
				(block.StateRoot != root ||
					len(block.TransactionResults) != 2) {
				return errors.New("FinalizeBlock result changed")
			}
			return err
		})

	commitBody := appendU64(nil, 7)
	commitBody = append(commitBody, root[:]...)
	exchange(
		t, serverConnection, KindCommit, nil, commitBody,
		func() error {
			head, err := client.Commit()
			if err == nil && (head.Height != 7 || head.StateRoot != root) {
				return errors.New("Commit head changed")
			}
			return err
		})
}
