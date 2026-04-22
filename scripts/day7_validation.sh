#!/usr/bin/env bash
#
# scripts/day7_validation.sh
#
# End-to-end Phase 2 validation — exercises the full training-team
# stack sequentially and prints PASS/FAIL per stage. Intended for
# one-shot validation after a full Phase 2 rollout or before a
# release cut.
#
# Run from the training-team submodule root:
#
#     bash scripts/day7_validation.sh
#
# Stages:
#   1. Unit tests pass
#   2. Integration tests pass (requires working ChromaDB embedder)
#   3. training_flow.py --mode status runs cleanly
#   4. LL curator parses docs/LESSONS_LEARNED.md successfully
#   5. approve_candidates.py --list works against fresh candidates/
#   6. Freshness report includes teams + top-level + (if registered) projects
#
# Exits 0 if every stage passed, 1 otherwise.
#
# Use --skip-integration to skip stage 2 in environments without a
# working ChromaDB embedder (e.g. sandboxes with blocked ONNX download).

set -uo pipefail

cd "$(dirname "$0")/.."
SUBMODULE_ROOT="$PWD"

# Prefer python3.11 (PP standard per the agent system manual), fall back
# to python3 for sandboxed/CI environments that only have the system python.
if command -v python3.11 >/dev/null 2>&1; then
    PY=python3.11
else
    PY=python3
fi

SKIP_INTEGRATION=0
for arg in "$@"; do
    case "$arg" in
        --skip-integration) SKIP_INTEGRATION=1 ;;
    esac
done

TOTAL=0
PASSED=0
FAILED=0
FAILED_STAGES=()

_stage() {
    local name="$1"
    shift
    TOTAL=$((TOTAL + 1))
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "STAGE $TOTAL: $name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if "$@"; then
        echo "✅ STAGE $TOTAL PASSED: $name"
        PASSED=$((PASSED + 1))
    else
        echo "❌ STAGE $TOTAL FAILED: $name"
        FAILED=$((FAILED + 1))
        FAILED_STAGES+=("$TOTAL: $name")
    fi
}

# ────────────────────────────────────────────────────────────────
_stage "Unit tests" \
    $PY -m pytest tests/ -q

if [ "$SKIP_INTEGRATION" -eq 0 ]; then
    _stage "Integration tests (real ChromaDB)" \
        $PY -m pytest tests/ -m integration -q
else
    echo ""
    echo "⏭️  SKIPPED: Integration tests (--skip-integration flag)"
fi

_stage "training_flow.py --mode status" \
    $PY flows/training_flow.py --mode status

_stage "LL curator parses real platform file" \
    $PY -c "
import sys
sys.path.insert(0, '$SUBMODULE_ROOT')
from pathlib import Path
from agents.curators.lessons_learned.parser import parse_ll_file
ll = Path('$SUBMODULE_ROOT').parent.parent / 'docs' / 'LESSONS_LEARNED.md'
entries = parse_ll_file(ll)
assert len(entries) >= 1, f'no LL entries parsed from {ll}'
ids = [e['ll_id'] for e in entries]
print(f'Parsed {len(entries)} entries: {ids}')
"

_stage "approve_candidates.py --list works on empty dir" \
    bash -c "
TMP=\$(mktemp -d)
CANDIDATES_DIR=\"\$TMP/cand\" KNOWLEDGE_DB_PATH=\"\$TMP/db\" \
    $PY scripts/approve_candidates.py --list
rc=\$?
rm -rf \$TMP
exit \$rc
"

_stage "Freshness report includes all 3 collection layers" \
    $PY -c "
import os, sys, tempfile
tmp = tempfile.mkdtemp()
os.environ['KNOWLEDGE_DB_PATH'] = os.path.join(tmp, 'db')
os.environ['CANDIDATES_DIR'] = os.path.join(tmp, 'cand')
sys.path.insert(0, '$SUBMODULE_ROOT')
import importlib, knowledge.knowledge_base as kb
importlib.reload(kb)
# Register a project to exercise the 3-layer report
kb.register_project('validation_project')
report = kb.get_freshness_report()
# Team presence
assert 'legal' in report, 'team collection missing'
# Project presence
assert 'validation_project' in report, 'project collection missing'
print(f'Freshness report covers {len(report)} scopes')
print(f'  Teams: {len([k for k in report if k in kb.TEAM_DOMAINS])}')
print(f'  Top-level: {sum(1 for k in report if k in kb.TOP_LEVEL_DOMAINS)}')
print(f'  Projects: {sum(1 for k in report if k in kb.PROJECT_DOMAINS)}')
import shutil; shutil.rmtree(tmp)
"

# ────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Total stages: $TOTAL"
echo "Passed:       $PASSED"
echo "Failed:       $FAILED"
if [ "$FAILED" -gt 0 ]; then
    echo ""
    echo "Failed stages:"
    for s in "${FAILED_STAGES[@]}"; do
        echo "  - $s"
    done
    exit 1
fi

echo ""
echo "🎉 Phase 2 validation: all stages passed"
exit 0
