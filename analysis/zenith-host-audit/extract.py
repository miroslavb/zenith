#!/usr/bin/env python3
"""Reproducible host-side audit of Zenith mission history.

The script treats ~/.zenith/projects as the authoritative mission registry and
uses agent transcript corpora only to establish which host agents referenced
the registered missions.  It never copies raw transcripts into the output.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


ATTEMPT_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z)")
PROJECT_ID_RE = re.compile(r"202\d{5}T\d{6}Z-[A-Za-z0-9_-]+")
GAP_HEADING_RE = re.compile(
    r"(?m)^#{2,4}\s+(GAP-[A-Za-z0-9_-]+)\s*(?:[-—:]\s*)?(.*)$"
)
SECRET_PATTERNS = (
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1‹redacted›"),
    (
        re.compile(
            r"(?i)((?:api[_ -]?key|token|password|passwd|secret|authorization)\s*[:=]\s*)\S+"
        ),
        r"\1‹redacted›",
    ),
    (re.compile(r"\b[A-Fa-f0-9]{40,}\b"), "‹redacted-long-hex›"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "‹redacted-ipv4›"),
    (re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"), "‹redacted-email›"),
)


@dataclass(frozen=True)
class AttemptRow:
    project_id: str
    mission_id: str
    node_id: str
    task_type: str
    source_path: str
    dispatched_at: str
    completed_at: str
    duration_seconds: float
    duration_robust: int
    done: int
    passed: int | None
    request_attention: int
    missing_end_node: int
    rate_limit: int
    killed_or_timeout: int
    internal_error: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--zenith-root", type=Path, default=Path("/root/.zenith/projects")
    )
    parser.add_argument(
        "--output", type=Path, default=Path(__file__).resolve().parent / "evidence"
    )
    parser.add_argument("--as-of", default="2026-09-01")
    parser.add_argument("--skip-transcripts", action="store_true")
    return parser.parse_args()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return default


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    result: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def bool_field(frontmatter: dict[str, str], key: str) -> int | None:
    value = frontmatter.get(key)
    if value == "true":
        return 1
    if value == "false":
        return 0
    return None


def redact(text: str, limit: int = 700) -> str:
    value = " ".join(text.split())
    for pattern, replacement in SECRET_PATTERNS:
        value = pattern.sub(replacement, value)
    return value[:limit]


def iso_from_attempt_filename(path: Path) -> tuple[datetime | None, str]:
    match = ATTEMPT_TS_RE.match(path.name)
    if not match:
        return None, ""
    token = match.group(1)
    try:
        parsed = datetime.strptime(token, "%Y-%m-%dT%H-%M-%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None, ""
    return parsed, parsed.isoformat().replace("+00:00", "Z")


def infer_task_type(node_id: str) -> str:
    lower = node_id.lower()
    if lower.startswith(("validate", "validator", "v-", "v_")) or "-validate" in lower:
        return "validate"
    if lower.startswith(("gate", "g-", "g_")) or "-gate" in lower:
        return "gate"
    return "work"


def classify_project(project_id: str, workspace: str) -> str:
    text = f"{project_id} {workspace}".lower()
    scientific = (
        "conformer",
        "xpd",
        "platinum",
        "oxaliplatin",
        "biometal",
        "ir-iii",
        "mpges2",
        "girdin",
        "scientific-article",
        "literature",
    )
    infrastructure = (
        "security-hardening",
        "edge-rce",
        "openssh",
        "zigbee",
        "c6-enviro",
        "ajazz",
        "vnish",
        "wildrig",
        "peakminer",
        "pearl-hopper",
        "ai-automation-nuc",
        "tanya-mission",
    )
    product = (
        "cloudstrix",
        "telecom-crm",
        "crypto-miner-alert",
        "capybara",
        "territory",
        "/arena",
        "pnl-analysis",
    )
    if any(token in text for token in scientific):
        return "scientific"
    if any(token in text for token in infrastructure):
        return "infrastructure_security"
    if any(token in text for token in product):
        return "product_software"
    return "research_process_other"


def direct_files(root: Path, pattern: str) -> list[Path]:
    return sorted(path for path in root.glob(pattern) if path.is_file())


def csv_write(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def corpus_units(cutoff_year_months: tuple[str, ...]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []

    claude_root = Path("/root/.claude/projects")
    if claude_root.exists():
        for child in sorted(path for path in claude_root.iterdir() if path.is_dir()):
            units.append(
                {
                    "source_unit": f"claude:{child.name}",
                    "agent": "claude",
                    "roots": [child],
                    "suffixes": {".jsonl"},
                    "names": set(),
                }
            )

    codex_root = Path("/root/.codex/sessions/2026")
    for month in cutoff_year_months:
        root = codex_root / month
        units.append(
            {
                "source_unit": f"codex:2026-{month}",
                "agent": "codex",
                "roots": [root],
                "suffixes": {".jsonl"},
                "names": set(),
            }
        )

    for home in (
        "/root/.hermes",
        "/root/.hermes-agent2",
        "/root/.hermes-hermes3",
        "/root/.hermes-miner",
        "/root/.hermes-rlm-repl",
        "/root/.hermes-hersets3",
    ):
        root = Path(home)
        units.append(
            {
                "source_unit": f"hermes:{root.name}",
                "agent": "hermes",
                "roots": [root / "sessions", root / ".hermes_history"],
                "suffixes": {".jsonl"},
                "names": {".hermes_history"},
            }
        )

    gstack_root = Path("/root/.gstack/projects")
    if gstack_root.exists():
        for child in sorted(path for path in gstack_root.iterdir() if path.is_dir()):
            units.append(
                {
                    "source_unit": f"gstack:{child.name}",
                    "agent": "gstack",
                    "roots": [child / "checkpoints"],
                    "suffixes": {".md"},
                    "names": set(),
                }
            )

    units.extend(
        [
            {
                "source_unit": "openclaw:evidence-only",
                "agent": "openclaw",
                "roots": [Path("/root/openclaw-backup/extracted/.openclaw")],
                "suffixes": {".log", ".md", ".jsonl"},
                "names": {"MEMORY.md"},
            },
            {
                "source_unit": "tg-bridge:agent-side",
                "agent": "tg_bridge",
                "roots": [Path("/root/.claude-tg-bridge/bridge.log")],
                "suffixes": {".log"},
                "names": {"bridge.log"},
            },
            {
                "source_unit": "gbrain:hermes-export-mirror",
                "agent": "gbrain_export",
                "roots": [Path("/root/.hermes/brain-export")],
                "suffixes": {".md", ".json", ".jsonl"},
                "names": set(),
            },
        ]
    )
    return units


def candidate_files(unit: dict[str, Any]) -> list[Path]:
    found: set[Path] = set()
    suffixes: set[str] = unit["suffixes"]
    names: set[str] = unit["names"]
    for root in unit["roots"]:
        if root.is_file():
            if root.suffix in suffixes or root.name in names:
                found.add(root)
            continue
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            dirnames[:] = [name for name in dirnames if name not in {"node_modules", ".git"}]
            base = Path(dirpath)
            for name in filenames:
                path = base / name
                if path.suffix in suffixes or name in names:
                    found.add(path)
    return sorted(found)


def rg_prefilter(files: list[Path]) -> tuple[int, set[str]]:
    if not files:
        return 0, set()
    matched_lines = 0
    mission_tokens: set[str] = set()
    pattern = r"(?i)zenith|202\d{5}T\d{6}Z-[A-Za-z0-9_-]+"
    for start in range(0, len(files), 350):
        batch = files[start : start + 350]
        process = subprocess.run(
            ["rg", "--json", "-e", pattern, "--", *map(str, batch)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        for line in process.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "match":
                continue
            text_value = event.get("data", {}).get("lines", {}).get("text", "")
            matched_lines += 1
            mission_tokens.update(PROJECT_ID_RE.findall(text_value))
    return matched_lines, mission_tokens


def scan_corpora(project_ids: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    coverage: list[dict[str, Any]] = []
    mention_counts: Counter[tuple[str, str]] = Counter()
    for unit in corpus_units(("06", "07", "08")):
        files = candidate_files(unit)
        matched_lines, tokens = rg_prefilter(files)
        exact = sorted(token for token in tokens if token in project_ids)
        for project_id in exact:
            mention_counts[(unit["agent"], project_id)] += 1
        coverage.append(
            {
                "source_unit": unit["source_unit"],
                "files_total": len(files),
                "files_read": len(files),
                "parse_depth": f"full-file rg --json prefilter; matched_lines={matched_lines}",
                "skip_reason": "" if files else "STRUCTURAL: missing or empty corpus unit",
            }
        )
    mentions = [
        {"agent": agent, "project_id": project_id, "units_with_exact_reference": count}
        for (agent, project_id), count in sorted(mention_counts.items())
    ]
    return coverage, mentions


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    low = int(index)
    high = min(low + 1, len(ordered) - 1)
    weight = index - low
    return ordered[low] * (1 - weight) + ordered[high] * weight


def first_report_excerpt(text: str) -> str:
    marker = text.find("## Report")
    if marker >= 0:
        return redact(text[marker + len("## Report") :])
    return redact(text)


def database_write(
    path: Path,
    findings: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    missions: list[dict[str, Any]],
    attempts: list[AttemptRow],
    tasks: list[dict[str, Any]],
    mentions: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        temporary = Path(tmp.name)
    try:
        connection = sqlite3.connect(temporary)
        connection.executescript(
            """
            PRAGMA page_size=4096;
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            PRAGMA locking_mode=EXCLUSIVE;
            CREATE TABLE findings(
              id INTEGER PRIMARY KEY, agent TEXT, pattern_id TEXT,
              source_path TEXT, locator TEXT, actor TEXT,
              verbatim_excerpt TEXT, severity TEXT, note TEXT
            );
            CREATE TABLE coverage_manifest(
              source_unit TEXT PRIMARY KEY, files_total INTEGER,
              files_read INTEGER, parse_depth TEXT, skip_reason TEXT
            );
            CREATE TABLE mission_metrics(
              project_id TEXT PRIMARY KEY, workspace_dir TEXT, created_at TEXT,
              state TEXT, category TEXT, tasks_total INTEGER, work_tasks INTEGER,
              validate_tasks INTEGER, gate_tasks INTEGER, superseded_tasks INTEGER,
              attempts_total INTEGER, attempts_done INTEGER, attempts_failed INTEGER,
              missing_end_node INTEGER, rate_limit INTEGER,
              robust_agent_seconds REAL, robust_batch_wall_seconds REAL,
              contracts INTEGER, regressions INTEGER, evidence_files INTEGER,
              evidence_bytes INTEGER, terminal_reviews INTEGER,
              terminal_gap_headings INTEGER, current_attention_items INTEGER
            );
            CREATE TABLE attempts(
              project_id TEXT, mission_id TEXT, node_id TEXT, task_type TEXT,
              source_path TEXT PRIMARY KEY, dispatched_at TEXT, completed_at TEXT,
              duration_seconds REAL, duration_robust INTEGER, done INTEGER,
              passed INTEGER, request_attention INTEGER, missing_end_node INTEGER,
              rate_limit INTEGER, killed_or_timeout INTEGER, internal_error INTEGER
            );
            CREATE TABLE task_inventory(
              project_id TEXT, mission_id TEXT, task_id TEXT, task_type TEXT,
              status TEXT, targets_count INTEGER,
              PRIMARY KEY(project_id, mission_id, task_id)
            );
            CREATE TABLE provider_mentions(
              agent TEXT, project_id TEXT, units_with_exact_reference INTEGER,
              PRIMARY KEY(agent, project_id)
            );
            """
        )
        connection.executemany(
            "INSERT INTO findings VALUES(?,?,?,?,?,?,?,?,?)",
            [
                (
                    index,
                    row["agent"],
                    row["pattern_id"],
                    row["source_path"],
                    row["locator"],
                    row["actor"],
                    row["verbatim_excerpt"],
                    row["severity"],
                    row["note"],
                )
                for index, row in enumerate(
                    sorted(
                        findings,
                        key=lambda item: (
                            item["pattern_id"],
                            item["source_path"],
                            item["locator"],
                        ),
                    ),
                    1,
                )
            ],
        )
        connection.executemany(
            "INSERT INTO coverage_manifest VALUES(?,?,?,?,?)",
            [
                tuple(row[field] for field in ("source_unit", "files_total", "files_read", "parse_depth", "skip_reason"))
                for row in sorted(coverage, key=lambda item: item["source_unit"])
            ],
        )
        mission_fields = (
            "project_id", "workspace_dir", "created_at", "state", "category",
            "tasks_total", "work_tasks", "validate_tasks", "gate_tasks",
            "superseded_tasks", "attempts_total", "attempts_done", "attempts_failed",
            "missing_end_node", "rate_limit", "robust_agent_seconds",
            "robust_batch_wall_seconds", "contracts", "regressions", "evidence_files",
            "evidence_bytes", "terminal_reviews", "terminal_gap_headings",
            "current_attention_items",
        )
        connection.executemany(
            f"INSERT INTO mission_metrics VALUES({','.join('?' for _ in mission_fields)})",
            [tuple(row[field] for field in mission_fields) for row in sorted(missions, key=lambda item: item["project_id"])],
        )
        attempt_fields = tuple(AttemptRow.__dataclass_fields__)
        connection.executemany(
            f"INSERT INTO attempts VALUES({','.join('?' for _ in attempt_fields)})",
            [tuple(asdict(row)[field] for field in attempt_fields) for row in sorted(attempts, key=lambda item: item.source_path)],
        )
        connection.executemany(
            "INSERT INTO task_inventory VALUES(?,?,?,?,?,?)",
            [
                tuple(row[field] for field in ("project_id", "mission_id", "task_id", "task_type", "status", "targets_count"))
                for row in sorted(tasks, key=lambda item: (item["project_id"], item["mission_id"], item["task_id"]))
            ],
        )
        connection.executemany(
            "INSERT INTO provider_mentions VALUES(?,?,?)",
            [
                tuple(row[field] for field in ("agent", "project_id", "units_with_exact_reference"))
                for row in sorted(mentions, key=lambda item: (item["agent"], item["project_id"]))
            ],
        )
        connection.commit()
        connection.execute("VACUUM")
        connection.close()
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def audit(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    projects = sorted(
        path.parent.parent
        for path in args.zenith_root.glob("*/.zenith-runtime/project.json")
    )
    project_ids = {path.name for path in projects}
    all_attempts: list[AttemptRow] = []
    all_tasks: list[dict[str, Any]] = []
    mission_rows: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []

    for project_root in projects:
        project = read_json(project_root / ".zenith-runtime" / "project.json", {})
        state_data = read_json(project_root / ".zenith-runtime" / "state.json", {})
        project_id = str(project.get("id", project_root.name))
        workspace = str(project.get("workspace_dir", ""))
        state = str(state_data.get("state", "unknown"))
        category = classify_project(project_id, workspace)
        project_task_rows: list[dict[str, Any]] = []
        project_attempts: list[AttemptRow] = []
        contracts = 0
        regressions = 0
        evidence_files = 0
        evidence_bytes = 0
        terminal_reviews = 0
        terminal_gap_headings = 0

        mission_runtime_root = project_root / ".zenith-runtime" / "missions"
        durable_mission_root = project_root / ".zenith" / "missions"
        mission_ids = sorted(
            {
                path.name
                for path in (list(mission_runtime_root.glob("mission-*")) + list(durable_mission_root.glob("mission-*")))
                if path.is_dir()
            }
        )
        for mission_id in mission_ids:
            runtime = mission_runtime_root / mission_id
            durable = durable_mission_root / mission_id
            task_doc = read_json(runtime / "tasks.json", {"tasks": []})
            task_state = read_json(runtime / "task-state.json", {"tasks": {}}).get("tasks", {})
            task_lookup: dict[str, str] = {}
            for task in task_doc.get("tasks", []):
                task_id = str(task.get("id", ""))
                task_type = str(task.get("type", "unknown"))
                task_lookup[task_id] = task_type
                row = {
                    "project_id": project_id,
                    "mission_id": mission_id,
                    "task_id": task_id,
                    "task_type": task_type,
                    "status": str(task_state.get(task_id, {}).get("status", "unknown")),
                    "targets_count": len(task.get("targets") or []),
                }
                project_task_rows.append(row)
                all_tasks.append(row)

            for attempt_path in direct_files(durable / "attempts", "*.md"):
                text = read_text(attempt_path)
                frontmatter = parse_frontmatter(text)
                fallback_node = attempt_path.stem.split("__", 1)[-1]
                node_id = frontmatter.get("node_id", fallback_node)
                task_type = task_lookup.get(node_id, infer_task_type(node_id))
                dispatched, dispatched_iso = iso_from_attempt_filename(attempt_path)
                completed = datetime.fromtimestamp(attempt_path.stat().st_mtime, tz=UTC)
                duration = (completed - dispatched).total_seconds() if dispatched else -1.0
                robust = int(0 <= duration <= 6 * 3600)
                done = bool_field(frontmatter, "done")
                passed = bool_field(frontmatter, "passed")
                request_attention = bool_field(frontmatter, "request_attention")
                row = AttemptRow(
                    project_id=project_id,
                    mission_id=mission_id,
                    node_id=node_id,
                    task_type=task_type,
                    source_path=str(attempt_path),
                    dispatched_at=dispatched_iso,
                    completed_at=completed.isoformat().replace("+00:00", "Z"),
                    duration_seconds=round(duration, 3),
                    duration_robust=robust,
                    done=int(done or 0),
                    passed=passed,
                    request_attention=int(request_attention or 0),
                    missing_end_node=int("without calling end_node" in text),
                    rate_limit=int(bool(re.search(r"rate_limit|session limit|usage limit", text, re.I))),
                    killed_or_timeout=int(bool(re.search(r"exit_code=-15|SIGTERM|timed out|timeout", text, re.I))),
                    internal_error=int(bool(re.search(r"MCP error|Internal error|acp_error|crashed", text, re.I))),
                )
                project_attempts.append(row)
                all_attempts.append(row)
                if row.missing_end_node:
                    findings.append(
                        {
                            "agent": task_type,
                            "pattern_id": "ZH-ACP-HANDOFF",
                            "source_path": str(attempt_path),
                            "locator": "frontmatter/report",
                            "actor": "agent",
                            "verbatim_excerpt": first_report_excerpt(text),
                            "severity": "medium",
                            "note": "Attempt ended without the mandatory handoff call.",
                        }
                    )
                if row.rate_limit:
                    findings.append(
                        {
                            "agent": task_type,
                            "pattern_id": "ZH-RATE-LIMIT",
                            "source_path": str(attempt_path),
                            "locator": "report",
                            "actor": "agent",
                            "verbatim_excerpt": first_report_excerpt(text),
                            "severity": "medium",
                            "note": "Attempt reports a provider/session usage limit.",
                        }
                    )

            contract_files = direct_files(durable / "contract", "*.md")
            contracts += len(contract_files)
            regression_files = direct_files(durable / "regressions", "*.md")
            regressions += len(regression_files)
            for regression in regression_files:
                findings.append(
                    {
                        "agent": "validator",
                        "pattern_id": "ZH-REGRESSION",
                        "source_path": str(regression),
                        "locator": "first heading",
                        "actor": "agent",
                        "verbatim_excerpt": first_report_excerpt(read_text(regression)),
                        "severity": "high",
                        "note": "Durable regression artifact emitted by validation.",
                    }
                )

            evidence_root = durable / "evidence"
            if evidence_root.exists():
                for artifact in sorted(path for path in evidence_root.rglob("*") if path.is_file()):
                    evidence_files += 1
                    try:
                        evidence_bytes += artifact.stat().st_size
                    except OSError:
                        pass

            review_files = direct_files(durable / "terminal-reviews", "*.md")
            terminal_reviews += len(review_files)
            for review in review_files:
                text = read_text(review)
                gaps = list(GAP_HEADING_RE.finditer(text))
                terminal_gap_headings += len(gaps)
                for match in gaps:
                    title = match.group(2).strip()
                    severity = "high" if re.search(r"critical|high", title, re.I) else "medium"
                    if category == "scientific" and severity == "high":
                        findings.append(
                            {
                                "agent": "terminal_reviewer",
                                "pattern_id": "ZH-SCIENCE-MATERIAL-GAP",
                                "source_path": str(review),
                                "locator": match.group(1),
                                "actor": "agent",
                                "verbatim_excerpt": redact(match.group(0)),
                                "severity": "high",
                                "note": "High-severity scientific gap found by independent terminal review.",
                            }
                        )

        reason = str(state_data.get("reason", ""))
        if "Terminal reviewer crashed" in reason:
            findings.append(
                {
                    "agent": "terminal_reviewer",
                    "pattern_id": "ZH-FORMAL-FALSE-NEGATIVE",
                    "source_path": str(project_root / ".zenith-runtime" / "state.json"),
                    "locator": "reason",
                    "actor": "agent",
                    "verbatim_excerpt": redact(reason),
                    "severity": "high",
                    "note": "Mission is failed solely at the mandatory terminal-review protocol boundary.",
                }
            )

        task_counts = Counter(row["task_type"] for row in project_task_rows)
        task_status = Counter(row["status"] for row in project_task_rows)
        robust_attempts = [row for row in project_attempts if row.duration_robust]
        batches: dict[tuple[str, str], float] = defaultdict(float)
        for attempt in robust_attempts:
            batches[(attempt.mission_id, attempt.dispatched_at)] = max(
                batches[(attempt.mission_id, attempt.dispatched_at)], attempt.duration_seconds
            )
        attention_items = state_data.get("items", [])
        mission_rows.append(
            {
                "project_id": project_id,
                "workspace_dir": workspace,
                "created_at": str(project.get("created_at", "")),
                "state": state,
                "category": category,
                "tasks_total": len(project_task_rows),
                "work_tasks": task_counts["work"],
                "validate_tasks": task_counts["validate"],
                "gate_tasks": task_counts["gate"],
                "superseded_tasks": task_status["superseded"],
                "attempts_total": len(project_attempts),
                "attempts_done": sum(row.done for row in project_attempts),
                "attempts_failed": sum(1 - row.done for row in project_attempts),
                "missing_end_node": sum(row.missing_end_node for row in project_attempts),
                "rate_limit": sum(row.rate_limit for row in project_attempts),
                "robust_agent_seconds": round(sum(row.duration_seconds for row in robust_attempts), 3),
                "robust_batch_wall_seconds": round(sum(batches.values()), 3),
                "contracts": contracts,
                "regressions": regressions,
                "evidence_files": evidence_files,
                "evidence_bytes": evidence_bytes,
                "terminal_reviews": terminal_reviews,
                "terminal_gap_headings": terminal_gap_headings,
                "current_attention_items": len(attention_items) if isinstance(attention_items, list) else 0,
            }
        )

    overhead_checkpoint = Path(
        "/root/.gstack/projects/miroslavb-pearl-hopper/checkpoints/"
        "20260823-233359-pearl-hopper-zenith-stopped-p0-p1-p2-handoff.md"
    )
    checkpoint_text = read_text(overhead_checkpoint)
    if "protocol overhead is too high" in checkpoint_text:
        sentence = next(
            (line.strip() for line in checkpoint_text.splitlines() if "protocol overhead is too high" in line),
            "",
        )
        findings.append(
            {
                "agent": "gstack_checkpoint",
                "pattern_id": "ZH-OPERATOR-OVERHEAD-STOP",
                "source_path": str(overhead_checkpoint),
                "locator": "Summary",
                "actor": "operator",
                "verbatim_excerpt": redact(sentence),
                "severity": "high",
                "note": "Durable handoff records an operator stop attributed to protocol overhead.",
            }
        )

    cloudstrix_checkpoint = Path(
        "/root/.gstack/projects/miroslavb-cloudstrix-integra/checkpoints/"
        "20260701-191158-cloudstrix-18.06-feedback-closed-prod-bugs-fixed.md"
    )
    cloudstrix_text = read_text(cloudstrix_checkpoint)
    if "stamped the run \"failed\" ONLY because the ACP terminal-reviewer crashed" in cloudstrix_text:
        sentence = next(
            (
                line.strip()
                for line in cloudstrix_text.splitlines()
                if "stamped the run \"failed\" ONLY" in line
            ),
            "",
        )
        findings.append(
            {
                "agent": "gstack_checkpoint",
                "pattern_id": "ZH-FORMAL-FALSE-NEGATIVE",
                "source_path": str(cloudstrix_checkpoint),
                "locator": "Notes",
                "actor": "agent",
                "verbatim_excerpt": redact(sentence),
                "severity": "high",
                "note": "Checkpoint distinguishes a product completion from a harness terminal failure.",
            }
        )

    if args.skip_transcripts:
        coverage: list[dict[str, Any]] = []
        mentions: list[dict[str, Any]] = []
    else:
        coverage, mentions = scan_corpora(project_ids)

    mission_fields = list(mission_rows[0]) if mission_rows else []
    csv_write(output / "mission_metrics.csv", sorted(mission_rows, key=lambda row: row["project_id"]), mission_fields)
    attempt_fields = list(AttemptRow.__dataclass_fields__)
    csv_write(output / "attempt_metrics.csv", [asdict(row) for row in sorted(all_attempts, key=lambda row: row.source_path)], attempt_fields)
    coverage_fields = ["source_unit", "files_total", "files_read", "parse_depth", "skip_reason"]
    csv_write(output / "coverage_manifest.csv", sorted(coverage, key=lambda row: row["source_unit"]), coverage_fields)
    csv_write(
        output / "provider_mentions.csv",
        mentions,
        ["agent", "project_id", "units_with_exact_reference"],
    )

    state_counts = Counter(row["state"] for row in mission_rows)
    category_counts = Counter(row["category"] for row in mission_rows)
    task_counts = Counter(row["task_type"] for row in all_tasks)
    task_status = Counter(row["status"] for row in all_tasks)
    robust_durations = [row.duration_seconds for row in all_attempts if row.duration_robust]
    valid_attempts = [row for row in all_attempts if row.done in (0, 1)]
    validation_control = task_counts["validate"] + task_counts["gate"]
    total_tasks = len(all_tasks)
    summary: dict[str, Any] = {
        "as_of": args.as_of,
        "zenith_root": str(args.zenith_root),
        "projects": len(mission_rows),
        "states": dict(sorted(state_counts.items())),
        "categories": dict(sorted(category_counts.items())),
        "tasks_total": total_tasks,
        "tasks_by_type": dict(sorted(task_counts.items())),
        "task_status": dict(sorted(task_status.items())),
        "validation_control_nodes": validation_control,
        "validation_control_share": round(validation_control / total_tasks, 4) if total_tasks else 0,
        "superseded_share": round(task_status["superseded"] / total_tasks, 4) if total_tasks else 0,
        "attempts_total": len(all_attempts),
        "attempts_done": sum(row.done for row in valid_attempts),
        "attempts_failed": sum(1 - row.done for row in valid_attempts),
        "attempt_failure_share": round(sum(1 - row.done for row in valid_attempts) / len(valid_attempts), 4) if valid_attempts else 0,
        "attempts_missing_end_node": sum(row.missing_end_node for row in all_attempts),
        "attempts_rate_limited": sum(row.rate_limit for row in all_attempts),
        "attempts_requesting_attention": sum(row.request_attention for row in all_attempts),
        "robust_attempt_duration_median_seconds": round(percentile(robust_durations, 0.5), 3),
        "robust_attempt_duration_p90_seconds": round(percentile(robust_durations, 0.9), 3),
        "robust_agent_hours": round(sum(row["robust_agent_seconds"] for row in mission_rows) / 3600, 3),
        "robust_dispatch_wall_hours": round(sum(row["robust_batch_wall_seconds"] for row in mission_rows) / 3600, 3),
        "contracts": sum(row["contracts"] for row in mission_rows),
        "regressions": sum(row["regressions"] for row in mission_rows),
        "evidence_files": sum(row["evidence_files"] for row in mission_rows),
        "evidence_bytes": sum(row["evidence_bytes"] for row in mission_rows),
        "terminal_reviews": sum(row["terminal_reviews"] for row in mission_rows),
        "terminal_gap_headings": sum(row["terminal_gap_headings"] for row in mission_rows),
        "findings": len(findings),
        "provider_exact_mission_references": dict(
            sorted(Counter(row["agent"] for row in mentions).items())
        ),
    }
    for category in sorted(category_counts):
        rows = [row for row in mission_rows if row["category"] == category]
        category_tasks = sum(row["tasks_total"] for row in rows)
        category_control = sum(row["validate_tasks"] + row["gate_tasks"] for row in rows)
        summary[f"category_{category}"] = {
            "projects": len(rows),
            "done": sum(row["state"] == "done" for row in rows),
            "tasks": category_tasks,
            "validation_control_share": round(category_control / category_tasks, 4) if category_tasks else 0,
            "attempts": sum(row["attempts_total"] for row in rows),
            "attempt_failure_share": round(
                sum(row["attempts_failed"] for row in rows) / sum(row["attempts_total"] for row in rows), 4
            ) if sum(row["attempts_total"] for row in rows) else 0,
            "regressions": sum(row["regressions"] for row in rows),
            "terminal_gap_headings": sum(row["terminal_gap_headings"] for row in rows),
        }

    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    database_write(output / "findings.db", findings, coverage, mission_rows, all_attempts, all_tasks, mentions)
    return summary


def main() -> None:
    args = parse_args()
    summary = audit(args)
    db_path = args.output.resolve() / "findings.db"
    digest = hashlib.sha256(db_path.read_bytes()).hexdigest()
    print(json.dumps({"summary": summary, "findings_db_sha256": digest}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
