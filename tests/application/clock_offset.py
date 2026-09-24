"""Moving one application process's real-time clock from outside it.

`libprotocol-clock-offset.so` (`clock_offset_shim.cpp`) is loaded with
`LD_PRELOAD` and adds a signed number of milliseconds to every
`CLOCK_REALTIME` reading the process takes. It reads the figure from a file on
every call, so a test moves the clock of a running process by rewriting the file.
A missing or malformed file is an unreadable clock rather than the real one.

The binary under test is the one that ships. ADR 0091 records why the skew is
applied here rather than through an option on the process.
"""

from __future__ import annotations

import os
import pathlib

OFFSET_FILE_VARIABLE = "PROTOCOL_STACK_CLOCK_OFFSET_FILE"

# GCC's dynamic ASan runtime refuses to start behind any preloaded library. The
# shim defines only `clock_gettime`, allocates nothing, and reaches the kernel
# through raw system calls, so the load order that check protects is not one it
# can disturb. Clang's static runtime and unsanitized builds ignore the option.
ASAN_LINK_ORDER_OPTION = "verify_asan_link_order=0"


def environment(shim: pathlib.Path, offset_file: pathlib.Path) -> dict[str, str]:
    """The variables one process needs in order to read its clock through the shim."""
    if not shim.is_absolute() or not offset_file.is_absolute():
        raise RuntimeError("the shim and its offset file must be absolute paths")
    inherited = os.environ.get("ASAN_OPTIONS", "")
    return {
        "LD_PRELOAD": str(shim),
        OFFSET_FILE_VARIABLE: str(offset_file),
        "ASAN_OPTIONS": (
            f"{inherited}:{ASAN_LINK_ORDER_OPTION}"
            if inherited
            else ASAN_LINK_ORDER_OPTION
        ),
    }


def set_offset(offset_file: pathlib.Path, millis: int) -> None:
    """Move the clock to `millis` from real time.

    The file is replaced whole, so no read sees half of one figure and half of
    another, and no read finds it missing.
    """
    staged = offset_file.with_name(offset_file.name + ".next")
    staged.write_text(f"{millis:+d}\n", encoding="ascii")
    os.replace(staged, offset_file)


def make_unreadable(offset_file: pathlib.Path) -> None:
    """Replace the figure with one the shim refuses, which is an unreadable clock."""
    staged = offset_file.with_name(offset_file.name + ".next")
    staged.write_text("unreadable\n", encoding="ascii")
    os.replace(staged, offset_file)
