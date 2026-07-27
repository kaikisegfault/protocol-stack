#pragma once

#include "protocol/application/application_v1.hpp"
#include "protocol/application/wire_v1.hpp"

namespace protocol::application {

EncodedFrameResult dispatch_request(
    ApplicationV1& application,
    const DecodedRequest& request);

}  // namespace protocol::application
