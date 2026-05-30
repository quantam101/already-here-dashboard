"""Unit tests for the 2-of-2 dual-actor approval flow on L5 (critical) gates.

These tests bypass HTTP and exercise `services.governance_service` directly
with a minimal in-memory Mongo-shaped stub. This lets us toggle
`DUAL_ACTOR_APPROVAL` per-test without restarting the backend.
"""
import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import governance_service as gov  # noqa: E402


# --------------------------------------------------------------------------
# Minimal async in-memory shim — implements the 4 methods governance uses.
# --------------------------------------------------------------------------
class _Collection:
    def __init__(self):
        self.rows: list[dict] = []

    async def insert_one(self, doc):
        self.rows.append(doc)
        return type("R", (), {"inserted_id": doc.get("id")})

    async def find_one(self, q, _proj=None):
        for r in self.rows:
            if all(r.get(k) == v for k, v in q.items()):
                return dict(r)
        return None

    async def update_one(self, q, ops):
        for r in self.rows:
            if all(r.get(k) == v for k, v in q.items()):
                for k, v in (ops.get("$set") or {}).items():
                    r[k] = v
                return type("R", (), {"matched_count": 1, "modified_count": 1})
        return type("R", (), {"matched_count": 0, "modified_count": 0})


class _DB:
    def __init__(self):
        self._cols: dict[str, _Collection] = {}

    def __getitem__(self, name):
        if name not in self._cols:
            self._cols[name] = _Collection()
        return self._cols[name]


@pytest.fixture
def db():
    return _DB()


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


# --------------------------------------------------------------------------
# Single-actor flow (default — DUAL_ACTOR_APPROVAL unset)
# --------------------------------------------------------------------------

def test_single_actor_approves_immediately(db, monkeypatch):
    monkeypatch.delenv("DUAL_ACTOR_APPROVAL", raising=False)
    row = _run(gov.create_approval_row(db, "payment_modification", {"route": "test"}))
    assert row["required_decisions"] == 1
    assert row["status"] == "pending"
    out = _run(gov.decide_approval(db, row["id"], approve=True, actor="alice", note="single"))
    assert out["status"] == "approved"
    assert len(out["decisions"]) == 1


# --------------------------------------------------------------------------
# 2-of-2 flow — DUAL_ACTOR_APPROVAL=true on critical gates only
# --------------------------------------------------------------------------

def test_critical_gate_requires_two_distinct_actors(db, monkeypatch):
    monkeypatch.setenv("DUAL_ACTOR_APPROVAL", "true")
    row = _run(gov.create_approval_row(db, "payment_modification", {"route": "test"}))
    assert row["required_decisions"] == 2

    # first approver -> still pending
    out1 = _run(gov.decide_approval(db, row["id"], approve=True, actor="alice", note="first"))
    assert out1["status"] == "pending"
    assert len(out1["decisions"]) == 1

    # same actor again -> idempotent, still pending, no duplicate
    out2 = _run(gov.decide_approval(db, row["id"], approve=True, actor="alice", note="duplicate"))
    assert out2["status"] == "pending"
    assert len([d for d in out2["decisions"] if d["actor"] == "alice" and d["approve"]]) == 1

    # second distinct actor -> approved
    out3 = _run(gov.decide_approval(db, row["id"], approve=True, actor="bob", note="second"))
    assert out3["status"] == "approved"
    distinct = {d["actor"] for d in out3["decisions"] if d["approve"]}
    assert distinct == {"alice", "bob"}


def test_high_severity_gate_stays_single_actor_even_with_flag(db, monkeypatch):
    """`mass_outreach` is severity=high (not critical) — dual-actor MUST NOT apply."""
    monkeypatch.setenv("DUAL_ACTOR_APPROVAL", "true")
    row = _run(gov.create_approval_row(db, "mass_outreach", {"route": "test"}))
    assert row["required_decisions"] == 1
    out = _run(gov.decide_approval(db, row["id"], approve=True, actor="alice"))
    assert out["status"] == "approved"


def test_any_single_reject_finalizes_rejected(db, monkeypatch):
    monkeypatch.setenv("DUAL_ACTOR_APPROVAL", "true")
    row = _run(gov.create_approval_row(db, "payment_modification", {"route": "test"}))
    _run(gov.decide_approval(db, row["id"], approve=True, actor="alice", note="lgtm"))
    out = _run(gov.decide_approval(db, row["id"], approve=False, actor="bob", note="vetoed"))
    assert out["status"] == "rejected"
    assert out["decided_by"] == "bob"
    # further decisions are no-ops once final
    out2 = _run(gov.decide_approval(db, row["id"], approve=True, actor="carol"))
    assert out2["status"] == "rejected"


def test_unknown_approval_returns_empty(db):
    out = _run(gov.decide_approval(db, "appr-does-not-exist", approve=True, actor="x"))
    assert out == {}
