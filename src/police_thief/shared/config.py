"""Configuration manager: the single way any layer reads settings.

Two sources, deliberately asymmetric (rulebook Appendix B):

* ``config/game.json`` - the **signed shared contract**. Loaded byte-for-byte
  identically by both peers, hashed into ``config_sha256`` and exchanged during
  negotiation; play is refused on mismatch. All game physics come from here.
* ``config/<role>/game.toml`` - **private per-peer** settings (port, opponent
  URL, strategy class, verbal-layer provider, email). Never crosses the network.

The overlay rule is enforced structurally: physics is exposed only through
:attr:`ConfigManager.contract`, so a private file can never weaken a signed
condition even if it repeats one of its keys.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..constants import ROLES
from .config_io import ConfigError, read_json, read_toml, sha256_of
from .contract import build_contract
from .interop_profile import InteropProfile, resolve
from .schema import GameContract
from .version import check_config_version, check_schema_version

SHARED_FILE = "game.json"
PRIVATE_FILE = "game.toml"


class ConfigManager:
    """Typed access to the shared contract and the private per-peer settings."""

    def __init__(self, raw_shared: dict[str, Any], raw_private: dict[str, Any], role: str) -> None:
        """Validate both sources and build the typed contract.

        Args:
            raw_shared: parsed shared contract mapping.
            raw_private: parsed private per-peer mapping.
            role: ``"police"`` or ``"thief"``.

        Raises:
            ConfigError: on an unknown role or a malformed contract.
            ConfigVersionError: on a missing or incompatible version.
        """
        if role not in ROLES:
            raise ConfigError(f"unknown role {role!r}; expected one of {ROLES}")
        check_config_version(raw_shared, label="config/game.json")
        check_config_version(raw_private, label=f"config/{role}/game.toml")
        check_schema_version(raw_shared)
        self._role = role
        self._raw_shared = raw_shared
        self._raw_private = raw_private
        self._contract = build_contract(raw_shared)

    @classmethod
    def load(cls, role: str, config_dir: str | Path = "config") -> ConfigManager:
        """Load both configuration files for ``role`` from ``config_dir``.

        The per-role sub-directory keeps the cop's and the thief's settings
        physically separate, as the mandatory separation rule requires.
        """
        base = Path(config_dir)
        raw_shared = read_json(base / SHARED_FILE)
        raw_private = read_toml(base / role / PRIVATE_FILE)
        return cls(raw_shared, raw_private, role)

    @property
    def role(self) -> str:
        """The role this peer plays."""
        return self._role

    @property
    def contract(self) -> GameContract:
        """The typed, signed game contract - the only source of game physics."""
        return self._contract

    @property
    def interop(self) -> InteropProfile:
        """The dialect this peer speaks, from the private ``[interop]`` section.

        Private rather than signed on purpose: it is not an Appendix B field, so
        putting it in the shared contract would change the hash every correct
        peer computes. It is declared beside the terms at the handshake instead,
        where a disagreement refuses (:mod:`shared.interop_profile`).
        """
        return resolve(
            self.private_value("interop", "profile"),
            self.private_value("interop", "tie_award"),
            self.private_value("interop", "settlement_scope"),
        )

    @property
    def raw_contract(self) -> dict[str, Any]:
        """A copy of the raw shared mapping, as hashed and exchanged."""
        return dict(self._raw_shared)

    @property
    def config_sha256(self) -> str:
        """Canonical SHA-256 of the shared contract, exchanged at negotiation.

        Both peers must compute the same digest; any difference proves the
        contracts are not identical and the game must not start.
        """
        return sha256_of(self._raw_shared)

    def private(self, section: str) -> dict[str, Any]:
        """Return a private TOML section, or an empty mapping when absent.

        Optional sections (``[strategy]``, ``[trash_talk]``) may legitimately be
        missing, in which case the caller falls back to its built-in default.
        """
        value = self._raw_private.get(section, {})
        if not isinstance(value, dict):
            raise ConfigError(f"private config: section {section!r} must be a table")
        return dict(value)

    def private_value(self, section: str, key: str, default: Any = None) -> Any:
        """Return a single private setting, or ``default`` when it is absent."""
        return self.private(section).get(key, default)
