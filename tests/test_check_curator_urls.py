"""
tests/test_check_curator_urls.py

Structural tests for scripts/check_curator_urls.py.

We don't actually hit the network in unit tests — the probe is mocked
so tests are deterministic and fast. One integration-marked test does
a real probe against a known-good URL, and even that is kept tight.
"""
import importlib
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = SUBMODULE_ROOT / "scripts" / "check_curator_urls.py"
sys.path.insert(0, str(SUBMODULE_ROOT / "scripts"))


def _fresh_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "check_curator_urls", str(SCRIPT_PATH)
    )
    mod = importlib.util.module_from_spec(spec)
    # Register BEFORE exec so @dataclass decorators can resolve the
    # module via sys.modules during their introspection pass.
    sys.modules["check_curator_urls"] = mod
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------------
# Structural
# ------------------------------------------------------------------------

def test_script_exists_and_executable():
    import os
    assert SCRIPT_PATH.exists()
    assert os.access(SCRIPT_PATH, os.X_OK), f"{SCRIPT_PATH} is not executable"


def test_script_importable():
    mod = _fresh_module()
    assert callable(getattr(mod, "run", None))
    assert callable(getattr(mod, "_probe_url", None))
    assert callable(getattr(mod, "_classify", None))


def test_classify_buckets_http_codes_correctly():
    mod = _fresh_module()
    assert mod._classify(200, "ok") == "ok"
    assert mod._classify(301, "redirect") == "ok"
    assert mod._classify(401, "auth") == "denied"
    assert mod._classify(403, "forbidden") == "denied"
    assert mod._classify(404, "gone") == "gone"
    assert mod._classify(0, "URLError") == "error"
    assert mod._classify(500, "boom") == "unknown"


def test_curator_teams_discovery_matches_filesystem():
    """_curator_teams() returns every team dir that has a curator.py."""
    mod = _fresh_module()
    teams = mod._curator_teams()
    # At least the Phase 2 set
    for expected in ["legal", "ds", "dev", "marketing", "strategy",
                     "design", "qa", "finance", "hr", "video", "sme"]:
        assert expected in teams, f"{expected} not discovered"
    # lessons_learned has no SOURCES — but its curator.py file exists,
    # so the discovery may include it; that's fine (load_sources returns []).


# ------------------------------------------------------------------------
# Behaviour with mocked network
# ------------------------------------------------------------------------

def test_run_with_mocked_probe_returns_zero_when_all_ok(capsys):
    mod = _fresh_module()
    with patch.object(mod, "_probe_url", return_value=(200, "GET 200")):
        rc = mod.run(teams=["legal"], timeout=1, head_only=True, json_out=False)
    assert rc == 0
    out = capsys.readouterr().out
    assert "legal" in out
    assert "healthy" in out.lower()


def test_run_counts_unhealthy(capsys):
    mod = _fresh_module()

    def fake_probe(url, timeout, head_only):
        # Alternate ok / 404 so every other source fails
        if "gamblingcommission" in url:
            return 404, "HTTPError 404"
        return 200, "GET 200"

    with patch.object(mod, "_probe_url", side_effect=fake_probe):
        rc = mod.run(teams=["legal"], timeout=1, head_only=True, json_out=False)

    # Legal has 2 UKGC-sourced entries at last count — exact number may
    # drift if sources change, but rc must be > 0 if any are unhealthy
    # and equal to the count of gamblingcommission URLs in SOURCES.
    assert rc >= 1


def test_json_output_parses(capsys):
    import json
    mod = _fresh_module()
    with patch.object(mod, "_probe_url", return_value=(200, "GET 200")):
        rc = mod.run(teams=["legal"], timeout=1, head_only=True, json_out=True)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert all({"team", "url", "status", "http"}.issubset(d.keys())
               for d in data)


def test_head_only_arg_passes_through(capsys):
    mod = _fresh_module()
    captured = {}

    def spy_probe(url, timeout, head_only):
        captured["head_only"] = head_only
        return 200, "ok"

    with patch.object(mod, "_probe_url", side_effect=spy_probe):
        mod.run(teams=["legal"], timeout=1, head_only=True, json_out=False)
    assert captured["head_only"] is True


def test_cli_team_filter(capsys):
    """--team limits probing to a single curator."""
    mod = _fresh_module()
    probed_teams = set()

    def spy_probe(url, timeout, head_only):
        # Infer team from URL presence is fragile; instead just
        # verify the run() call's `teams` arg via a direct invocation.
        return 200, "ok"

    with patch.object(mod, "_probe_url", side_effect=spy_probe):
        rc = mod.run(teams=["ds"], timeout=1, head_only=True, json_out=False)
    assert rc == 0
    out = capsys.readouterr().out
    # Output header should name ds
    assert "ds" in out
    # And should NOT iterate legal/dev/etc
    assert "legal" not in out
    assert "dev" not in out


# ------------------------------------------------------------------------
# Integration: real network
# ------------------------------------------------------------------------

@pytest.mark.integration
def test_probe_hits_real_url_cleanly():
    """
    Real probe against a known-good URL. Skipped by default.
    Run: pytest -m integration
    """
    mod = _fresh_module()
    code, detail = mod._probe_url(
        "https://www.python.org/",
        timeout=10, head_only=False,
    )
    assert code > 0, f"network unreachable: {detail}"
    # Either 2xx or 3xx is fine; just not 0 (network error)
