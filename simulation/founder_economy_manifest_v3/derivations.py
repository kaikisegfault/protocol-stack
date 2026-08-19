"""Version three's binding of the shared checked-arithmetic derivation stage.

The stage is exercised directly as well as through the loader, because the
ordered loader reaches it only for a manifest that already matches the fixed
contract table and is therefore arithmetically correct by construction.
"""

from __future__ import annotations

from typing import Any

from . import contract as c
from ..founder_economy_manifest import derivations as shared
from ..founder_economy_manifest.derivations import DerivationError

__all__ = ["DerivationError", "check_derivations"]


def check_derivations(root: dict[str, Any]) -> None:
    shared.check_derivations(root, c)
