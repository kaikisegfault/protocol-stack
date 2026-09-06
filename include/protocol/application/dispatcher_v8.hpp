#pragma once

// One decoded request to one encoded response frame, for the version-eight
// application. It performs no I/O: the socket loop reads the frame and writes
// what this returns, which is what lets the whole request surface be tested
// against bytes without a socket.

#include "protocol/application/application_v8.hpp"
#include "protocol/application/wire_v1.hpp"

namespace protocol::application {

EncodedFrameResult dispatch_request_v8(ApplicationV8& application,
                                       const DecodedRequest& request);

}  // namespace protocol::application
