#!/usr/bin/env python3
"""Org-wide Actions artifact + GitHub Packages prune for surefirev2.

Keep policy (npm semver):
  - Within each MAJOR.MINOR keep only the highest PATCH.
  - Within each MAJOR keep only the latest two minors (Y and Y-1).
  - Never delete the single newest version overall.

Containers: keep digests tagged latest/main; keep newest digest; delete untagged extras.

Artifacts: delete when age >= max_age_days (default 3), skip age < min_age_days (default 1).

Usage:
  python3 scripts/storage_gc.py --dry-run
  python3 scripts/storage_gc.py --apply
  python3 scripts/storage_gc.py --dry-run --package math-spike2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


API = "https://api.github.com"


@dataclass
class Summary:
    artifact_deleted: int = 0
    artifact_skipped: int = 0
    artifact_errors: int = 0
    npm_deleted: list[str] = field(default_factory=list)
    npm_kept: list[str] = field(default_factory=list)
    npm_errors: list[str] = field(default_factory=list)
    container_deleted: list[str] = field(default_factory=list)
    container_kept: list[str] = field(default_factory=list)
    container_errors: list[str] = field(default_factory=list)

    def as_markdown(self, dry_run: bool) -> str:
        mode = "DRY RUN" if dry_run else "APPLY"
        lines = [
            f"## Storage GC ({mode})",
            "",
            "### Actions artifacts",
            f"- deleted={self.artifact_deleted} skipped={self.artifact_skipped} errors={self.artifact_errors}",
            "",
            "### npm packages",
            f"- kept ({len(self.npm_kept)}): {', '.join(self.npm_kept) or '(none)'}",
            f"- delete ({len(self.npm_deleted)}): {', '.join(self.npm_deleted) or '(none)'}",
        ]
        if self.npm_errors:
            lines.append(f"- errors: {'; '.join(self.npm_errors)}")
        lines += [
            "",
            "### container packages",
            f"- kept ({len(self.container_kept)}): {', '.join(self.container_kept) or '(none)'}",
            f"- delete ({len(self.container_deleted)}): {', '.join(self.container_deleted) or '(none)'}",
        ]
        if self.container_errors:
            lines.append(f"- errors: {'; '.join(self.container_errors)}")
        return "\n".join(lines) + "\n"


@dataclass(frozen=True, order=True)
class Semver:
    major: int
    minor: int
    patch: int
    raw: str

    @classmethod
    def parse(cls, raw: str) -> Semver | None:
        parts = raw.split(".")
        if len(parts) != 3:
            return None
        try:
            return cls(int(parts[0]), int(parts[1]), int(parts[2]), raw)
        except ValueError:
            return None


class GitHubClient:
    def __init__(self, token: str, org: str) -> None:
        self.token = token
        self.org = org

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        qs = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = f"{API}{path}{qs}"
        req = urllib.request.Request(
            url,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "surefirev2-storage-gc",
            },
        )
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read()
                if not body:
                    return None
                return json.loads(body.decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"{method} {path} -> {exc.code}: {detail}") from exc

    def paginate(self, path: str, *, list_key: str | None = None) -> list[Any]:
        """Paginate list endpoints. If list_key is set, unwrap that key per page."""
        page = 1
        out: list[Any] = []
        while True:
            data = self._request("GET", path, params={"per_page": 100, "page": page})
            if data is None:
                break
            if list_key is not None:
                chunk = data.get(list_key) or []
                out.extend(chunk)
                total = data.get("total_count")
                if not chunk or (total is not None and len(out) >= total):
                    break
            else:
                if not isinstance(data, list) or not data:
                    break
                out.extend(data)
                if len(data) < 100:
                    break
            page += 1
        return out

    def list_repos(self) -> list[str]:
        repos = self.paginate(f"/orgs/{self.org}/repos")
        return [r["name"] for r in repos if not r.get("archived")]

    def list_artifacts(self, repo: str) -> list[dict[str, Any]]:
        return self.paginate(
            f"/repos/{self.org}/{repo}/actions/artifacts",
            list_key="artifacts",
        )

    def delete_artifact(self, repo: str, artifact_id: int) -> None:
        self._request(
            "DELETE",
            f"/repos/{self.org}/{repo}/actions/artifacts/{artifact_id}",
        )

    def list_packages_of_type(self, package_type: str) -> list[dict[str, Any]]:
        page = 1
        out: list[Any] = []
        while True:
            data = self._request(
                "GET",
                f"/orgs/{self.org}/packages",
                params={"package_type": package_type, "per_page": 100, "page": page},
            )
            if not isinstance(data, list) or not data:
                break
            out.extend(data)
            if len(data) < 100:
                break
            page += 1
        return out

    def list_package_versions(
        self, package_type: str, package_name: str
    ) -> list[dict[str, Any]]:
        enc = urllib.parse.quote(package_name, safe="")
        return self.paginate(
            f"/orgs/{self.org}/packages/{package_type}/{enc}/versions"
        )

    def delete_package_version(
        self, package_type: str, package_name: str, version_id: int
    ) -> None:
        enc = urllib.parse.quote(package_name, safe="")
        self._request(
            "DELETE",
            f"/orgs/{self.org}/packages/{package_type}/{enc}/versions/{version_id}",
        )


def npm_versions_to_delete(
    versions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (to_delete, to_keep) for npm package versions."""
    parsed: list[tuple[Semver, dict[str, Any]]] = []
    non_semver: list[dict[str, Any]] = []
    for ver in versions:
        name = ver.get("name") or ""
        sv = Semver.parse(name)
        if sv is None:
            non_semver.append(ver)
            continue
        parsed.append((sv, ver))

    if not parsed:
        return [], non_semver

    newest = max(sv for sv, _ in parsed)
    by_major: dict[int, list[tuple[Semver, dict[str, Any]]]] = defaultdict(list)
    for sv, ver in parsed:
        by_major[sv.major].append((sv, ver))

    keep_ids: set[int] = set()
    for major, items in by_major.items():
        max_minor = max(sv.minor for sv, _ in items)
        allowed_minors = {max_minor, max_minor - 1}
        by_minor: dict[int, list[tuple[Semver, dict[str, Any]]]] = defaultdict(list)
        for sv, ver in items:
            if sv.minor in allowed_minors:
                by_minor[sv.minor].append((sv, ver))
        for _minor, minor_items in by_minor.items():
            best = max(sv for sv, _ in minor_items)
            for sv, ver in minor_items:
                if sv == best:
                    keep_ids.add(ver["id"])

    # Always protect the single newest version overall.
    for sv, ver in parsed:
        if sv == newest:
            keep_ids.add(ver["id"])

    to_keep = [ver for sv, ver in parsed if ver["id"] in keep_ids] + non_semver
    to_delete = [ver for sv, ver in parsed if ver["id"] not in keep_ids]
    return to_delete, to_keep


def container_versions_to_delete(
    versions: list[dict[str, Any]],
    protected_tags: frozenset[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not versions:
        return [], []

    # Newest first by updated_at / created_at
    def sort_key(v: dict[str, Any]) -> str:
        return v.get("updated_at") or v.get("created_at") or ""

    ordered = sorted(versions, key=sort_key, reverse=True)
    newest_id = ordered[0]["id"]

    to_keep: list[dict[str, Any]] = []
    to_delete: list[dict[str, Any]] = []
    for ver in ordered:
        tags = set(
            ((ver.get("metadata") or {}).get("container") or {}).get("tags") or []
        )
        protected = bool(tags & protected_tags) or ver["id"] == newest_id
        if protected:
            to_keep.append(ver)
        elif not tags:
            # Untagged extras
            to_delete.append(ver)
        else:
            # Tagged but not protected — keep (e.g. semver/sha tags on comic-reader)
            to_keep.append(ver)
    return to_delete, to_keep


def prune_artifacts(
    client: GitHubClient,
    summary: Summary,
    *,
    dry_run: bool,
    max_age_days: int,
    min_age_days: int,
) -> None:
    max_age_ms = max_age_days * 24 * 60 * 60 * 1000
    min_age_ms = min_age_days * 24 * 60 * 60 * 1000
    now_ms = int(time.time() * 1000)

    for repo in client.list_repos():
        try:
            artifacts = client.list_artifacts(repo)
        except RuntimeError as exc:
            print(f"warn: list artifacts {repo}: {exc}", file=sys.stderr)
            summary.artifact_errors += 1
            continue

        for artifact in artifacts:
            if artifact.get("expired"):
                # Already expired; still try delete to free billing lag items
                pass
            created = artifact.get("created_at")
            if not created:
                summary.artifact_skipped += 1
                continue
            try:
                from datetime import datetime

                created_ms = int(
                    datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
                    * 1000
                )
            except ValueError:
                summary.artifact_skipped += 1
                continue

            age_ms = now_ms - created_ms
            if age_ms < min_age_ms:
                summary.artifact_skipped += 1
                continue
            if age_ms < max_age_ms and not artifact.get("expired"):
                summary.artifact_skipped += 1
                continue

            label = f"{repo}/{artifact.get('name')}#{artifact['id']}"
            if dry_run:
                print(f"would delete artifact {label}")
                summary.artifact_deleted += 1
                continue
            try:
                client.delete_artifact(repo, artifact["id"])
                print(f"deleted artifact {label}")
                summary.artifact_deleted += 1
            except RuntimeError as exc:
                print(f"warn: delete artifact {label}: {exc}", file=sys.stderr)
                summary.artifact_errors += 1


def prune_npm(
    client: GitHubClient,
    summary: Summary,
    *,
    dry_run: bool,
    package_filter: str | None,
) -> None:
    packages = client.list_packages_of_type("npm")
    for pkg in packages:
        name = pkg["name"]
        if package_filter and name != package_filter:
            continue
        versions = client.list_package_versions("npm", name)
        to_delete, to_keep = npm_versions_to_delete(versions)
        for ver in to_keep:
            summary.npm_kept.append(f"{name}@{ver.get('name')}")
        for ver in to_delete:
            label = f"{name}@{ver.get('name')}#{ver['id']}"
            if dry_run:
                print(f"would delete npm {label}")
                summary.npm_deleted.append(label)
                continue
            try:
                client.delete_package_version("npm", name, ver["id"])
                print(f"deleted npm {label}")
                summary.npm_deleted.append(label)
            except RuntimeError as exc:
                print(f"warn: delete npm {label}: {exc}", file=sys.stderr)
                summary.npm_errors.append(label)


def prune_containers(
    client: GitHubClient,
    summary: Summary,
    *,
    dry_run: bool,
    package_filter: str | None,
    protected_tags: frozenset[str],
) -> None:
    packages = client.list_packages_of_type("container")
    for pkg in packages:
        name = pkg["name"]
        if package_filter and name != package_filter:
            continue
        try:
            versions = client.list_package_versions("container", name)
        except RuntimeError as exc:
            print(f"warn: list container {name}: {exc}", file=sys.stderr)
            summary.container_errors.append(name)
            continue
        to_delete, to_keep = container_versions_to_delete(versions, protected_tags)
        for ver in to_keep:
            tags = ((ver.get("metadata") or {}).get("container") or {}).get("tags") or []
            summary.container_kept.append(
                f"{name}@{ver.get('name')[:12]} tags={','.join(tags) or '-'}"
            )
        for ver in to_delete:
            label = f"{name}@{ver.get('name')[:12]}#{ver['id']}"
            if dry_run:
                print(f"would delete container {label}")
                summary.container_deleted.append(label)
                continue
            try:
                client.delete_package_version("container", name, ver["id"])
                print(f"deleted container {label}")
                summary.container_deleted.append(label)
            except RuntimeError as exc:
                print(f"warn: delete container {label}: {exc}", file=sys.stderr)
                summary.container_errors.append(label)


def write_summary(path: str | None, text: str) -> None:
    print(text)
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--org", default=os.environ.get("STORAGE_GC_ORG", "surefirev2"))
    parser.add_argument(
        "--token",
        default=os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "",
    )
    parser.add_argument("--package", default=None, help="Limit to one package name")
    parser.add_argument("--max-age-days", type=int, default=3)
    parser.add_argument("--min-age-days", type=int, default=1)
    parser.add_argument(
        "--skip-artifacts",
        action="store_true",
        help="Only prune packages",
    )
    parser.add_argument(
        "--skip-packages",
        action="store_true",
        help="Only prune artifacts",
    )
    parser.add_argument(
        "--summary-path",
        default=os.environ.get("GITHUB_STEP_SUMMARY"),
    )
    args = parser.parse_args(argv)

    if not args.token:
        print("GITHUB_TOKEN or GH_TOKEN required", file=sys.stderr)
        return 2

    dry_run = bool(args.dry_run)
    client = GitHubClient(args.token, args.org)
    summary = Summary()

    if not args.skip_artifacts:
        prune_artifacts(
            client,
            summary,
            dry_run=dry_run,
            max_age_days=args.max_age_days,
            min_age_days=args.min_age_days,
        )
    if not args.skip_packages:
        prune_npm(
            client,
            summary,
            dry_run=dry_run,
            package_filter=args.package,
        )
        prune_containers(
            client,
            summary,
            dry_run=dry_run,
            package_filter=args.package,
            protected_tags=frozenset({"latest", "main"}),
        )

    write_summary(args.summary_path, summary.as_markdown(dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
