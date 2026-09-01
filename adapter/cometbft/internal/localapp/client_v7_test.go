package localapp

import (
	"net"
	"testing"
)

// The version-seven client sends version one's frames. Only the response it
// reads back is its own, so the request this test reads off the wire must be
// byte-for-byte the request version one would have sent.
func TestVersionSevenClientSendsVersionOnesRequest(t *testing.T) {
	clientConnection, serverConnection := net.Pipe()
	defer serverConnection.Close()
	client := newClientV7(newClient(clientConnection))
	defer client.Close()

	root := Hash{0: 0xa5, 31: 0x5a}
	blockID := Hash{0: 0x5a, 31: 0xa5}
	transactions := [][]byte{{1, 2, 3}, {4}}
	serverDone := make(chan struct{})
	go func() {
		defer close(serverDone)
		kind, requestID, payload, err := readRequest(serverConnection)
		if err != nil {
			t.Error(err)
			return
		}
		expected, err := blockPayload(9, transactions)
		if err != nil {
			t.Error(err)
			return
		}
		if kind != KindFinalizeBlock || requestID != 1 ||
			string(payload) != string(expected) {
			t.Errorf("request = %d/%d/%x", kind, requestID, payload)
			return
		}
		body := append([]byte(nil), root[:]...)
		body = append(body, blockID[:]...)
		body = appendU32(body, 2)
		body = appendU32(body, 0)
		body = appendBlob(body, receiptV7(0))
		body = appendU32(body, 2)
		body = appendU32(body, 0)
		if _, err := serverConnection.Write(
			successResponse(kind, requestID, body)); err != nil {
			t.Error(err)
		}
	}()

	block, err := client.FinalizeBlock(9, transactions)
	if err != nil {
		t.Fatal(err)
	}
	<-serverDone
	if block.StateRoot != root || block.BlockID != blockID ||
		len(block.TransactionResults) != 2 ||
		block.TransactionResults[0].Code != 0 ||
		len(block.TransactionResults[0].Data) != receiptBytesV7 ||
		block.TransactionResults[1].Code != 2 ||
		len(block.TransactionResults[1].Data) != 0 {
		t.Fatalf("unexpected finalized block: %#v", block)
	}
}

// The six operations that are not version-specific are the embedded client's,
// so a version-seven client answers them without a second copy of anything.
func TestVersionSevenClientSharesTheOtherOperations(t *testing.T) {
	clientConnection, serverConnection := net.Pipe()
	defer serverConnection.Close()
	client := newClientV7(newClient(clientConnection))
	defer client.Close()

	root := Hash{0: 7}
	serverDone := make(chan struct{})
	go func() {
		defer close(serverDone)
		kind, requestID, payload, err := readRequest(serverConnection)
		if err != nil {
			t.Error(err)
			return
		}
		if kind != KindInfo || len(payload) != 0 {
			t.Errorf("request = %d/%x", kind, payload)
			return
		}
		body := appendU64(nil, 7)
		body = appendU64(body, 4)
		body = append(body, root[:]...)
		if _, err := serverConnection.Write(
			successResponse(kind, requestID, body)); err != nil {
			t.Error(err)
		}
	}()

	info, err := client.Info()
	if err != nil {
		t.Fatal(err)
	}
	<-serverDone
	if info.ApplicationVersion != 7 || info.Height != 4 ||
		info.StateRoot != root {
		t.Fatalf("unexpected Info: %#v", info)
	}
}

// A protocol failure in the version-seven response is terminal for the whole
// connection, the same as version one's, because the latch is the embedded
// client's and there is only one of it.
func TestVersionSevenProtocolFailureIsTerminal(t *testing.T) {
	clientConnection, serverConnection := net.Pipe()
	defer serverConnection.Close()
	client := newClientV7(newClient(clientConnection))

	go func() {
		kind, requestID, _, err := readRequest(serverConnection)
		if err != nil {
			t.Error(err)
			return
		}
		// Version one's finalized block: no identifier, so the count the
		// version-seven decoder reads is the identifier's leading octets.
		body := make([]byte, 32)
		body = appendU32(body, 1)
		body = appendU32(body, 0)
		body = appendBlob(body, receiptV7(0))
		if _, err := serverConnection.Write(
			successResponse(kind, requestID, body)); err != nil {
			t.Error(err)
		}
	}()

	if _, err := client.FinalizeBlock(1, [][]byte{{1}}); err == nil {
		t.Fatal("a version-one finalized block was accepted")
	}
	if _, err := client.Info(); err == nil {
		t.Fatal("the connection survived a protocol failure")
	}
}
