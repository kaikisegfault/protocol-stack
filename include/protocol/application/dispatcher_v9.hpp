#pragma once

// One decoded version-two request to one encoded version-two response frame, for
// the version-nine application. It performs no I/O: the socket loop reads the
// frame and writes what this returns, which is what lets the whole request
// surface be tested against bytes without a socket.

#include "protocol/application/application_v9.hpp"
#include "protocol/application/wire_v2.hpp"

namespace protocol::application {

EncodedFrameResult dispatch_request_v9(ApplicationV9& application,
                                       const DecodedRequestV2& request);

}  // namespace protocol::application
