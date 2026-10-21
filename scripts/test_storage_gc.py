#!/usr/bin/env python3
"""Offline unit checks for storage_gc keep policy."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from storage_gc import (  # noqa: E402
    Semver,
    container_versions_to_delete,
    npm_versions_to_delete,
)


def _ver(name: str, vid: int) -> dict:
    return {"id": vid, "name": name}


def test_npm_keeps_latest_two_minors_max_patch() -> None:
    versions = [
        _ver("1.60.0", 1),
        _ver("1.61.0", 2),
        _ver("1.61.1", 3),
        _ver("1.62.0", 4),
        _ver("1.62.1", 5),
        _ver("1.59.9", 6),
    ]
    to_delete, to_keep = npm_versions_to_delete(versions)
    keep_names = sorted(v["name"] for v in to_keep)
    delete_names = sorted(v["name"] for v in to_delete)
    assert keep_names == ["1.61.1", "1.62.1"], keep_names
    assert delete_names == ["1.59.9", "1.60.0", "1.61.0", "1.62.0"], delete_names


def test_npm_protects_newest_when_only_one_minor() -> None:
    versions = [_ver("2.0.0", 1), _ver("2.0.1", 2)]
    to_delete, to_keep = npm_versions_to_delete(versions)
    assert [v["name"] for v in to_keep] == ["2.0.1"]
    assert [v["name"] for v in to_delete] == ["2.0.0"]


def test_semver_parse() -> None:
    assert Semver.parse("1.2.3") == Semver(1, 2, 3, "1.2.3")
    assert Semver.parse("nope") is None


def test_container_deletes_untagged_extras() -> None:
    versions = [
        {
            "id": 1,
            "name": "sha256:aaa",
            "updated_at": "2026-01-02T00:00:00Z",
            "metadata": {"container": {"tags": ["latest"]}},
        },
        {
            "id": 2,
            "name": "sha256:bbb",
            "updated_at": "2026-01-01T00:00:00Z",
            "metadata": {"container": {"tags": []}},
        },
        {
            "id": 3,
            "name": "sha256:ccc",
            "updated_at": "2026-01-03T00:00:00Z",
            "metadata": {"container": {"tags": ["sha-deadbeef"]}},
        },
    ]
    to_delete, to_keep = container_versions_to_delete(
        versions, frozenset({"latest", "main"})
    )
    delete_ids = {v["id"] for v in to_delete}
    keep_ids = {v["id"] for v in to_keep}
    assert delete_ids == {2}
    assert keep_ids == {1, 3}  # latest + tagged sha + newest (3)


def main() -> int:
    test_semver_parse()
    test_npm_keeps_latest_two_minors_max_patch()
    test_npm_protects_newest_when_only_one_minor()
    test_container_deletes_untagged_extras()
    print("test_storage_gc: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
