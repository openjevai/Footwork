"""OpenJEV provider selection (additive; TypeSafe stays the default).

Jev is built by TypeSafe (https://typesafe.ai). OpenJEV (https://openjev.sh) is a
free community gateway to the same Jev model. This module picks which endpoint
to talk to without changing TypeSafe behaviour for anyone who has a TypeSafe
key.

Selection rule (implemented in the project's own style):
  1. ``JEV_PROVIDER=openjev`` wins explicitly.
  2. Otherwise, if ``TYPESAFE_API_KEY`` is set -> TypeSafe (unchanged default).
  3. Otherwise, if only ``OPENJEV_API_KEY`` is set -> OpenJEV.
Anyone with a TypeSafe key sees zero behaviour change.

The TypeSafe Python SDK (``typesafe_sdk``) reads ``TYPESAFE_API_KEY`` and
``TYPESAFE_BASE_URL`` from the environment and appends ``/v1/systemone`` to the
base URL. ``apply_provider_env`` points those two variables at OpenJEV when it
is selected, so the existing ``AsyncTypeSafeClient()`` call sites work unchanged.
``jev_model`` swaps the model id: OpenJEV serves ``openjev`` where TypeSafe
serves the pinned ``jev-1.13.0``.

OpenJEV signals overload with HTTP 503 (TypeSafe uses 529); both are 5xx and are
already retried by the existing ``RetryPolicy(respect_retry_after=True)`` path.
"""

from __future__ import annotations

import os

#: OpenJEV gateway host. The SDK appends ``/v1/systemone``.
OPENJEV_BASE_URL = "https://api.openjev.sh"

#: Model id the OpenJEV gateway serves.
OPENJEV_MODEL = "openjev"

_resolved: str | None = None


def jev_provider() -> str:
    """``"openjev"`` or ``"typesafe"`` per the selection rule.

    The result is cached on the first call so that ``apply_provider_env`` mapping
    ``TYPESAFE_API_KEY`` onto the OpenJEV key cannot flip the auto-detection.
    """
    global _resolved
    if _resolved is not None:
        return _resolved
    explicit = os.environ.get("JEV_PROVIDER", "").strip().lower()
    if explicit == "openjev":
        _resolved = "openjev"
    elif explicit == "typesafe":
        _resolved = "typesafe"
    elif os.environ.get("TYPESAFE_API_KEY"):
        _resolved = "typesafe"
    elif os.environ.get("OPENJEV_API_KEY"):
        _resolved = "openjev"
    else:
        _resolved = "typesafe"
    return _resolved


def jev_model(typesafe_default: str) -> str:
    """Model id to send: ``openjev`` for OpenJEV, otherwise the TypeSafe default."""
    return OPENJEV_MODEL if jev_provider() == "openjev" else typesafe_default


def apply_provider_env() -> bool:
    """Map the selected provider onto the env vars the TypeSafe SDK reads.

    TypeSafe (default): no-op. OpenJEV: set ``TYPESAFE_BASE_URL`` and point
    ``TYPESAFE_API_KEY`` at the OpenJEV key, so unmodified ``AsyncTypeSafeClient()``
    call sites hit the community gateway. Returns whether a Jev key is available.
    """
    if jev_provider() == "openjev":
        key = os.environ.get("OPENJEV_API_KEY")
        if key:
            os.environ.setdefault("TYPESAFE_BASE_URL", OPENJEV_BASE_URL)
            os.environ["TYPESAFE_API_KEY"] = key
            return True
        return False
    return bool(os.environ.get("TYPESAFE_API_KEY"))


def make_jev_client():
    """Construct the System One client for the selected provider.

    TypeSafe: ``AsyncTypeSafeClient()`` unchanged. OpenJEV: explicit
    ``api_key``/``base_url`` (use this for entry points that do not call
    ``load_keys`` first).
    """
    from typesafe_sdk import AsyncTypeSafeClient

    if jev_provider() == "openjev":
        return AsyncTypeSafeClient(
            api_key=os.environ["OPENJEV_API_KEY"],
            base_url=OPENJEV_BASE_URL,
        )
    return AsyncTypeSafeClient()


def has_jev_key(keys: dict[str, bool] | None = None) -> bool:
    """True if a Jev key (TypeSafe or OpenJEV) is available."""
    if keys is not None:
        return bool(keys.get("TYPESAFE_API_KEY") or keys.get("OPENJEV_API_KEY"))
    return bool(os.environ.get("TYPESAFE_API_KEY") or os.environ.get("OPENJEV_API_KEY"))
