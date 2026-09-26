# OpenJEV support

This fork adds **optional** [OpenJEV](https://openjev.sh) support alongside the original
[TypeSafe](https://typesafe.ai) Jev integration. OpenJEV is a free community gateway to the same
Jev model. TypeSafe stays the default; anyone with a `TYPESAFE_API_KEY` sees zero behaviour change.

## What was added

- `jevdual/python/jevdual/provider.py` (new) — provider selection: `jev_provider()`,
  `jev_model()`, `apply_provider_env()`, `make_jev_client()`, `has_jev_key()`.
- `jevdual/python/jevdual/keys.py` — loads `OPENJEV_API_KEY` from the key dir and calls
  `apply_provider_env()` so the existing `AsyncTypeSafeClient()` call sites hit OpenJEV when
  it is selected (no call site changed).
- `jevdual/python/jevdual/policy.py`, `verify.py`, `evidence.py` — the `model` default for
  `JevPolicy`, `Verifier` and `EvidenceSelector` now resolves to `openjev` when OpenJEV is
  selected (TypeSafe's pinned `jev-1.13.0` otherwise).
- `jevdual/scripts/policy_live_check.py` — gate and client use `has_jev_key()` / `make_jev_client()`
  (this script did not call `load_keys`).
- `README.md` and `jevdual/README.md` — short OpenJEV notes (TypeSafe credited first).

No TypeSafe code was removed or re-defaulted. The LICENSE and credits are untouched.

## Provider selection rule

1. `JEV_PROVIDER=openjev` wins explicitly.
2. Otherwise, if `TYPESAFE_API_KEY` is set → TypeSafe (unchanged default).
3. Otherwise, if only `OPENJEV_API_KEY` is set → OpenJEV.

Mapping (OpenJEV selected): the TypeSafe SDK reads `TYPESAFE_BASE_URL` and `TYPESAFE_API_KEY`
from the environment and appends `/v1/systemone`. `apply_provider_env()` sets
`TYPESAFE_BASE_URL=https://api.openjev.sh` and points `TYPESAFE_API_KEY` at the OpenJEV key,
so the unmodified `AsyncTypeSafeClient()` calls hit `https://api.openjev.sh/v1/systemone`
with model `openjev`. OpenJEV signals overload with HTTP 503 (TypeSafe uses 529); both are 5xx
and are already retried by the existing `RetryPolicy(respect_retry_after=True)` path.

## How to configure

Place an `OPENJEV_API_KEY` file under `~/.config/jevdual` (materialized by `keys.py`), or export
`OPENJEV_API_KEY` in your environment. Get a key from https://openjev.sh/dashboard. To force
OpenJEV even when a TypeSafe key is also present, set `JEV_PROVIDER=openjev`.

## How it was verified

- A live `POST https://api.openjev.sh/v1/systemone` request with model `openjev`, `state: "ping"`
  and one noul question returned HTTP 200 (run by the porter, not the repo's own code).
- `grep` confirmed no hardcoded `api.typesafe.ai` default was introduced: the only TypeSafe
  endpoint is the SDK's own default, active when TypeSafe is selected.

## Upstream

Original project: https://github.com/Tom-R-Main/Footwork by @Tom-R-Main.
