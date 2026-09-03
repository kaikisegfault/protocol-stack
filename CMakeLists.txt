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
  src/v7/economy_assignment.cpp
  src/v7/economy_block.cpp
  src/v7/economy_body.cpp
  src/v7/economy_contract.cpp
  src/v7/economy_envelope.cpp
  src/v7/economy_execution.cpp
  src/v7/economy_genesis.cpp
  src/v7/economy_identity.cpp
  src/v7/economy_invariants.cpp
  src/v7/economy_ledger.cpp
  src/v7/economy_messages.cpp
  src/v7/economy_receipt.cpp
  src/v7/economy_settlement.cpp
  src/v7/economy_state.cpp
  src/v7/economy_transitions.cpp
  src/v7/economy_tree.cpp
  src/v7/economy_value_transitions.cpp
)
add_library(protocol_kernel STATIC ${PROTOCOL_STACK_KERNEL_SOURCES})
target_include_directories(
  protocol_kernel
  PUBLIC
    "${PROJECT_SOURCE_DIR}/include"
)
add_library(
  protocol_storage
  STATIC
    src/storage/archive_v1.cpp
    src/storage/sqlite_archive_import_v1.cpp
    src/storage/sqlite_archive_v1.cpp
    src/storage/sqlite_connection.cpp
    src/storage/sqlite_fault_injection.cpp
    src/storage/sqlite_block_store_v1.cpp
    src/storage/sqlite_history_replay_v1.cpp
    src/storage/sqlite_ledger.cpp
    src/storage/sqlite_schema_v1.cpp
    src/storage/sqlite_ledger_v7.cpp
    src/storage/sqlite_ledger_v7_open.cpp
    src/storage/sqlite_schema_v7.cpp
    src/storage/sqlite_snapshot_v1.cpp
    src/storage/snapshot_v1.cpp
    src/storage/snapshot_v7.cpp
    src/storage/snapshot_v7_assignments.cpp
    src/storage/snapshot_v7_entries.cpp
)
add_library(
  protocol_application
  STATIC
    src/application/application_block_v1.cpp
    src/application/application_block_v7.cpp
    src/application/application_v1.cpp
    src/application/application_v7.cpp
    src/application/dispatcher_v1.cpp
    src/application/dispatcher_v7.cpp
    src/application/response_v1.cpp
    src/application/response_v7.cpp
    src/application/unix_connection_v1.cpp
    src/application/unix_server_v1.cpp
    src/application/wire_v1.cpp
)
target_include_directories(
  protocol_application
  PUBLIC
    "${PROJECT_SOURCE_DIR}/include"
)
target_link_libraries(
  protocol_application
  PUBLIC
    protocol_storage
)
add_executable(
  protocol_application_server
  src/application/main.cpp
)
set_target_properties(
  protocol_application_server
  PROPERTIES
    OUTPUT_NAME protocol-application
)
target_link_libraries(
  protocol_application_server
  PRIVATE
    protocol_application
)
add_executable(
  protocol_application_server_v7
  src/application/main_v7.cpp
)
set_target_properties(
  protocol_application_server_v7
  PROPERTIES
    OUTPUT_NAME protocol-application-v7
)
target_link_libraries(
  protocol_application_server_v7
  PRIVATE
    protocol_application
)
target_include_directories(
  protocol_storage
  PUBLIC
    "${PROJECT_SOURCE_DIR}/include"
)
target_link_libraries(
  protocol_storage
  PUBLIC
    protocol_kernel
  PRIVATE
    protocol_stack_sqlite
)
add_executable(
  kernel_primitive_tests
  tests/kernel/primitives_test.cpp
)
target_link_libraries(kernel_primitive_tests PRIVATE protocol_kernel)
add_executable(
  economy_v7_codec_tests
  tests/kernel/economy_v7_test.cpp
  tests/kernel/economy_v7_encoding_test.cpp
  tests/kernel/economy_v7_identity_test.cpp
  tests/kernel/economy_v7_settlement_test.cpp
  tests/kernel/economy_v7_state_test.cpp
  tests/kernel/economy_v7_version_test.cpp
)
target_link_libraries(economy_v7_codec_tests PRIVATE protocol_kernel)
add_executable(
  economy_v7_execution_tests
  tests/kernel/economy_v7_execution_test.cpp
  tests/kernel/economy_v7_trace.cpp
  tests/kernel/economy_v7_scenarios_test.cpp
  tests/kernel/economy_v7_execution_checks.cpp
  tests/kernel/economy_v7_derived_test.cpp
  tests/kernel/economy_v7_transitions_test.cpp
)
target_link_libraries(economy_v7_execution_tests PRIVATE protocol_kernel)
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
  kernel_restore_tests
  tests/kernel/restore_test.cpp
)
target_link_libraries(kernel_restore_tests PRIVATE protocol_kernel)
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
add_executable(
  storage_sqlite_ledger_tests
  tests/storage/sqlite_ledger_test.cpp
)
add_executable(
  storage_sqlite_history_tests
  tests/storage/sqlite_history_test.cpp
)
add_executable(
  storage_sqlite_recovery_tests
  tests/storage/sqlite_recovery_test.cpp
)
add_executable(
  storage_sqlite_sequence_tests
  tests/storage/sqlite_sequence_test.cpp
)
add_executable(
  storage_sqlite_vfs_failure_tests
  tests/storage/sqlite_vfs_failure_test.cpp
  tests/storage/sqlite_fault_vfs.cpp
)
# The scenario translation units are the kernel execution suite's own: a
# recovered head is checked against the recorded roots, not against the store.
add_executable(
  storage_sqlite_recovery_v7_tests
  tests/storage/sqlite_recovery_v7_test.cpp
  tests/storage/sqlite_fault_vfs.cpp
  tests/kernel/economy_v7_trace.cpp
  tests/kernel/economy_v7_scenarios_test.cpp
)
add_executable(
  storage_snapshot_v1_tests
  tests/storage/snapshot_v1_test.cpp
)
# The two scenario translation units are the kernel execution suite's own, reused
# rather than restated: the recorded scenarios are what a snapshot is checked
# against, and a second copy of them would be a second opinion about the states
# whose roots the vectors fix.
# The two scenario translation units are the kernel execution suite's own, for
# the reason the snapshot tests reuse them: the recorded scenarios are the third
# source a store is checked against.
add_executable(
  storage_sqlite_ledger_v7_tests
  tests/storage/sqlite_ledger_v7_test.cpp
  tests/storage/sqlite_ledger_v7_refusals.cpp
  tests/kernel/economy_v7_trace.cpp
  tests/kernel/economy_v7_scenarios_test.cpp
)
add_executable(
  storage_snapshot_v7_tests
  tests/storage/snapshot_v7_test.cpp
  tests/storage/snapshot_v7_fixture.cpp
  tests/storage/snapshot_v7_round_trip.cpp
  tests/storage/snapshot_v7_refusals.cpp
  tests/storage/snapshot_v7_entry_refusals.cpp
  tests/kernel/economy_v7_trace.cpp
  tests/kernel/economy_v7_scenarios_test.cpp
)
add_executable(
  storage_archive_v1_tests
  tests/storage/archive_v1_test.cpp
)
add_executable(
  application_v1_tests
  tests/application/application_v1_test.cpp
)
# The two scenario translation units are the kernel execution suite's own, for
# the reason the snapshot and store tests reuse them: the recorded scenarios are
# the third source a block driven through the application is checked against.
add_executable(
  application_v7_tests
  tests/application/application_v7_test.cpp
  tests/kernel/economy_v7_trace.cpp
  tests/kernel/economy_v7_scenarios_test.cpp
)
# The scenario translation units are the kernel execution suite's own: the
# recorded scenarios are the third source a block driven over the wire is
# checked against.
add_executable(
  application_transport_v7_tests
  tests/application/transport_v7_test.cpp
  tests/kernel/economy_v7_trace.cpp
  tests/kernel/economy_v7_scenarios_test.cpp
)
add_executable(
  application_wire_v1_tests
  tests/application/wire_v1_test.cpp
)
add_executable(
  application_response_v1_tests
  tests/application/response_v1_test.cpp
)
add_executable(
  application_unix_server_v1_tests
  tests/application/unix_server_v1_test.cpp
)
target_link_libraries(
  storage_sqlite_ledger_tests
  PRIVATE
    protocol_storage
    protocol_stack_sqlite
)
target_link_libraries(
  storage_sqlite_history_tests
  PRIVATE
    protocol_storage
    protocol_stack_sqlite
)
target_link_libraries(
  storage_sqlite_recovery_tests
  PRIVATE
    protocol_storage
    protocol_stack_sqlite
)
target_link_libraries(
  storage_sqlite_sequence_tests
  PRIVATE
    protocol_storage
    protocol_stack_sqlite
)
target_link_libraries(
  storage_sqlite_recovery_v7_tests
  PRIVATE
    protocol_storage
    protocol_stack_sqlite
)
target_link_libraries(
  storage_sqlite_vfs_failure_tests
  PRIVATE
    protocol_storage
    protocol_stack_sqlite
)
target_link_libraries(
  storage_snapshot_v1_tests
  PRIVATE
    protocol_storage
    protocol_stack_sqlite
)
target_link_libraries(
  storage_snapshot_v7_tests
  PRIVATE
    protocol_storage
    protocol_stack_sqlite
)
target_link_libraries(
  storage_sqlite_ledger_v7_tests
  PRIVATE
    protocol_storage
    protocol_stack_sqlite
)
target_link_libraries(
  storage_archive_v1_tests
  PRIVATE
    protocol_storage
    protocol_stack_sqlite
)
target_link_libraries(
  application_v1_tests
  PRIVATE
    protocol_application
)
target_link_libraries(
  application_v7_tests
  PRIVATE
    protocol_application
    protocol_stack_sqlite
)
target_link_libraries(
  application_transport_v7_tests
  PRIVATE
    protocol_application
    protocol_stack_sqlite
)
target_link_libraries(
  application_wire_v1_tests
  PRIVATE
    protocol_application
)
target_link_libraries(
  application_response_v1_tests
  PRIVATE
    protocol_application
)
target_link_libraries(
  application_unix_server_v1_tests
  PRIVATE
    protocol_application
    Threads::Threads
)

set(
  PROTOCOL_STACK_TARGETS
  protocol_primitive_vectors
  ledger_transition_vectors
  protocol_kernel
  protocol_storage
  protocol_application
  protocol_application_server
  protocol_application_server_v7
  kernel_primitive_tests
  economy_v7_codec_tests
  economy_v7_execution_tests
  kernel_admission_tests
  kernel_execution_tests
  kernel_genesis_tests
  kernel_commitment_tests
  kernel_block_tests
  kernel_restore_tests
  kernel_property_tests
  kernel_differential_runner
  sqlite_dependency_tests
  storage_sqlite_ledger_tests
  storage_sqlite_history_tests
  storage_sqlite_recovery_tests
  storage_sqlite_sequence_tests
  storage_sqlite_vfs_failure_tests
  storage_sqlite_recovery_v7_tests
  storage_snapshot_v1_tests
  storage_snapshot_v7_tests
  storage_sqlite_ledger_v7_tests
  storage_archive_v1_tests
  application_v1_tests
  application_v7_tests
  application_transport_v7_tests
  application_wire_v1_tests
  application_response_v1_tests
  application_unix_server_v1_tests
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
    economy_v7_fuzz
    tests/fuzz/economy_v7_fuzz.cpp
  )
  target_link_libraries(economy_v7_fuzz PRIVATE protocol_kernel_fuzz)
  add_executable(
    kernel_genesis_fuzz
    tests/fuzz/genesis_fuzz.cpp
  )
  add_library(
    protocol_storage_fuzz
    STATIC
      src/storage/archive_v1.cpp
      src/storage/snapshot_v1.cpp
      src/storage/snapshot_v7.cpp
      src/storage/snapshot_v7_assignments.cpp
      src/storage/snapshot_v7_entries.cpp
  )
  add_library(
    protocol_application_wire_fuzz
    STATIC
      src/application/wire_v1.cpp
  )
  target_include_directories(
    protocol_application_wire_fuzz
    PUBLIC
      "${PROJECT_SOURCE_DIR}/include"
  )
  target_include_directories(
    protocol_storage_fuzz
    PUBLIC
      "${PROJECT_SOURCE_DIR}/include"
  )
  target_link_libraries(
    protocol_storage_fuzz
    PUBLIC
      protocol_kernel_fuzz
  )
  add_executable(
    storage_snapshot_fuzz
    tests/fuzz/snapshot_fuzz.cpp
  )
  add_executable(
    storage_snapshot_v7_fuzz
    tests/fuzz/snapshot_v7_fuzz.cpp
  )
  add_executable(
    storage_archive_fuzz
    tests/fuzz/archive_fuzz.cpp
  )
  add_executable(
    application_wire_fuzz
    tests/fuzz/application_wire_fuzz.cpp
  )
  target_link_libraries(
    storage_archive_fuzz
    PRIVATE
      protocol_storage_fuzz
  )
  target_link_libraries(
    storage_snapshot_fuzz
    PRIVATE
      protocol_storage_fuzz
  )
  target_link_libraries(
    storage_snapshot_v7_fuzz
    PRIVATE
      protocol_storage_fuzz
  )
  target_link_libraries(
    application_wire_fuzz
    PRIVATE
      protocol_application_wire_fuzz
  )
  target_link_libraries(kernel_genesis_fuzz PRIVATE protocol_kernel_fuzz)
  list(
    APPEND
    PROTOCOL_STACK_TARGETS
    protocol_kernel_fuzz
    kernel_admission_fuzz
    kernel_address_fuzz
    kernel_genesis_fuzz
    economy_v7_fuzz
    protocol_storage_fuzz
    storage_snapshot_fuzz
    storage_snapshot_v7_fuzz
    storage_archive_fuzz
    protocol_application_wire_fuzz
    application_wire_fuzz
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
      economy_v7_fuzz
      protocol_storage_fuzz
      storage_snapshot_fuzz
      storage_snapshot_v7_fuzz
      storage_archive_fuzz
      protocol_application_wire_fuzz
      application_wire_fuzz
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
      economy_v7_fuzz
      storage_snapshot_fuzz
      storage_snapshot_v7_fuzz
      storage_archive_fuzz
      application_wire_fuzz
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
  NAME economy-transition-v7-cpp
  COMMAND
    economy_v7_codec_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v7.txt"
    "${PROJECT_SOURCE_DIR}/test-vectors/protocol-primitives-v1.txt"
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v3.txt"
    "${PROJECT_SOURCE_DIR}/test-vectors/founder-economy-manifest-v3.txt"
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v6.txt"
)
add_test(
  NAME economy-transition-v7-execution-cpp
  COMMAND
    economy_v7_execution_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v7-execution.txt"
    "${PROJECT_SOURCE_DIR}/test-vectors/protocol-primitives-v1.txt"
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
    "${PROJECT_SOURCE_DIR}/test-vectors/founder-economy-manifest-v3.txt"
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v3.txt"
)
add_test(
  NAME version-seven-snapshot
  COMMAND
    storage_snapshot_v7_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v7-execution.txt"
)
# The directory name is short because the termination cases re-exec this binary
# and its arguments include the directory.
add_test(
  NAME version-seven-store-recovery
  COMMAND
    storage_sqlite_recovery_v7_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v7-execution.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/sr-v7"
)
add_test(
  NAME version-seven-owning-store
  COMMAND
    storage_sqlite_ledger_v7_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v7-execution.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/version-seven-owning-store"
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
  NAME kernel-restore
  COMMAND
    kernel_restore_tests
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
add_test(
  NAME storage-sqlite-ledger
  COMMAND
    storage_sqlite_ledger_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/storage-sqlite-ledger-test"
)
add_test(
  NAME storage-sqlite-history
  COMMAND
    storage_sqlite_history_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/storage-sqlite-history-test"
)
add_test(
  NAME storage-sqlite-recovery
  COMMAND
    storage_sqlite_recovery_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/storage-sqlite-recovery-test"
)
add_test(
  NAME storage-sqlite-sequence
  COMMAND
    storage_sqlite_sequence_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
    "${PROJECT_SOURCE_DIR}/test-vectors/protocol-primitives-v1.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/storage-sqlite-sequence-test.db"
)
add_test(
  NAME storage-sqlite-vfs-failures
  COMMAND
    storage_sqlite_vfs_failure_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/storage-sqlite-vfs-failure-test"
)
add_test(
  NAME storage-snapshot-v1
  COMMAND
    storage_snapshot_v1_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/storage-snapshot-v1-test"
)
add_test(
  NAME storage-archive-v1
  COMMAND
    storage_archive_v1_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/storage-archive-v1-test"
)
add_test(
  NAME application-v1
  COMMAND
    application_v1_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/application-v1-test"
)
add_test(
  NAME version-seven-application
  COMMAND
    application_v7_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v7-execution.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/version-seven-application"
)
# The directory name is deliberately short: this entry binds a Unix socket
# inside it, and `sun_path` caps a socket pathname near 108 octets.
add_test(
  NAME version-seven-transport
  COMMAND
    application_transport_v7_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v7-execution.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/at-v7"
)
add_test(
  NAME application-wire-v1
  COMMAND application_wire_v1_tests
)
add_test(
  NAME application-response-v1
  COMMAND
    application_response_v1_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/application-response-v1-test.db"
)
add_test(
  NAME application-unix-server-v1
  COMMAND
    application_unix_server_v1_tests
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/au-v1"
)
add_test(
  NAME application-headless-process
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/application/headless_process_test.py"
    "$<TARGET_FILE:protocol_application_server>"
    "${PROJECT_SOURCE_DIR}/test-vectors/ledger-transition-v1.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/ah-v1"
)
# The directory name is short because this entry binds a Unix socket inside it
# and `sun_path` caps a socket pathname near 108 octets.
add_test(
  NAME version-seven-headless-process
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/application/headless_process_v7_test.py"
    "$<TARGET_FILE:protocol_application_server_v7>"
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v7-execution.txt"
    "${CMAKE_CURRENT_BINARY_DIR}/ah-v7"
)
add_test(
  NAME cometbft-port-allocation
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/integration/cometbft_port_allocation_test.py"
)
add_test(
  NAME repository-metadata
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/verify_metadata.py"
)
add_test(
  NAME verification-scope
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/tools/verification_scope_test.py"
)
add_test(
  NAME verify-metadata
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/tools/verify_metadata_test.py"
)
# The registration guard was reachable only through the focused metadata path,
# which the workflow runs when the scope classifies `lightweight`. A change that
# adds a test or a verifier classifies `full`, so the one check that catches an
# unregistered entry was skipped by exactly the pull requests that can introduce
# one. It is registered here so both paths run it.
add_test(
  NAME test-registration
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/tools/test_registration_test.py"
)
add_test(
  NAME founder-economy-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/founder-economy-vectors/verify.py"
    --manifest-vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/founder-economy-manifest-v1.txt"
    --simulator-vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/founder-economy-simulator-v1.txt"
)
add_test(
  NAME founder-economy-manifest
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_economy_manifest_test.py"
)
add_test(
  NAME founder-economy-model
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_economy_model_test.py"
)
add_test(
  NAME founder-economy-errors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_economy_errors_test.py"
)
add_test(
  NAME founder-economy-scenarios
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_economy_scenario_test.py"
)
add_test(
  NAME founder-economy-v2-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/founder-economy-v2-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/founder-economy-manifest-v2.txt"
)
add_test(
  NAME founder-economy-v2-manifest
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_economy_v2_manifest_test.py"
)
add_test(
  NAME founder-economy-v2-errors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_economy_v2_errors_test.py"
)
add_test(
  NAME founder-economy-v2-simulator-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/founder-economy-v2-vectors/verify_simulator.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/founder-economy-simulator-v2.txt"
)
add_test(
  NAME founder-economy-v2-model
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_economy_v2_model_test.py"
)
add_test(
  NAME founder-economy-v2-transition-errors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_economy_v2_transition_errors_test.py"
)
add_test(
  NAME founder-economy-v2-scenarios
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_economy_v2_scenario_test.py"
)
add_test(
  NAME founder-economy-v3-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/founder-economy-v3-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/founder-economy-simulator-v3.txt"
)
add_test(
  NAME founder-economy-v3-schedule
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_economy_v3_schedule_test.py"
)
add_test(
  NAME founder-economy-v3-model
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_economy_v3_model_test.py"
)
add_test(
  NAME founder-economy-v3-errors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_economy_v3_errors_test.py"
)
add_test(
  NAME founder-economy-v3-scenarios
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_economy_v3_scenario_test.py"
)
add_test(
  NAME founder-economy-manifest-v3-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/founder-economy-manifest-v3-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/founder-economy-manifest-v3.txt"
)
add_test(
  NAME founder-economy-manifest-v3
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_economy_manifest_v3_test.py"
)
add_test(
  NAME cycle-boundary-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/cycle-boundary-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/cycle-boundary-v1.txt"
)
add_test(
  NAME cycle-boundary-grid
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/cycle_boundary_grid_test.py"
)
add_test(
  NAME cycle-boundary-model
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/cycle_boundary_model_test.py"
)
add_test(
  NAME uptime-measurement-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/uptime-measurement-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/uptime-measurement-v1.txt"
)
add_test(
  NAME uptime-measurement-slots
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/uptime_measurement_slots_test.py"
)
add_test(
  NAME uptime-measurement-model
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/uptime_measurement_model_test.py"
)
add_test(
  NAME uptime-measurement-economy-join
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/uptime_measurement_economy_test.py"
)
add_test(
  NAME economy-transition-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/economy-transition-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v2.txt"
)
add_test(
  NAME economy-transition-envelope
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_envelope_test.py"
)
add_test(
  NAME economy-transition-state
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_state_test.py"
)
add_test(
  NAME economy-transition-codes
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_codes_test.py"
)
add_test(
  NAME economy-transition-cycle
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_cycle_test.py"
)
add_test(
  NAME economy-transition-v3-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/economy-transition-v3-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v3.txt"
)
add_test(
  NAME economy-transition-v3-envelope
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v3_envelope_test.py"
)
add_test(
  NAME economy-transition-v3-state
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v3_state_test.py"
)
add_test(
  NAME economy-transition-v3-codes
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v3_codes_test.py"
)
add_test(
  NAME economy-transition-v3-settlement
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v3_settlement_test.py"
)
add_test(
  NAME economy-transition-v4-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/economy-transition-v4-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v4.txt"
)
add_test(
  NAME economy-transition-v4-envelope
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v4_envelope_test.py"
)
add_test(
  NAME economy-transition-v4-state
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v4_state_test.py"
)
add_test(
  NAME economy-transition-v4-codes
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v4_codes_test.py"
)
add_test(
  NAME economy-transition-v4-identity
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v4_identity_test.py"
)
add_test(
  NAME economy-transition-v5-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/economy-transition-v5-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v5.txt"
)
add_test(
  NAME economy-transition-v5-envelope
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v5_envelope_test.py"
)
add_test(
  NAME economy-transition-v5-state
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v5_state_test.py"
)
add_test(
  NAME economy-transition-v5-identity
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v5_identity_test.py"
)
add_test(
  NAME economy-transition-v5-carryover
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v5_carryover_test.py"
)
add_test(
  NAME economy-transition-v6-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/economy-transition-v6-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v6.txt"
)
add_test(
  NAME economy-transition-v6-envelope
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v6_envelope_test.py"
)
add_test(
  NAME economy-transition-v6-state
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v6_state_test.py"
)
add_test(
  NAME economy-transition-v6-identity
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v6_identity_test.py"
)
add_test(
  NAME economy-transition-v6-verified-user
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v6_verified_user_test.py"
)
add_test(
  NAME economy-transition-v6-execution-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/economy-transition-v6-execution-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v6-execution.txt"
)
add_test(
  NAME economy-transition-v6-execution
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v6_execution_test.py"
)
add_test(
  NAME economy-transition-v6-block
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v6_block_test.py"
)
add_test(
  NAME economy-transition-v7-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/economy-transition-v7-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v7.txt"
)
add_test(
  NAME economy-transition-v7-carryover
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v7_carryover_test.py"
)
add_test(
  NAME economy-transition-v7-state
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v7_state_test.py"
)
add_test(
  NAME economy-transition-v7-settlement
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v7_settlement_test.py"
)
add_test(
  NAME economy-transition-v7-execution
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v7_execution_test.py"
)
add_test(
  NAME economy-transition-v7-ledger
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v7_ledger_test.py"
)
add_test(
  NAME economy-transition-v7-block
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v7_block_test.py"
)
add_test(
  NAME version-seven-chain-fixture
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/integration/version_seven_chain_test.py"
    --libsodium
    "${PROTOCOL_STACK_SODIUM_SHARED_LIBRARY}"
)
add_test(
  NAME economy-transition-v7-execution-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/economy-transition-v7-execution-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v7-execution.txt"
)
add_test(
  NAME economy-transition-v8-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/economy-transition-v8-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v8.txt"
)
add_test(
  NAME economy-transition-v8-carryover
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v8_carryover_test.py"
)
add_test(
  NAME economy-transition-v8-execution
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v8_execution_test.py"
)
add_test(
  NAME economy-transition-v8-block
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economy_transition_v8_block_test.py"
)
add_test(
  NAME economy-transition-v8-execution-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/economy-transition-v8-execution-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-transition-v8-execution.txt"
)
add_test(
  NAME founder-seat-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/founder-seat-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/founder-seat-schedule-v1.txt"
)
add_test(
  NAME founder-seat-schedule
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_seat_schedule_test.py"
)
add_test(
  NAME founder-seat-sale
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_seat_sale_test.py"
)
add_test(
  NAME founder-seat-errors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/founder_seat_errors_test.py"
)
add_test(
  NAME revenue-routing-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/revenue-routing-vectors/verify.py"
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/revenue-routing-v1.txt"
)
add_test(
  NAME revenue-routing-split
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/revenue_routing_split_test.py"
)
add_test(
  NAME revenue-routing-model
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/revenue_routing_model_test.py"
)
add_test(
  NAME revenue-routing-errors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/revenue_routing_errors_test.py"
)
add_test(
  NAME escrow-payout-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/escrow-payout-vectors/verify.py"
    --version
    v1
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/escrow-payout-v1.txt"
)
add_test(
  NAME escrow-payout-v2-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/escrow-payout-vectors/verify.py"
    --version
    v2
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/escrow-payout-v2.txt"
)
add_test(
  NAME escrow-payout-v3-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/escrow-payout-vectors/verify.py"
    --version
    v3
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/escrow-payout-v3.txt"
)
add_test(
  NAME escrow-payout-model
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/escrow_payout_model_test.py"
)
add_test(
  NAME escrow-payout-errors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/escrow_payout_errors_test.py"
)
add_test(
  NAME escrow-payout-v2
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/escrow_payout_v2_test.py"
)
add_test(
  NAME escrow-payout-v3
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/escrow_payout_v3_test.py"
)
add_test(
  NAME scenario-suite-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/scenario-suite-vectors/verify.py"
    --version
    v1
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-scenario-suite-v1.txt"
)
add_test(
  NAME scenario-suite-v2-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/scenario-suite-vectors/verify.py"
    --version
    v2
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-scenario-suite-v2.txt"
)
add_test(
  NAME scenario-suite-v3-vectors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tools/scenario-suite-vectors/verify.py"
    --version
    v3
    --vectors
    "${PROJECT_SOURCE_DIR}/test-vectors/economy-scenario-suite-v3.txt"
)
add_test(
  NAME scenario-v2
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/scenario_v2_test.py"
)
add_test(
  NAME scenario-v3
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/scenario_v3_test.py"
)
add_test(
  NAME scenario-v3-properties
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/scenario_v3_property_test.py"
)
add_test(
  NAME scenario-multiyear
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/scenario_multiyear_test.py"
)
add_test(
  NAME scenario-market
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/scenario_market_test.py"
)
add_test(
  NAME scenario-properties
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/scenario_property_test.py"
)
add_test(
  NAME native-economy-model
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/native_economy_model_test.py"
)
add_test(
  NAME native-economy-errors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/native_economy_errors_test.py"
)
add_test(
  NAME native-economy-scenarios
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/native_economy_scenario_test.py"
)
add_test(
  NAME participation-model
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/participation_model_test.py"
)
add_test(
  NAME participation-errors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/participation_errors_test.py"
)
add_test(
  NAME participation-lifecycle
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/participation_lifecycle_test.py"
)
add_test(
  NAME participation-scenarios
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/participation_scenario_test.py"
)
add_test(
  NAME authority-model
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/authority_model_test.py"
)
add_test(
  NAME authority-errors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/authority_errors_test.py"
)
add_test(
  NAME authority-lifecycle
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/authority_lifecycle_test.py"
)
add_test(
  NAME authority-scenarios
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/authority_scenario_test.py"
)
add_test(
  NAME economic-stress-design
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economic_stress_design_test.py"
)
add_test(
  NAME economic-stress-model
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economic_stress_model_test.py"
)
add_test(
  NAME economic-stress-study
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economic_stress_study_test.py"
)
add_test(
  NAME economic-stress-errors
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economic_stress_errors_test.py"
)
add_test(
  NAME economic-envelope-design
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economic_envelope_design_test.py"
)
add_test(
  NAME economic-envelope-projection
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economic_envelope_projection_test.py"
)
add_test(
  NAME economic-envelope-study
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/economic_envelope_study_test.py"
)
add_test(
  NAME reward-distribution-design
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/reward_distribution_design_test.py"
)
add_test(
  NAME reward-distribution-model
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/reward_distribution_model_test.py"
)
add_test(
  NAME reward-distribution-study
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/reward_distribution_study_test.py"
)
add_test(
  NAME admission-cost-design
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/admission_cost_design_test.py"
)
add_test(
  NAME admission-cost-model
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/admission_cost_model_test.py"
)
add_test(
  NAME admission-cost-study
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/admission_cost_study_test.py"
)
add_test(
  NAME minimum-entitlement-design
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/minimum_entitlement_design_test.py"
)
add_test(
  NAME minimum-entitlement-model
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/minimum_entitlement_model_test.py"
)
add_test(
  NAME minimum-entitlement-study
  COMMAND
    "${Python3_EXECUTABLE}"
    "${PROJECT_SOURCE_DIR}/tests/simulation/minimum_entitlement_study_test.py"
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
# The multi-year scenarios run tens of thousands of events, and the economy
# simulator clones state per event, so give them room on a slow hosted runner.
set_tests_properties(
  scenario-suite-vectors
  scenario-multiyear
  scenario-market
  PROPERTIES
    TIMEOUT 600
)
# `ctest --parallel` runs the highest-cost entries first, and without a cost it
# runs them in registration order. The longest entries are registered late, so
# the run would finish with one long test and idle workers. These are the
# seconds measured in the `gcc-sanitizers` job of run 31495429227, which is a
# scheduling hint rather than a bound: a stale figure costs packing efficiency
# and never correctness, and a fresh checkout has no CTestCostData.txt to use
# instead.
set_tests_properties(economic-envelope-study PROPERTIES COST 92)
set_tests_properties(scenario-v2 PROPERTIES COST 50)
set_tests_properties(scenario-v3 PROPERTIES COST 46)
set_tests_properties(admission-cost-study PROPERTIES COST 43)
set_tests_properties(scenario-suite-v3-vectors PROPERTIES COST 40)
set_tests_properties(scenario-suite-v2-vectors PROPERTIES COST 40)
set_tests_properties(kernel-differential PROPERTIES COST 35)
set_tests_properties(scenario-suite-vectors PROPERTIES COST 32)
set_tests_properties(economic-stress-study PROPERTIES COST 30)
set_tests_properties(scenario-market PROPERTIES COST 29)
set_tests_properties(scenario-multiyear PROPERTIES COST 25)
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
  add_test(
    NAME economy-transition-v7-fuzz-smoke
    COMMAND
      economy_v7_fuzz
      -seed=824311
      -runs=512
      -max_len=512
      -len_control=0
  )
  add_test(
    NAME storage-snapshot-fuzz-smoke
    COMMAND
      storage_snapshot_fuzz
      -seed=824311
      -runs=512
      -max_len=4096
      -len_control=0
  )
  add_test(
    NAME storage-snapshot-v7-fuzz-smoke
    COMMAND
      storage_snapshot_v7_fuzz
      -seed=824311
      -runs=512
      -max_len=4096
      -len_control=0
  )
  add_test(
    NAME storage-archive-fuzz-smoke
    COMMAND
      storage_archive_fuzz
      -seed=824311
      -runs=512
      -max_len=16384
      -len_control=0
  )
  add_test(
    NAME application-wire-fuzz-smoke
    COMMAND
      application_wire_fuzz
      -seed=824311
      -runs=512
      -max_len=65536
      -len_control=0
  )
  set_tests_properties(
    kernel-admission-fuzz-smoke
    kernel-address-fuzz-smoke
    kernel-genesis-fuzz-smoke
    economy-transition-v7-fuzz-smoke
    storage-snapshot-fuzz-smoke
    storage-archive-fuzz-smoke
    application-wire-fuzz-smoke
    PROPERTIES
      LABELS fuzz
      TIMEOUT 60
  )
endif()
