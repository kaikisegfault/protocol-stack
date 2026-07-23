cmake_minimum_required(VERSION 3.25)

project(protocol_stack LANGUAGES C CXX)

include(CTest)
include(ExternalProject)

option(PROTOCOL_STACK_ENABLE_SANITIZERS
       "Build protocol-stack verification targets with ASan and UBSan" OFF)

find_package(Python3 3.11 REQUIRED COMPONENTS Interpreter)
find_program(PROTOCOL_STACK_MAKE_EXECUTABLE make REQUIRED)

set(PROTOCOL_STACK_SODIUM_VERSION "1.0.22")
set(PROTOCOL_STACK_SODIUM_PREFIX
    "${CMAKE_BINARY_DIR}/dependencies/libsodium")
set(PROTOCOL_STACK_SODIUM_LIBRARY
    "${PROTOCOL_STACK_SODIUM_PREFIX}/lib/libsodium.a")
set(PROTOCOL_STACK_SODIUM_SHARED_LIBRARY
    "${PROTOCOL_STACK_SODIUM_PREFIX}/lib/${CMAKE_SHARED_LIBRARY_PREFIX}sodium${CMAKE_SHARED_LIBRARY_SUFFIX}")

set(PROTOCOL_STACK_SANITIZER_FLAGS "")
if(PROTOCOL_STACK_ENABLE_SANITIZERS)
  if(NOT CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
    message(FATAL_ERROR "Sanitizer presets require GCC or Clang")
  endif()
  set(PROTOCOL_STACK_SANITIZER_FLAGS
      "-fsanitize=address,undefined;-fno-omit-frame-pointer")
endif()

file(MAKE_DIRECTORY "${PROTOCOL_STACK_SODIUM_PREFIX}/include")

ExternalProject_Add(
  libsodium_external
  URL
    "https://download.libsodium.org/libsodium/releases/libsodium-${PROTOCOL_STACK_SODIUM_VERSION}.tar.gz"
  URL_HASH
    "SHA256=adbdd8f16149e81ac6078a03aca6fc03b592b89ef7b5ed83841c086191be3349"
  TLS_VERIFY ON
  UPDATE_COMMAND ""
  CONFIGURE_COMMAND
    "${CMAKE_COMMAND}" -E env
    "CC=${CMAKE_C_COMPILER}"
    "CFLAGS=-O2 -g"
    <SOURCE_DIR>/configure
    --prefix=<INSTALL_DIR>
    --libdir=<INSTALL_DIR>/lib
    --disable-dependency-tracking
    --enable-static
    --enable-shared
    --with-pic
  BUILD_COMMAND "${PROTOCOL_STACK_MAKE_EXECUTABLE}"
  INSTALL_COMMAND "${PROTOCOL_STACK_MAKE_EXECUTABLE}" install
  INSTALL_DIR "${PROTOCOL_STACK_SODIUM_PREFIX}"
  BUILD_BYPRODUCTS
    "${PROTOCOL_STACK_SODIUM_LIBRARY}"
    "${PROTOCOL_STACK_SODIUM_SHARED_LIBRARY}"
)

add_library(protocol_stack_sodium STATIC IMPORTED GLOBAL)
set_target_properties(
  protocol_stack_sodium
  PROPERTIES
    IMPORTED_LOCATION "${PROTOCOL_STACK_SODIUM_LIBRARY}"
    INTERFACE_INCLUDE_DIRECTORIES "${PROTOCOL_STACK_SODIUM_PREFIX}/include"
)
add_dependencies(protocol_stack_sodium libsodium_external)

add_executable(
  protocol_primitive_vectors
  tools/protocol-vectors/verify.cpp
)
target_compile_features(protocol_primitive_vectors PRIVATE cxx_std_20)
target_compile_definitions(
  protocol_primitive_vectors
  PRIVATE
    _GLIBCXX_ASSERTIONS
)
target_compile_options(
  protocol_primitive_vectors
  PRIVATE
    -Wall
    -Wextra
    -Wpedantic
    -Werror
    ${PROTOCOL_STACK_SANITIZER_FLAGS}
)
target_link_options(
  protocol_primitive_vectors
  PRIVATE
    ${PROTOCOL_STACK_SANITIZER_FLAGS}
)
target_link_libraries(protocol_primitive_vectors PRIVATE protocol_stack_sodium)

add_test(
  NAME protocol-primitives-cpp
  COMMAND
    protocol_primitive_vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/protocol-primitives-v1.txt"
)
add_test(
  NAME protocol-primitives-python
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/protocol-vectors/verify.py"
    "${PROJECT_SOURCE_DIR}/test-vectors/protocol-primitives-v1.txt"
)
set_tests_properties(
  protocol-primitives-python
  PROPERTIES
    ENVIRONMENT
      "PROTOCOL_STACK_LIBSODIUM=${PROTOCOL_STACK_SODIUM_SHARED_LIBRARY}"
)
