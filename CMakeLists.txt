cmake_minimum_required(VERSION 3.25)

project(protocol_stack LANGUAGES C CXX)

include(CTest)
include(ExternalProject)

option(PROTOCOL_STACK_ENABLE_SANITIZERS
       "Build protocol-stack verification targets with ASan and UBSan" OFF)
option(PROTOCOL_STACK_ENABLE_FUZZING
       "Build Clang libFuzzer targets" OFF)

find_package(Python3 3.11 REQUIRED COMPONENTS Interpreter)
find_program(PROTOCOL_STACK_MAKE_EXECUTABLE make REQUIRED)
find_package(Threads REQUIRED)

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
if(PROTOCOL_STACK_ENABLE_FUZZING)
  if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    message(FATAL_ERROR "Fuzzing requires Clang")
  endif()
  if(NOT PROTOCOL_STACK_ENABLE_SANITIZERS)
    message(FATAL_ERROR "Fuzzing requires sanitizer instrumentation")
  endif()
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

set(PROTOCOL_STACK_SQLITE_VERSION "3.53.3")
set(PROTOCOL_STACK_SQLITE_ARCHIVE_VERSION "3530300")
set(PROTOCOL_STACK_SQLITE_CFLAGS
    "-O2 -g -DSQLITE_DQS=0 -DSQLITE_TRUSTED_SCHEMA=0 -DSQLITE_ENABLE_API_ARMOR")
if(PROTOCOL_STACK_ENABLE_SANITIZERS)
  string(
    APPEND
    PROTOCOL_STACK_SQLITE_CFLAGS
    " -fsanitize=address,undefined -fno-omit-frame-pointer"
  )
endif()
set(PROTOCOL_STACK_SQLITE_PREFIX
    "${CMAKE_BINARY_DIR}/dependencies/sqlite")
set(PROTOCOL_STACK_SQLITE_LIBRARY
    "${PROTOCOL_STACK_SQLITE_PREFIX}/lib/libsqlite3.a")

file(MAKE_DIRECTORY "${PROTOCOL_STACK_SQLITE_PREFIX}/include")

ExternalProject_Add(
  sqlite_external
  URL
    "https://sqlite.org/2026/sqlite-autoconf-${PROTOCOL_STACK_SQLITE_ARCHIVE_VERSION}.tar.gz"
  URL_HASH
    "SHA256=c917d7db16648ec95f714974ace5e5dcf46b7dc70e26600a0a102a3141125db0"
  TLS_VERIFY ON
  UPDATE_COMMAND ""
  CONFIGURE_COMMAND
    "${CMAKE_COMMAND}" -E env
    "CC=${CMAKE_C_COMPILER}"
    "CFLAGS=${PROTOCOL_STACK_SQLITE_CFLAGS}"
    <SOURCE_DIR>/configure
    --prefix=<INSTALL_DIR>
    --libdir=<INSTALL_DIR>/lib
    --disable-shared
    --enable-static
    --disable-load-extension
    --disable-math
    --disable-json
    --disable-carray
    --disable-readline
  BUILD_COMMAND
    "${PROTOCOL_STACK_MAKE_EXECUTABLE}" libsqlite3.a
  INSTALL_COMMAND
    "${PROTOCOL_STACK_MAKE_EXECUTABLE}" install-lib install-headers
  INSTALL_DIR "${PROTOCOL_STACK_SQLITE_PREFIX}"
  BUILD_BYPRODUCTS
    "${PROTOCOL_STACK_SQLITE_LIBRARY}"
)

add_library(protocol_stack_sqlite STATIC IMPORTED GLOBAL)
set_target_properties(
  protocol_stack_sqlite
  PROPERTIES
    IMPORTED_LOCATION "${PROTOCOL_STACK_SQLITE_LIBRARY}"
    INTERFACE_INCLUDE_DIRECTORIES "${PROTOCOL_STACK_SQLITE_PREFIX}/include"
)
target_link_libraries(protocol_stack_sqlite INTERFACE Threads::Threads)
add_dependencies(protocol_stack_sqlite sqlite_external)

add_executable(
  protocol_primitive_vectors
  tools/protocol-vectors/verify.cpp
)
add_executable(
  ledger_transition_vectors
  tools/ledger-vectors/verify.cpp
)
set(
  PROTOCOL_STACK_KERNEL_SOURCES
  src/v1/address.cpp
  src/v1/admission.cpp
  src/v1/commitments.cpp
  src/v1/crypto.cpp
  src/v1/execution.cpp
  src/v1/genesis.cpp
  src/v1/ledger.cpp
)
add_library(protocol_kernel STATIC ${PROTOCOL_STACK_KERNEL_SOURCES})
target_include_directories(
  protocol_kernel
  PUBLIC
    "${PROJECT_SOURCE_DIR}/include"
)
add_executable(
  kernel_primitive_tests
  tests/kernel/primitives_test.cpp
)
target_link_libraries(kernel_primitive_tests PRIVATE protocol_kernel)
add_executable(
  kernel_admission_tests
  tests/kernel/admission_test.cpp
)
target_link_libraries(kernel_admission_tests PRIVATE protocol_kernel)
add_executable(
  kernel_execution_tests
  tests/kernel/execution_test.cpp
)
target_link_libraries(kernel_execution_tests PRIVATE protocol_kernel)
add_executable(
  kernel_genesis_tests
  tests/kernel/genesis_test.cpp
)
target_link_libraries(kernel_genesis_tests PRIVATE protocol_kernel)
add_executable(
  kernel_commitment_tests
  tests/kernel/commitments_test.cpp
)
target_link_libraries(kernel_commitment_tests PRIVATE protocol_kernel)
add_executable(
  kernel_block_tests
  tests/kernel/block_test.cpp
)
target_link_libraries(kernel_block_tests PRIVATE protocol_kernel)
add_executable(
  kernel_property_tests
  tests/kernel/property_test.cpp
)
target_link_libraries(kernel_property_tests PRIVATE protocol_kernel)
add_executable(
  kernel_differential_runner
  tests/differential/kernel_runner.cpp
)
target_link_libraries(kernel_differential_runner PRIVATE protocol_kernel)
add_executable(
  sqlite_dependency_tests
  tests/storage/sqlite_dependency_test.cpp
)
target_link_libraries(sqlite_dependency_tests PRIVATE protocol_stack_sqlite)

set(
  PROTOCOL_STACK_TARGETS
  protocol_primitive_vectors
  ledger_transition_vectors
  protocol_kernel
  kernel_primitive_tests
  kernel_admission_tests
  kernel_execution_tests
  kernel_genesis_tests
  kernel_commitment_tests
  kernel_block_tests
  kernel_property_tests
  kernel_differential_runner
  sqlite_dependency_tests
)
if(PROTOCOL_STACK_ENABLE_FUZZING)
  add_library(
    protocol_kernel_fuzz
    STATIC
      ${PROTOCOL_STACK_KERNEL_SOURCES}
  )
  target_include_directories(
    protocol_kernel_fuzz
    PUBLIC
      "${PROJECT_SOURCE_DIR}/include"
  )
  add_executable(
    kernel_admission_fuzz
    tests/fuzz/admission_fuzz.cpp
  )
  target_link_libraries(kernel_admission_fuzz PRIVATE protocol_kernel_fuzz)
  add_executable(
    kernel_address_fuzz
    tests/fuzz/address_fuzz.cpp
  )
  target_link_libraries(kernel_address_fuzz PRIVATE protocol_kernel_fuzz)
  add_executable(
    kernel_genesis_fuzz
    tests/fuzz/genesis_fuzz.cpp
  )
  target_link_libraries(kernel_genesis_fuzz PRIVATE protocol_kernel_fuzz)
  list(
    APPEND
    PROTOCOL_STACK_TARGETS
    protocol_kernel_fuzz
    kernel_admission_fuzz
    kernel_address_fuzz
    kernel_genesis_fuzz
  )
endif()

foreach(protocol_stack_target IN LISTS PROTOCOL_STACK_TARGETS)
  target_compile_features(${protocol_stack_target} PRIVATE cxx_std_20)
  target_compile_definitions(
    ${protocol_stack_target}
    PRIVATE
      _GLIBCXX_ASSERTIONS
  )
  target_compile_options(
    ${protocol_stack_target}
    PRIVATE
      -Wall
      -Wextra
      -Wpedantic
      -Werror
      ${PROTOCOL_STACK_SANITIZER_FLAGS}
  )
  target_link_options(
    ${protocol_stack_target}
    PRIVATE
      ${PROTOCOL_STACK_SANITIZER_FLAGS}
  )
  target_link_libraries(${protocol_stack_target} PRIVATE protocol_stack_sodium)
endforeach()
if(PROTOCOL_STACK_ENABLE_FUZZING)
  foreach(
    protocol_stack_fuzz_target
    IN ITEMS
      protocol_kernel_fuzz
      kernel_admission_fuzz
      kernel_address_fuzz
      kernel_genesis_fuzz
  )
    target_compile_options(
      ${protocol_stack_fuzz_target}
      PRIVATE
        -fsanitize=fuzzer-no-link
    )
  endforeach()
  foreach(
    protocol_stack_fuzz_executable
    IN ITEMS
      kernel_admission_fuzz
      kernel_address_fuzz
      kernel_genesis_fuzz
  )
    target_link_options(
      ${protocol_stack_fuzz_executable}
      PRIVATE
        -fsanitize=fuzzer
    )
  endforeach()
endif()

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
add_test(
  NAME ledger-transition-cpp
  COMMAND
    ledger_transition_vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
)
add_test(
  NAME ledger-transition-python
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/ledger-vectors/verify.py"
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
)
add_test(
  NAME kernel-primitives
  COMMAND
    kernel_primitive_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/protocol-primitives-v1.txt"
)
add_test(
  NAME kernel-admission
  COMMAND
    kernel_admission_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
)
add_test(
  NAME kernel-execution
  COMMAND
    kernel_execution_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
)
add_test(
  NAME kernel-genesis
  COMMAND
    kernel_genesis_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
)
add_test(
  NAME kernel-commitments
  COMMAND
    kernel_commitment_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
)
add_test(
  NAME kernel-block
  COMMAND
    kernel_block_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
)
add_test(
  NAME kernel-properties
  COMMAND kernel_property_tests
)
add_test(
  NAME kernel-differential
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/differential/run.py"
    "$<TARGET_FILE:kernel_differential_runner>"
    --count
    10000
    --libsodium
    "${PROTOCOL_STACK_SODIUM_SHARED_LIBRARY}"
)
add_test(
  NAME sqlite-dependency
  COMMAND
    sqlite_dependency_tests
    "${CMAKE_CURRENT_BINARY_DIR}/sqlite-dependency-test.db"
)
set_tests_properties(
  protocol-primitives-python
  ledger-transition-python
  PROPERTIES
    ENVIRONMENT
      "PROTOCOL_STACK_LIBSODIUM=${PROTOCOL_STACK_SODIUM_SHARED_LIBRARY}"
)
set_tests_properties(
  kernel-differential
  PROPERTIES
    TIMEOUT 300
)
if(PROTOCOL_STACK_ENABLE_FUZZING)
  add_test(
    NAME kernel-admission-fuzz-smoke
    COMMAND
      kernel_admission_fuzz
      -seed=824311
      -runs=512
      -max_len=256
      -len_control=0
  )
  add_test(
    NAME kernel-genesis-fuzz-smoke
    COMMAND
      kernel_genesis_fuzz
      -seed=824311
      -runs=512
      -max_len=4096
      -len_control=0
  )
  add_test(
    NAME kernel-address-fuzz-smoke
    COMMAND
      kernel_address_fuzz
      -seed=824311
      -runs=512
      -max_len=256
      -len_control=0
  )
  set_tests_properties(
    kernel-admission-fuzz-smoke
    kernel-address-fuzz-smoke
    kernel-genesis-fuzz-smoke
    PROPERTIES
      LABELS fuzz
      TIMEOUT 60
  )
endif()
