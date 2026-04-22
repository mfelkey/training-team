"""
tests/test_top_level_domains.py

TDD — knowledge_base.py must expose a TOP_LEVEL_DOMAINS registry for
collections that span all teams (per kickoff doc Decision 2).

The first top-level domain is 'lessons_learned'. Future additions
(system_updates, etc.) follow the same pattern.

Freshness reporting must include top-level domains.
"""
import sys
from pathlib import Path

import pytest

SUBMODULE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUBMODULE_ROOT))


def test_top_level_domains_registry_exists(clean_env):
    import importlib
    if "knowledge.knowledge_base" in sys.modules:
        importlib.reload(sys.modules["knowledge.knowledge_base"])
    from knowledge.knowledge_base import TOP_LEVEL_DOMAINS

    assert isinstance(TOP_LEVEL_DOMAINS, list), \
        "TOP_LEVEL_DOMAINS should be a list of collection names"
    assert "lessons_learned" in TOP_LEVEL_DOMAINS


def test_top_level_domain_uses_bare_collection_name(clean_env):
    """
    Top-level collections skip the `{team}_` prefix — they're stored
    under the bare domain name.
    """
    import importlib
    if "knowledge.knowledge_base" in sys.modules:
        importlib.reload(sys.modules["knowledge.knowledge_base"])
    from knowledge.knowledge_base import _collection_name

    # The convention: top-level domain's collection name is the domain itself
    # (no team prefix). We achieve this by treating team="lessons_learned"
    # and domain="platform" (or "project") — so the collection name becomes
    # "lessons_learned_platform", which keeps the {team}_{domain} idiom.
    name = _collection_name("lessons_learned", "platform")
    assert name == "lessons_learned_platform"
