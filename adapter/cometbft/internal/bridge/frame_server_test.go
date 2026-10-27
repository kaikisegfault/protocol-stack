package bridge

import (
	"encoding/binary"
	"io"
	"net"
	"path/filepath"
	"sync"
	"testing"
)

// A stand-in application on a real Unix socket, for the ledger versions that
// speak the version-two frame: nine and ten. It speaks the frame by hand — none
// of `localapp`'s encoders — and records every request, so what these tests
// check is the octets the bridge actually sent. It moved here from
// `application_v9_test.go` so that ADR 0104's step 7 can delete that file whole.
type frameServer struct {
	mutex    sync.Mutex
	requests []frameRequest
	answer   func(kind byte, payload []byte) (uint16, []byte)
}

type frameRequest struct {
	kind    byte
	payload []byte
}

func startFrameServer(
	t *testing.T,
	answer func(kind byte, payload []byte) (uint16, []byte),
) (*frameServer, string) {
	path := filepath.Join(t.TempDir(), "s")
	listener, err := net.Listen("unix", path)
	if err != nil {
		t.Fatal(err)
	}
	server := &frameServer{answer: answer}
	go func() {
		connection, err := listener.Accept()
		_ = listener.Close()
		if err != nil {
			return
		}
		defer connection.Close()
		for server.serveOne(connection) {
		}
	}()
	t.Cleanup(func() { _ = listener.Close() })
	return server, path
}

func (s *frameServer) serveOne(connection net.Conn) bool {
	header := make([]byte, 20)
	if _, err := io.ReadFull(connection, header); err != nil ||
		binary.BigEndian.Uint16(header[4:6]) != 2 {
		return false
	}
	payload := make([]byte, int(binary.BigEndian.Uint32(header[16:20])))
	if _, err := io.ReadFull(connection, payload); err != nil {
		return false
	}
	s.mutex.Lock()
	s.requests = append(s.requests, frameRequest{header[7], payload})
	s.mutex.Unlock()
	status, body := s.answer(header[7], payload)
	response := binary.BigEndian.AppendUint16(nil, status)
	response = binary.BigEndian.AppendUint32(response, 0)
	response = append(response, body...)
	frame := append([]byte("PSAP"), 0, 2, 1, header[7])
	frame = append(frame, header[8:16]...)
	frame = binary.BigEndian.AppendUint32(frame, uint32(len(response)))
	_, err := connection.Write(append(frame, response...))
	return err == nil
}

func (s *frameServer) sent() []frameRequest {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	return append([]frameRequest(nil), s.requests...)
}

func stampOf(payload []byte, offset int) uint64 {
	return binary.BigEndian.Uint64(payload[offset : offset+8])
}
