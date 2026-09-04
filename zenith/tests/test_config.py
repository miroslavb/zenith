"""Harness configuration defaults."""
from __future__ import annotations

from pathlib import Path

from zenith_harness.config import HarnessConfig


def test_discover_defaults_to_four_parallel_nodes(
    monkeypatch,
    harness_home: Path,
) -> None:
    monkeypatch.setenv("ZENITH_HOME", str(harness_home))
    monkeypatch.delenv("ZENITH_PROJECTS_DIR", raising=False)
    monkeypatch.delenv("ZENITH_PROJECT_BUCKET_DIR", raising=False)
    monkeypatch.delenv("ZENITH_MAX_PARALLEL_NODES", raising=False)

    config = HarnessConfig.discover()

    assert config.max_parallel_nodes == 4
    assert config.resolved_codex_subscription_home == harness_home / "codex-subscription"
    assert config.api_grants_file is None


def test_discover_explicit_codex_auth_paths(monkeypatch, harness_home: Path) -> None:
    subscription_home = harness_home / "subscription-auth"
    grants_file = harness_home / "grants.json"
    monkeypatch.setenv("ZENITH_HOME", str(harness_home))
    monkeypatch.setenv("ZENITH_CODEX_SUBSCRIPTION_HOME", str(subscription_home))
    monkeypatch.setenv("ZENITH_API_GRANTS_FILE", str(grants_file))

    config = HarnessConfig.discover()

    assert config.resolved_codex_subscription_home == subscription_home
    assert config.api_grants_file == grants_file


def test_discover_explicit_one_uses_serial_parallelism(
    monkeypatch,
    harness_home: Path,
) -> None:
    monkeypatch.setenv("ZENITH_HOME", str(harness_home))
    monkeypatch.delenv("ZENITH_PROJECT_BUCKET_DIR", raising=False)
    monkeypatch.setenv("ZENITH_MAX_PARALLEL_NODES", "1")

    config = HarnessConfig.discover()

    assert config.max_parallel_nodes == 1


def test_discover_invalid_parallelism_falls_back_to_default(
    monkeypatch,
    harness_home: Path,
) -> None:
    monkeypatch.setenv("ZENITH_HOME", str(harness_home))
    monkeypatch.delenv("ZENITH_PROJECT_BUCKET_DIR", raising=False)
    monkeypatch.setenv("ZENITH_MAX_PARALLEL_NODES", "not-an-int")

    config = HarnessConfig.discover()

    assert config.max_parallel_nodes == 4
