"""SQLite shim that exposes a Motor-compatible async API.

Each "Mongo collection" maps to a SQLite table with schema:
    CREATE TABLE <name> (id TEXT PRIMARY KEY, doc TEXT NOT NULL)
where `doc` is the full JSON-serialized document. `id` is auto-indexed by the
PRIMARY KEY constraint.

Supported subset (matches what the codebase actually uses — audited via grep):
  Methods:        find_one, find, insert_one, insert_many, update_one,
                  delete_one, delete_many, count_documents, aggregate
  Filter ops:     equality, $gte, $gt, $lte, $lt, $ne, $in, $nin, $exists
  Update ops:     $set, $inc, $max
  Cursor:         .sort(field, direction), .limit(n), .to_list(n)
  Aggregate:      $group (with $sum, $max), $sort, $limit

Unsupported by design — fail loud:
  $unset, $push, $pull, $addToSet (codebase doesn't use them)

Gate via env: set STORAGE_BACKEND=sqlite to use this; default 'mongodb' keeps
motor in the dev/preview environment unchanged.
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any, Optional

import aiosqlite


# ─── filter/update predicates ──────────────────────────────────────────────────

def _matches(doc: dict, filter_: Optional[dict]) -> bool:
    if not filter_:
        return True
    for k, v in filter_.items():
        field = doc.get(k)
        if isinstance(v, dict):
            for op, val in v.items():
                if op == "$gte":
                    if field is None or field < val:
                        return False
                elif op == "$gt":
                    if field is None or field <= val:
                        return False
                elif op == "$lte":
                    if field is None or field > val:
                        return False
                elif op == "$lt":
                    if field is None or field >= val:
                        return False
                elif op == "$ne":
                    if field == val:
                        return False
                elif op == "$in":
                    if field not in val:
                        return False
                elif op == "$nin":
                    if field in val:
                        return False
                elif op == "$exists":
                    if (k in doc) != bool(val):
                        return False
                else:
                    raise NotImplementedError(f"SQLite shim: filter op {op!r} not supported")
        elif v is None:
            if field is not None:
                return False
        else:
            if field != v:
                return False
    return True


def _apply_update(doc: dict, update: dict) -> None:
    for op, payload in update.items():
        if op == "$set":
            doc.update(payload)
        elif op == "$inc":
            for k, delta in payload.items():
                doc[k] = (doc.get(k) or 0) + delta
        elif op == "$max":
            for k, candidate in payload.items():
                cur = doc.get(k)
                if cur is None or candidate > cur:
                    doc[k] = candidate
        else:
            raise NotImplementedError(f"SQLite shim: update op {op!r} not supported")


# ─── result shims ──────────────────────────────────────────────────────────────

class _InsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class _UpdateResult:
    def __init__(self, matched: int, modified: int):
        self.matched_count = matched
        self.modified_count = modified


class _DeleteResult:
    def __init__(self, deleted: int):
        self.deleted_count = deleted


# ─── cursors ───────────────────────────────────────────────────────────────────

class _FindCursor:
    def __init__(self, db, table, filter_, projection):
        self._db = db
        self._table = table
        self._filter = filter_ or {}
        self._projection = projection
        self._sort: Optional[tuple] = None
        self._limit: Optional[int] = None

    def sort(self, field, direction=1):
        self._sort = (field, direction)
        return self

    def limit(self, n: int):
        self._limit = n
        return self

    async def to_list(self, length: Optional[int] = None):
        return await self._db._find_list(
            self._table, self._filter, self._projection, self._sort,
            self._limit if self._limit is not None else length,
        )


class _AggregateCursor:
    def __init__(self, db, table, pipeline):
        self._db = db
        self._table = table
        self._pipeline = pipeline

    async def to_list(self, length: Optional[int] = None):
        return await self._db._aggregate(self._table, self._pipeline, length)


# ─── collection ────────────────────────────────────────────────────────────────

class SqliteCollection:
    def __init__(self, db, name: str):
        self._db = db
        self._name = name

    async def find_one(self, filter_=None, projection=None, sort=None):
        """Find single document. sort= accepts MongoDB-style list[tuple] e.g. [('field', -1)]."""
        sort_tuple = None
        if sort:
            # MongoDB: sort=[("field", -1)] → (field, -1)
            if isinstance(sort, list) and sort:
                sort_tuple = (sort[0][0], sort[0][1])
            elif isinstance(sort, tuple):
                sort_tuple = sort
        rows = await self._db._find_list(self._name, filter_ or {}, projection, sort_tuple, 1)
        return rows[0] if rows else None

    def find(self, filter_=None, projection=None):
        return _FindCursor(self._db, self._name, filter_, projection)

    async def insert_one(self, doc: dict) -> _InsertOneResult:
        return _InsertOneResult(await self._db._insert(self._name, doc))

    async def insert_many(self, docs: list[dict]):
        ids = []
        for d in docs:
            ids.append(await self._db._insert(self._name, d))
        return _InsertOneResult(ids)

    async def update_one(self, filter_, update) -> _UpdateResult:
        matched, modified = await self._db._update_one(self._name, filter_, update)
        return _UpdateResult(matched, modified)

    async def delete_one(self, filter_) -> _DeleteResult:
        return _DeleteResult(await self._db._delete(self._name, filter_, one=True))

    async def delete_many(self, filter_) -> _DeleteResult:
        return _DeleteResult(await self._db._delete(self._name, filter_, one=False))

    async def count_documents(self, filter_) -> int:
        return await self._db._count(self._name, filter_)

    def aggregate(self, pipeline):
        return _AggregateCursor(self._db, self._name, pipeline)


# ─── database ──────────────────────────────────────────────────────────────────

class SqliteDatabase:
    """Mongo-API-compatible facade over a single SQLite file."""

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._tables_known: set[str] = set()
        self._lock = asyncio.Lock()

    def __getattr__(self, name: str) -> SqliteCollection:
        # Internal attrs starting with _ are handled by normal attribute lookup
        if name.startswith("_"):
            raise AttributeError(name)
        return SqliteCollection(self, name)

    def __getitem__(self, name: str) -> SqliteCollection:
        return SqliteCollection(self, name)

    async def _ensure(self, table: str):
        if table in self._tables_known:
            return
        async with self._lock:
            if table in self._tables_known:
                return
            async with aiosqlite.connect(self.path) as c:
                await c.execute(
                    f'CREATE TABLE IF NOT EXISTS "{table}" '
                    f"(id TEXT PRIMARY KEY, doc TEXT NOT NULL)"
                )
                await c.commit()
            self._tables_known.add(table)

    @staticmethod
    def _project(doc: dict, projection: Optional[dict]) -> dict:
        if not projection:
            return doc
        # Mongo idiom in this codebase: {"_id": 0} — we never store _id, so noop
        out = dict(doc)
        for k, include in projection.items():
            if k == "_id":
                out.pop("_id", None)
            elif include == 0:
                out.pop(k, None)
        return out

    async def _find_list(self, table, filter_, projection, sort_, limit):
        await self._ensure(table)
        async with aiosqlite.connect(self.path) as c:
            cur = await c.execute(f'SELECT doc FROM "{table}"')
            rows = await cur.fetchall()
        docs = [json.loads(r[0]) for r in rows]
        if filter_:
            docs = [d for d in docs if _matches(d, filter_)]
        if sort_:
            field, direction = sort_
            docs.sort(
                key=lambda d: (d.get(field) is None, d.get(field) or ""),
                reverse=(direction == -1),
            )
        if limit:
            docs = docs[: int(limit)]
        return [self._project(d, projection) for d in docs]

    async def _insert(self, table, doc):
        await self._ensure(table)
        doc_id = doc.get("id") or str(uuid.uuid4())
        doc["id"] = doc_id
        body = json.dumps(doc, default=str)
        async with aiosqlite.connect(self.path) as c:
            await c.execute(
                f'INSERT OR REPLACE INTO "{table}" (id, doc) VALUES (?, ?)',
                (doc_id, body),
            )
            await c.commit()
        return doc_id

    async def _update_one(self, table, filter_, update):
        await self._ensure(table)
        async with aiosqlite.connect(self.path) as c:
            cur = await c.execute(f'SELECT id, doc FROM "{table}"')
            rows = await cur.fetchall()
            for row_id, row_doc in rows:
                doc = json.loads(row_doc)
                if _matches(doc, filter_):
                    _apply_update(doc, update)
                    await c.execute(
                        f'UPDATE "{table}" SET doc=? WHERE id=?',
                        (json.dumps(doc, default=str), row_id),
                    )
                    await c.commit()
                    return 1, 1
        return 0, 0

    async def _delete(self, table, filter_, one: bool):
        await self._ensure(table)
        deleted = 0
        async with aiosqlite.connect(self.path) as c:
            cur = await c.execute(f'SELECT id, doc FROM "{table}"')
            rows = await cur.fetchall()
            for row_id, row_doc in rows:
                doc = json.loads(row_doc)
                if _matches(doc, filter_):
                    await c.execute(f'DELETE FROM "{table}" WHERE id=?', (row_id,))
                    deleted += 1
                    if one:
                        break
            await c.commit()
        return deleted

    async def _count(self, table, filter_):
        await self._ensure(table)
        async with aiosqlite.connect(self.path) as c:
            if not filter_:
                cur = await c.execute(f'SELECT COUNT(*) FROM "{table}"')
                (n,) = await cur.fetchone()
                return n
            cur = await c.execute(f'SELECT doc FROM "{table}"')
            rows = await cur.fetchall()
            return sum(1 for r in rows if _matches(json.loads(r[0]), filter_))

    async def _aggregate(self, table, pipeline, length):
        docs = await self._find_list(table, {}, None, None, None)
        for stage in pipeline:
            if "$group" in stage:
                docs = self._stage_group(docs, stage["$group"])
            elif "$match" in stage:
                docs = [d for d in docs if _matches(d, stage["$match"])]
            elif "$sort" in stage:
                for field, direction in reversed(list(stage["$sort"].items())):
                    docs.sort(key=lambda d: (d.get(field) is None, d.get(field) or 0), reverse=(direction == -1))
            elif "$limit" in stage:
                docs = docs[: stage["$limit"]]
            else:
                raise NotImplementedError(f"SQLite shim: aggregate stage {list(stage)!r} not supported")
        if length:
            docs = docs[: length]
        return docs

    @staticmethod
    def _stage_group(docs, spec):
        key_expr = spec["_id"]
        groups: dict[Any, dict] = {}
        for d in docs:
            if isinstance(key_expr, str) and key_expr.startswith("$"):
                k = d.get(key_expr[1:])
            else:
                k = key_expr
            if k not in groups:
                groups[k] = {"_id": k}
            for field, op_spec in spec.items():
                if field == "_id":
                    continue
                if "$sum" in op_spec:
                    val = op_spec["$sum"]
                    if isinstance(val, str) and val.startswith("$"):
                        val = d.get(val[1:], 0) or 0
                    groups[k][field] = groups[k].get(field, 0) + val
                elif "$max" in op_spec:
                    v = op_spec["$max"]
                    if isinstance(v, str) and v.startswith("$"):
                        v = d.get(v[1:])
                    cur = groups[k].get(field)
                    if v is not None and (cur is None or v > cur):
                        groups[k][field] = v
                else:
                    raise NotImplementedError(f"SQLite shim: $group op {list(op_spec)!r} not supported")
        return list(groups.values())


class SqliteClient:
    """Stand-in for AsyncIOMotorClient — only needs .close() and __getitem__."""

    def __init__(self, path: str):
        self._db = SqliteDatabase(path)

    def __getitem__(self, _name: str) -> SqliteDatabase:
        return self._db

    def get_database(self, _name: str) -> SqliteDatabase:
        return self._db

    def close(self):
        pass  # connections are per-call, nothing to close
