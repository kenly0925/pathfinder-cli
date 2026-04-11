from __future__ import annotations

import asyncio
import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Final

from rich import box
from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, RichLog, Static

from .theme import PALETTE, gradient_bar, pipe_bar


TABLE_BOX: Final = box.ASCII
BT_AGENT_LABEL: Final[str] = "\N{ROBOT FACE} BT Pathfinder"
MODEL_PROVIDER_LABEL: Final[str] = "Pathfinder AI"
MODEL_NAME_LABEL: Final[str] = "GPT-5.4"
TOKEN_BUDGET: Final[int] = 200_000
BASE_SESSION_TOKEN_ESTIMATE: Final[int] = 2400
FOOTER_HELP_MESSAGES: Final[tuple[str, ...]] = (
    "I can show you some features.",
    "Need a quick tour? Ask me for the command list.",
    "I can open apps, queues, and graph views.",
    "Try /help if you want the shortcut rundown.",
    "I can guide you through the current demo story.",
)
FOOTER_SPINNER_FRAMES: Final[tuple[str, ...]] = ("/", "-", "\\", "|")


@dataclass(frozen=True)
class ModuleSpec:
    key: str
    category: str
    label: str
    title: str
    overview: str
    status: str
    status_level: str
    metrics: tuple[tuple[str, int, str], ...]
    insights: tuple[str, ...]


@dataclass(frozen=True)
class OverviewRow:
    label: str
    status: str
    status_level: str
    metric_a_label: str
    metric_a_value: int
    metric_b_label: str
    metric_b_value: int


@dataclass(frozen=True)
class AttentionItem:
    severity: str
    subject: str
    summary: str
    emphasis_level: str
    module_key: str
    detail: str


@dataclass(frozen=True)
class HomeAction:
    key: str
    label: str
    summary: str
    module_key: str


@dataclass(frozen=True)
class GraphSpotlight:
    key: str
    label: str
    scope: str
    live_edge: str
    note: str
    tone: str


@dataclass(frozen=True)
class DashboardProfile:
    slices: tuple[tuple[str, int, str], ...]
    heatmap_rows: tuple[str, ...]
    heatmap_columns: tuple[str, ...]


@dataclass(frozen=True)
class PasswordSafeLane:
    label: str
    signal: str
    control: str
    note: str
    tone: str


@dataclass(frozen=True)
class PasswordSafeControlRow:
    label: str
    display_value: str
    bar_value: int
    trend: str
    note: str
    tone: str


@dataclass(frozen=True)
class PasswordSafeSessionRow:
    session_id: str
    channel: str
    state: str
    recording: str
    action: str
    tone: str


@dataclass(frozen=True)
class PasswordSafeSecretRow:
    label: str
    inventory: str
    bar_value: int
    delivery: str
    note: str
    tone: str


@dataclass(frozen=True)
class LiveSessionQueueRow:
    session_id: str
    operator: str
    target: str
    waiting: str
    approval: str
    signal: str
    tone: str


@dataclass(frozen=True)
class PendingApproval:
    key: str
    source: str
    request: str
    requester: str
    resource: str
    waiting: str
    ticket: str
    duration: str
    scope: str
    approver: str
    business_case: str
    note: str
    tone: str


@dataclass(frozen=True)
class AgentStatusRow:
    agent: str
    connector: str
    connector_level: str
    access: str
    role: str


@dataclass(frozen=True)
class InvestigationAction:
    key: str
    label: str
    summary: str
    result: str


@dataclass(frozen=True)
class InvestigationCase:
    key: str
    identity: str
    priority: str
    risk_score: int
    alert_reason: str
    linked_systems: tuple[str, ...]
    top_findings: tuple[str, ...]
    ai_checks: tuple[str, ...]
    known: tuple[str, ...]
    unverified: tuple[str, ...]
    blast_radius: str
    confidence: str
    evidence_gaps: tuple[str, ...]
    business_impact: str
    recommendation: str
    next_actions: tuple[InvestigationAction, ...]


@dataclass(frozen=True)
class VerificationOutcome:
    action_applied: str
    case_state: str
    status_level: str
    risk_after: int
    residual_access: str
    recommendation: str
    checks: tuple[tuple[str, str], ...]


@dataclass
class ConversationEntry:
    role: str
    text: str
    source_prompt: str = ""
    show_table: bool = False
    show_metrics: bool = False
    kind: str = "message"
    context_key: str = ""
    action_key: str = ""
    created_at: time.struct_time = field(default_factory=time.localtime)


@dataclass
class StoryContext:
    entity: str = "svc-backup-ops"
    environment: str | None = None
    time_range: str | None = None
    goal: str | None = None
    working_hypothesis: str = (
        "Suspicious privileged service-account activity overlaps an active production session and a reachable admin path."
    )
    active_session: str = "pra-2214"
    reachable_path: str = "grp-cloud-admins -> aws-prod-admin"
    risk_score: int = 91
    memory_active: bool = False
    role_label: str = "SOC Analyst II"
    current_scene: str = "story_ambiguity"
    prepared_approval_keys: tuple[str, ...] = ()
    incident_ticket: str | None = None
    approval_proof_requested: bool = False
    incident_review_staged: bool = False
    export_ready: bool = False
    top_asset: str = "prod-sql-07"
    selected_scope_label: str = "production | last 24 hours | triage + containment recommendation"


@dataclass(frozen=True)
class StoryModeReturnState:
    module_picker_active: bool
    home_navigation_active: bool
    investigation_navigation_active: bool
    investigation_case_key: str | None
    investigation_action_index: int
    detail_navigation_active: bool
    detail_view_key: str | None
    detail_action_index: int
    detail_return_view_key: str | None
    verification_profile_key: str | None


MODULES: Final[tuple[ModuleSpec, ...]] = (
    ModuleSpec(
        key="pathfinder",
        category="Platform",
        label="Pathfinder Platform",
        title="Pathfinder Platform Overview",
        overview=(
            "Unified identity telemetry and policy context across privileged access, "
            "endpoints, workforce identities, and support channels."
        ),
        status="Healthy with three connectors pending validation.",
        status_level="ok",
        metrics=(
            ("Identity Coverage", 86, "up 4%"),
            ("Cross-Signal Correlation", 74, "up 6%"),
            ("Policy Drift Resolved", 68, "up 2%"),
        ),
        insights=(
            "Prioritize high-risk identity pathways with privileged and endpoint overlap.",
            "Tune anomaly thresholds for stale sessions older than 24 hours.",
            "Complete remaining connector validation to improve lateral visibility.",
        ),
    ),
    ModuleSpec(
        key="pra",
        category="Privileged Access",
        label="Privileged Remote Access",
        title="Privileged Remote Access Overview",
        overview=(
            "Vendor and internal privileged sessions controlled through brokered access, "
            "session controls, and audit-ready recordings."
        ),
        status="Healthy with one live session flagged for review.",
        status_level="ok",
        metrics=(
            ("MFA-Enforced Sessions", 91, "flat"),
            ("Session Recording Coverage", 95, "up 1%"),
            ("Policy Exception Rate", 64, "down 3%"),
        ),
        insights=(
            "Reduce standing access by tightening approval windows for vendor sessions.",
            "Review policy exceptions triggered by emergency access workflows.",
            "Increase automated termination rules for idle privileged sessions.",
        ),
    ),
    ModuleSpec(
        key="password_safe",
        category="Privileged Access",
        label="Password Safe",
        title="Password Safe Overview",
        overview=(
            "Privileged account and secrets control plane for managed accounts, "
            "requests, monitored sessions, and non-human secret delivery."
        ),
        status="Healthy with two Password Safe approvals waiting and nine rotations due soon.",
        status_level="ok",
        metrics=(
            ("Managed Rotation Coverage", 88, "up 5%"),
            ("Approval Response SLA", 64, "down 3%"),
            ("Secrets Safe Coverage", 81, "up 6%"),
        ),
        insights=(
            "Prioritize overdue production checkouts and break-glass reviews.",
            "Expand change-after-release coverage for high-value managed accounts.",
            "Use Smart Rules and Discovery to reduce unmanaged privileged assets.",
        ),
    ),
    ModuleSpec(
        key="epm",
        category="Endpoint & Identity",
        label="Endpoint Privilege Management",
        title="Endpoint Privilege Management Overview",
        overview=(
            "Least-privilege enforcement on endpoints through elevation controls, "
            "application policies, and local admin reduction."
        ),
        status="Degraded: one sync failure is keeping eight endpoints out of compliance.",
        status_level="warn",
        metrics=(
            ("Least Privilege Coverage", 83, "up 3%"),
            ("Unauthorized Elevation Blocks", 79, "up 9%"),
            ("Local Admin Reduction", 71, "up 2%"),
        ),
        insights=(
            "Investigate the failed sync before policy drift expands beyond the current endpoint group.",
            "Segment policy baselines between engineering and finance endpoints.",
            "Close policy drift on unmanaged contractor workstations.",
        ),
    ),
    ModuleSpec(
        key="isi",
        category="Endpoint & Identity",
        label="Identity Security Insights",
        title="Identity Security Insights Overview",
        overview=(
            "Identity posture analytics to detect excessive access, risky relationships, "
            "and entitlement anomalies across hybrid identity systems."
        ),
        status="Healthy with seven urgent detections queued for analyst review.",
        status_level="ok",
        metrics=(
            ("Excess Access Reduction", 76, "up 8%"),
            ("High-Risk Identity Paths", 62, "down 6%"),
            ("Remediation Completion", 69, "up 4%"),
        ),
        insights=(
            "Focus on users with high privilege density and weak authentication patterns.",
            "Validate dormant access pathways connecting endpoint and cloud identities.",
            "Prioritize remediation of toxic combinations in finance and IT roles.",
        ),
    ),
    ModuleSpec(
        key="entitle",
        category="Endpoint & Identity",
        label="Entitle",
        title="Entitle Overview",
        overview=(
            "Just-in-time and least-privilege access controls for cloud entitlements, "
            "with approvals and policy guardrails for identity operations."
        ),
        status="Needs attention: JIT approval backlog exceeds threshold.",
        status_level="warn",
        metrics=(
            ("JIT Adoption", 73, "up 6%"),
            ("Approval SLA", 58, "down 5%"),
            ("Over-Privileged Identities", 66, "down 4%"),
        ),
        insights=(
            "Reduce JIT approval latency for high-frequency engineering workflows.",
            "Escalate overdue approvals tied to production resources.",
            "Enable stronger expiration defaults for temporary grants.",
        ),
    ),
    ModuleSpec(
        key="ad_bridge",
        category="Endpoint & Identity",
        label="AD Bridge",
        title="AD Bridge Overview",
        overview=(
            "Centralized identity and policy controls extending Active Directory-backed "
            "authentication and access management into Linux and Unix environments."
        ),
        status="Healthy with Linux host enrollment growth.",
        status_level="ok",
        metrics=(
            ("Managed Host Enrollment", 84, "up 7%"),
            ("Policy Compliance", 78, "up 3%"),
            ("Auth Failure Anomalies", 67, "down 2%"),
        ),
        insights=(
            "Review anomaly spikes on hosts with custom PAM configurations.",
            "Increase compliance checks for privileged shell access paths.",
            "Complete enrollment of remaining legacy Unix servers.",
        ),
    ),
    ModuleSpec(
        key="remote_support",
        category="Support",
        label="Remote Support",
        title="Remote Support Overview",
        overview=(
            "Secure remote support session controls with granular permissions, "
            "session logging, and identity-linked support workflows."
        ),
        status="Healthy with stable session throughput.",
        status_level="ok",
        metrics=(
            ("Verified Support Sessions", 89, "up 2%"),
            ("Session Audit Completeness", 94, "flat"),
            ("Escalation Response Time", 72, "up 3%"),
        ),
        insights=(
            "Audit unattended access usage for privileged support groups.",
            "Improve permission templates for high-risk endpoint support tasks.",
            "Align escalation workflows with identity risk scores.",
        ),
    ),
)


OVERVIEW_ROWS: Final[tuple[OverviewRow, ...]] = (
    OverviewRow("Identity Security Insights", "Healthy", "ok", "Urgent detections", 7, "High-risk identities", 4),
    OverviewRow("Password Safe", "Healthy", "ok", "Pending approval", 2, "Rotations overdue", 9),
    OverviewRow("PRA", "Healthy", "ok", "Sessions to review", 1, "Live sessions", 5),
    OverviewRow("EPM", "Degraded", "warn", "Sync failures", 1, "Noncompliant endpoints", 8),
    OverviewRow("Connectors", "Warning", "risk", "Stale connectors", 1, "Delayed sources", 1),
)


ATTENTION_ITEMS: Final[tuple[AttentionItem, ...]] = (
    AttentionItem(
        "critical",
        "svc-backup-ops",
        "risk 91 | unusual privileged activity | active session overlap",
        "risk",
        "pathfinder",
        "Start the AI-native investigation flow to scope production activity, compare approval evidence, and prepare a reviewer-facing response without executing the privileged change.",
    ),
    AttentionItem(
        "warning",
        "pra-2214",
        "approval evidence missing | review now",
        "warn",
        "pra",
        "Review the active privileged session metadata, compare it against the current approval trail, and decide whether a reviewer-facing revoke request should be prepared.",
    ),
    AttentionItem(
        "warning",
        "entitle request drift",
        "JIT approval mismatch | production scope",
        "warn",
        "entitle",
        "Compare the live production access path with the latest JIT approval artifact and stage a hold or escalation packet if the workflow no longer lines up cleanly.",
    ),
    AttentionItem(
        "medium",
        "linux-backup-policy",
        "elevation path changed | validate",
        "medium",
        "epm",
        "Validate whether the recent Linux elevation path change is expected, then confirm it does not widen the current backup-adjacent production path.",
    ),
)


HOME_ACTIONS: Final[tuple[HomeAction, ...]] = (
    HomeAction(
        "true_privilege_graph",
        "True Privilege graph",
        "Show the True Privilege graph for the risky AWS admin path so an analyst can dig in more.",
        "isi",
    ),
    HomeAction(
        "live_session_queue",
        "Live session queue",
        "Review active privileged sessions that still need analyst validation in Privileged Remote Access.",
        "pra",
    ),
    HomeAction(
        "pending_approvals",
        "Pending approvals",
        "Review production access approvals waiting in Password Safe and just-in-time workflows.",
        "password_safe",
    ),
    HomeAction(
        "portfolio_cover",
        "Portfolio cover",
        "Open a screenshot-ready Pathfinder CLI title card inspired by the BeyondTrust login screen.",
        "pathfinder",
    ),
    HomeAction(
        "temp_sunset_scene",
        "Temp sunset scene",
        "Open a temporary PATHFINDER CLI loading scene with a block wordmark, layered offsets, gradient bar, and geometric accents.",
        "pathfinder",
    ),
)

PORTFOLIO_COVER_WORDMARK: Final[tuple[str, ...]] = (
    " ____   _  _____ _   _ _____ ___ _   _ ____  _____ ____  ",
    "|  _ \\ / \\|_   _| | | |  ___|_ _| \\ | |  _ \\| ____|  _ \\ ",
    "| |_) / _ \\ | | | |_| | |_   | ||  \\| | | | |  _| | |_) |",
    "|  __/ ___ \\| | |  _  |  _|  | || |\\  | |_| | |___|  _ < ",
    "|_| /_/   \\_\\_| |_| |_|_|   |___|_| \\_|____/|_____|_| \\_\\",
    "   ____ _     ___ ",
    "  / ___| |   |_ _|",
    " | |   | |    | | ",
    " | |___| |___ | | ",
    "  \\____|_____|___|",
)

TEMP_SUNSET_SCENE_WORDMARK: Final[tuple[str, ...]] = (
    "PATHFINDER",
    "CLI",
)

TEMP_SUNSET_SCENE_FONT: Final[dict[str, tuple[str, ...]]] = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "11110", "10000", "10000", "10000", "11111"),
    "F": ("11111", "10000", "11110", "10000", "10000", "10000", "10000"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
}

GRAPH_SPOTLIGHTS: Final[tuple[GraphSpotlight, ...]] = (
    GraphSpotlight(
        "samantha-lee-prod-spine",
        "Samantha Lee production spine",
        "workforce -> Entra -> AWS -> PRA",
        "yes",
        "multi-hop cloud admin route with one live brokered session",
        "risk",
    ),
    GraphSpotlight(
        "contractor-support-overlap",
        "Contractor support overlap",
        "Okta -> support groups -> vault",
        "watch",
        "vendor support path overlaps with a password safe break-glass lane",
        "warn",
    ),
    GraphSpotlight(
        "dormant-service-branch",
        "Dormant service account branch",
        "AD -> legacy groups -> backup vault",
        "none",
        "low activity but still reaches backup administration paths",
        "accent",
    ),
)

GRAPH_FOCUS_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="return_to_graph_catalog",
        label="return to graph catalog",
        summary="go back to the graph catalog and choose another route",
        result="Returned focus to the graph catalog.",
    ),
)

MODULE_DASHBOARD_PROFILES: Final[dict[str, DashboardProfile]] = {
    "pathfinder": DashboardProfile(
        slices=(("correlated", 46, "teal"), ("watch", 31, "info"), ("stale", 23, "warn")),
        heatmap_rows=("identity", "policy", "connector", "response"),
        heatmap_columns=("Mon", "Tue", "Wed", "Thu", "Fri"),
    ),
    "pra": DashboardProfile(
        slices=(("verified", 58, "ok"), ("review", 27, "warn"), ("critical", 15, "risk")),
        heatmap_rows=("broker", "recording", "approval", "incident"),
        heatmap_columns=("00-06", "06-12", "12-18", "18-24"),
    ),
    "password_safe": DashboardProfile(
        slices=(("vaulted", 55, "teal"), ("pending", 29, "warn"), ("breakglass", 16, "risk")),
        heatmap_rows=("checkout", "rotation", "approval", "dual ctl"),
        heatmap_columns=("Mon", "Tue", "Wed", "Thu", "Fri"),
    ),
    "epm": DashboardProfile(
        slices=(("aligned", 51, "ok"), ("watch", 24, "info"), ("drift", 25, "risk")),
        heatmap_rows=("windows", "macos", "linux", "contract"),
        heatmap_columns=("Policy", "Elevate", "Drift", "Block", "Audit"),
    ),
    "isi": DashboardProfile(
        slices=(("resolved", 43, "teal"), ("watch", 32, "info"), ("toxic", 25, "risk")),
        heatmap_rows=("paths", "sign-in", "role", "session"),
        heatmap_columns=("Mon", "Tue", "Wed", "Thu", "Fri"),
    ),
    "entitle": DashboardProfile(
        slices=(("jit ok", 48, "ok"), ("pending", 34, "warn"), ("overdue", 18, "risk")),
        heatmap_rows=("aws", "azure", "gcp", "k8s"),
        heatmap_columns=("1h", "4h", "8h", "24h", "48h"),
    ),
    "ad_bridge": DashboardProfile(
        slices=(("enrolled", 57, "ok"), ("watch", 26, "info"), ("legacy", 17, "warn")),
        heatmap_rows=("linux", "unix", "ssh", "pam"),
        heatmap_columns=("Mon", "Tue", "Wed", "Thu", "Fri"),
    ),
    "remote_support": DashboardProfile(
        slices=(("verified", 61, "ok"), ("review", 24, "info"), ("escalated", 15, "warn")),
        heatmap_rows=("assist", "elevate", "unattend", "transfer"),
        heatmap_columns=("08", "10", "12", "14", "16"),
    ),
}

MODULE_SELECTION_GUIDANCE: Final[dict[str, str]] = {
    "pathfinder": "correlate platform-wide identity, policy, and connector signals",
    "pra": "review brokered sessions, approvals, and recording gaps",
    "password_safe": "review managed accounts, vault checkout pressure, and secrets controls",
    "epm": "trace endpoint elevation drift and least-privilege gaps",
    "isi": "investigate risky identity paths and toxic privilege overlap",
    "entitle": "clear JIT backlog and inspect temporary cloud grants",
    "ad_bridge": "audit Linux and Unix authentication pathways",
    "remote_support": "review support-session controls and escalation posture",
}

MODULE_DASHBOARD_CALLOUTS: Final[dict[str, str]] = {
    "pathfinder": "Signals below show which identity, policy, and connector lanes are carrying the most analyst attention right now.",
    "pra": "Use the charts to separate healthy brokered access from sessions that still need approval proof or live review.",
    "password_safe": "This view follows the main Password Safe lanes: onboarding, managed account hygiene, requests, monitored sessions, and Secrets Safe.",
    "epm": "This view is strongest when you need to compare policy drift against where elevation blocks are actually landing.",
    "isi": "The dashboard highlights where risky identity paths, sign-in anomalies, and remediation work are concentrating.",
    "entitle": "Use this app when temporary access is piling up and you need to see where approvals are aging out.",
    "ad_bridge": "This dashboard helps distinguish host enrollment progress from the Linux and PAM lanes where auth risk still pools.",
    "remote_support": "Use the mix and heat map together to spot when normal support volume starts leaning into higher-risk assist patterns.",
}

PASSWORD_SAFE_LANES: Final[tuple[PasswordSafeLane, ...]] = (
    PasswordSafeLane(
        "Discovery & onboarding",
        "2 active scans | 37 hosts staged",
        "Smart Rules + automated onboarding",
        "reduces unmanaged privileged assets before they bypass checkout controls",
        "info",
    ),
    PasswordSafeLane(
        "Managed accounts",
        "1,284 accounts | 76% disabled at rest",
        "rotation, next-change, change-after-release",
        "centralizes Windows, AD, Linux, database, and service-account control",
        "teal",
    ),
    PasswordSafeLane(
        "Requests & approvals",
        "2 waiting | 1 break-glass aging",
        "dual control + ticket-linked approval",
        "keeps password release tied to business justification and approver action",
        "warn",
    ),
    PasswordSafeLane(
        "Sessions",
        "4 active | 1 needs review",
        "proxy recording, lock, and terminate actions",
        "turns privileged checkout into observable session activity",
        "risk",
    ),
    PasswordSafeLane(
        "SSH keys & app creds",
        "147 SSH keys | 19 app mappings",
        "rotation policies + app-to-app credential control",
        "covers private keys and hard-coded credential removal work",
        "accent",
    ),
    PasswordSafeLane(
        "Secrets Safe & APIs",
        "318 secrets | 41 API-enabled accounts",
        "GUI, API, and automation retrieval",
        "extends Password Safe into non-human access and DevOps delivery",
        "violet",
    ),
)

PASSWORD_SAFE_CONTROL_ROWS: Final[tuple[PasswordSafeControlRow, ...]] = (
    PasswordSafeControlRow(
        "Auto-managed rotation",
        "88%",
        88,
        "up 5%",
        "most privileged credentials rotate on schedule or after controlled use",
        "ok",
    ),
    PasswordSafeControlRow(
        "Change Password After Release",
        "92%",
        92,
        "up 3%",
        "high-value accounts reset immediately after checkout or session close",
        "ok",
    ),
    PasswordSafeControlRow(
        "Disabled at Rest coverage",
        "76%",
        76,
        "up 8%",
        "service and break-glass accounts stay offline until explicitly requested",
        "info",
    ),
    PasswordSafeControlRow(
        "Next-change overdue",
        "9 accounts",
        34,
        "down 2",
        "legacy SQL and backup accounts still need remediation before the next review",
        "risk",
    ),
    PasswordSafeControlRow(
        "API-enabled managed accounts",
        "41 accounts",
        58,
        "up 4",
        "automation still depends on tightly-scoped vaulted retrieval and audit",
        "accent",
    ),
)

PASSWORD_SAFE_SESSION_ROWS: Final[tuple[PasswordSafeSessionRow, ...]] = (
    PasswordSafeSessionRow(
        "ps-rdp-prod-04",
        "RDP proxy",
        "active | approval evidence missing",
        "recording healthy",
        "lock or terminate if the request stays unverified",
        "risk",
    ),
    PasswordSafeSessionRow(
        "ps-ssh-core-02",
        "SSH proxy",
        "active | approved vendor policy",
        "key audit healthy",
        "monitor for check-in on release expiry",
        "ok",
    ),
    PasswordSafeSessionRow(
        "ps-breakglass-net",
        "admin session",
        "waiting | manager sign-off pending",
        "session not launched",
        "keep locked until break-glass approval is completed",
        "warn",
    ),
)

PASSWORD_SAFE_SECRET_ROWS: Final[tuple[PasswordSafeSecretRow, ...]] = (
    PasswordSafeSecretRow(
        "API tokens",
        "84 items",
        84,
        "GUI + API",
        "service teams retrieve these directly through controlled automation flows",
        "accent",
    ),
    PasswordSafeSecretRow(
        "Certificates",
        "36 items",
        36,
        "GUI + API",
        "certificate material is tracked alongside other privileged secrets",
        "info",
    ),
    PasswordSafeSecretRow(
        "JSON / XML bundles",
        "51 items",
        51,
        "GUI + API",
        "application payloads still need owner review before broader automation use",
        "teal",
    ),
    PasswordSafeSecretRow(
        "SSH keys",
        "147 keys",
        74,
        "proxy + desktop tools",
        "private keys are stored, rotated, and tied to recorded SSH activity",
        "ok",
    ),
    PasswordSafeSecretRow(
        "Workforce passwords",
        "62 accounts",
        62,
        "browser extension",
        "employee app passwords are growing, but coverage is still partial",
        "warn",
    ),
)

LIVE_SESSION_QUEUE_ROWS: Final[tuple[LiveSessionQueueRow, ...]] = (
    LiveSessionQueueRow("pra-2214", "amy.miller", "aws-prod-admin", "14m", "missing", "review now", "risk"),
    LiveSessionQueueRow("pra-2198", "victor.chen", "linux-breakglass", "9m", "late", "attestation drift", "warn"),
    LiveSessionQueueRow("pra-2182", "ops.vendor", "prd-sql-02", "4m", "confirmed", "recorded", "ok"),
    LiveSessionQueueRow("pra-2166", "maya.patel", "enclave-bastion", "22m", "pending", "idle window", "warn"),
)

PENDING_APPROVALS: Final[tuple[PendingApproval, ...]] = (
    PendingApproval(
        key="ps-prod-admin",
        source="Password Safe",
        request="prod-admin checkout",
        requester="samantha.lee",
        resource="win-admin-prod-04",
        waiting="19m",
        ticket="CHG-8821",
        duration="45m",
        scope="finance database patch validation",
        approver="dba-lead",
        business_case="validate a post-patch service restart on a production database node",
        note="dual control still waiting on the DBA lead",
        tone="risk",
    ),
    PendingApproval(
        key="ps-break-glass",
        source="Password Safe",
        request="break-glass review",
        requester="oncall.ops",
        resource="core-network vault",
        waiting="12m",
        ticket="INC-4102",
        duration="30m",
        scope="edge network failover investigation",
        approver="network-manager",
        business_case="review and release an emergency vault checkout for the network team",
        note="manager sign-off not recorded yet",
        tone="warn",
    ),
    PendingApproval(
        key="jit-aws-prod",
        source="Entitle",
        request="AWS production admin JIT",
        requester="jordan.rivera",
        resource="aws-prod-admin",
        waiting="7m",
        ticket="CHG-8830",
        duration="60m",
        scope="production Terraform rollback",
        approver="cloud-platform-lead",
        business_case="temporary cloud admin needed to verify a rollback and restore policy bindings",
        note="policy checks passed but approver has not responded",
        tone="risk",
    ),
    PendingApproval(
        key="jit-k8s-prod",
        source="Entitle",
        request="Kubernetes prod support",
        requester="mia.lopez",
        resource="eks-prod-support",
        waiting="4m",
        ticket="OPS-7741",
        duration="25m",
        scope="production incident triage",
        approver="site-reliability-lead",
        business_case="limited cluster access requested to inspect a failing production workload",
        note="scope is narrower, but the request is still production-linked",
        tone="accent",
    ),
)

PENDING_APPROVAL_DETAIL_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="approve_pending_request",
        label="✓ approve request",
        summary="approve the selected request after reviewing its details",
        result="Pending approval approved.",
    ),
    InvestigationAction(
        key="hold_pending_request",
        label="⚠ hold request",
        summary="pause the request and ask for more context",
        result="Pending approval moved to hold.",
    ),
    InvestigationAction(
        key="return_to_pending_approvals",
        label="↩ return to approval queue",
        summary="go back to the pending approvals table",
        result="Returned focus to the pending approvals queue.",
    ),
)

LIVE_SESSION_FOLLOWUP_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="inspect_target_activity",
        label="inspect target activity",
        summary="review recent actions on aws-prod-admin",
        result="Target activity view opened. Sensitive actions were observed within minutes of the session opening and still are not tied to approved work.",
    ),
    InvestigationAction(
        key="request_approval_proof",
        label="request approval proof",
        summary="ask the operator or approver to provide the missing work record",
        result="Approval proof request sent. No approved work record is currently attached to PRA-2214, and the assigned operator has been asked to justify the session.",
    ),
    InvestigationAction(
        key="revoke_session",
        label="revoke session",
        summary="terminate the active privileged session now",
        result="Session revoke prepared. PRA-2214 can be terminated immediately if no valid approval or business owner attestation is produced.",
    ),
    InvestigationAction(
        key="show_privilege_path",
        label="show privilege path",
        summary="trace the identity route that keeps aws-prod-admin reachable",
        result="Privilege path expanded. Current route: Okta -> Entra group inheritance -> AWS SSO -> AWS-Prod-Admin.",
    ),
    InvestigationAction(
        key="return_to_case_summary",
        label="return to case summary",
        summary="leave this step and return focus to the case summary",
        result="Returned focus to the case summary for amy.miller.",
    ),
)

TARGET_ACTIVITY_FOLLOWUP_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="show_privilege_path",
        label="show privilege path",
        summary="trace the dangerous route that keeps aws-prod-admin reachable",
        result="Privilege path review opened. The current route still resolves through grp-cloud-admins into aws-prod-admin while the PRA session remains active.",
    ),
    InvestigationAction(
        key="simulate_containment",
        label="simulate containment",
        summary="compare response options before taking action",
        result="Containment simulation opened. Current options compare immediate session revocation against breaking the inherited admin path.",
    ),
    InvestigationAction(
        key="revoke_session",
        label="revoke session",
        summary="terminate the active privileged session now",
        result="Session revoke prepared. PRA-2214 can be terminated immediately from Privileged Remote Access while incident review is opened.",
    ),
    InvestigationAction(
        key="open_incident_review",
        label="open incident review",
        summary="escalate the session to incident handling",
        result="Incident review draft opened. The session is active on aws-prod-admin with sensitive activity already observed and no approval confirmed.",
    ),
    InvestigationAction(
        key="request_approval_proof",
        label="request approval proof",
        summary="demand immediate evidence for the active privileged work",
        result="Approval proof request sent. No approved task is currently attached to the session, and the operator has been asked to justify the activity immediately.",
    ),
    InvestigationAction(
        key="return_to_session_summary",
        label="return to session summary",
        summary="leave the activity view and go back to the live session assessment",
        result="Returned focus to the live session summary for pra-2214.",
    ),
)

PRIVILEGE_PATH_FOLLOWUP_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="simulate_containment",
        label="simulate containment",
        summary="preview the impact of breaking the inherited admin link",
        result="Containment simulation prepared. Suspending the grp-cloud-admins -> aws-prod-admin inheritance would cut the exposed route without affecting Amy's standard workforce access.",
    ),
    InvestigationAction(
        key="revoke_session",
        label="revoke session",
        summary="terminate the active PRA session now",
        result="Session revoke prepared. PRA-2214 can be terminated immediately while the inherited admin link is reviewed.",
    ),
    InvestigationAction(
        key="remove_inherited_admin_link",
        label="remove inherited admin link",
        summary="break the inherited admin route before more privileged activity occurs",
        result="Admin link removal prepared. Suspending grp-cloud-admins -> aws-prod-admin would cut the inherited route while preserving Amy's standard workforce access.",
    ),
    InvestigationAction(
        key="open_incident_review",
        label="open incident review",
        summary="escalate the exposed admin path for incident handling",
        result="Incident review draft opened. The reachable admin chain remains active with a live PRA session still attached to the same identity path.",
    ),
    InvestigationAction(
        key="return_to_activity_review",
        label="return to activity review",
        summary="leave the path graph and go back to the target activity assessment",
        result="Returned focus to the target activity review for pra-2214.",
    ),
)

CONTAINMENT_FOLLOWUP_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="do_both_actions",
        label="do both now",
        summary="terminate the session and break the admin path together",
        result="Combined containment completed. PRA-2214 was revoked and the inherited admin link was removed for the fastest immediate and durable reduction.",
    ),
    InvestigationAction(
        key="revoke_session_now",
        label="revoke session now",
        summary="terminate the active session immediately",
        result="Session revoke completed. PRA-2214 was terminated to stop further privileged activity on aws-prod-admin.",
    ),
    InvestigationAction(
        key="remove_admin_link",
        label="remove admin link now",
        summary="break the inherited path into aws-prod-admin",
        result="Admin link removal completed. The grp-cloud-admins -> aws-prod-admin inheritance was removed to break the reachable admin path.",
    ),
    InvestigationAction(
        key="stage_incident_review",
        label="stage incident review",
        summary="prepare incident handling alongside containment",
        result="Incident review staged. Evidence from the session, activity timeline, and privilege path has been grouped for escalation if containment proceeds.",
    ),
    InvestigationAction(
        key="cancel_return",
        label="return",
        summary="leave containment planning and return to the previous step",
        result="Containment planning closed. Returned to the prior investigation step.",
    ),
)

VERIFICATION_FOLLOWUP_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="open_incident_review",
        label="open incident review",
        summary="escalate the contained case for incident handling",
        result="Incident review opened. The sensitive activity, containment decision, and residual questions were packaged for follow-up.",
    ),
    InvestigationAction(
        key="export_investigation_summary",
        label="export investigation summary",
        summary="export the case findings and containment outcome",
        result="Investigation summary exported. The case package now includes the activity evidence, chosen action, and verification outcome.",
    ),
    InvestigationAction(
        key="return_to_queue",
        label="return to queue",
        summary="leave the case and go back to prioritized investigations",
        result="Returned to queue. The current case remains available for later follow-up.",
    ),
    InvestigationAction(
        key="close_case_as_contained",
        label="close case as contained",
        summary="mark the case contained and end the active investigation flow",
        result="Case marked contained. The live exposure was reduced and the current investigation flow was closed.",
    ),
)


TABLE_TOKENS: Final[tuple[str, ...]] = ("table", "compare", "list", "breakdown", "report")
METRIC_TOKENS: Final[tuple[str, ...]] = ("metric", "metrics", "trend", "graph", "chart", "kpi", "health")
AGENT_STATUS_CORE_TOKENS: Final[frozenset[str]] = frozenset({"agent", "agents"})
AGENT_STATUS_HINT_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "status",
        "state",
        "health",
        "healthy",
        "connector",
        "connected",
        "disconnected",
        "connection",
        "connections",
        "token",
        "expiring",
        "auth",
        "authentication",
        "access",
        "role",
        "mode",
        "modes",
        "verified",
    }
)
AGENT_STATUS_ROWS: Final[tuple[AgentStatusRow, ...]] = (
    AgentStatusRow("identity security insights", "connected", "ok", "detections, true privilege graph", "analyze"),
    AgentStatusRow("okta", "connected", "ok", "sign-ins, mfa, groups", "observe"),
    AgentStatusRow("microsoft entra id", "token expiring", "warn", "risk, app roles, directory changes", "observe"),
    AgentStatusRow("ad bridge", "connected", "ok", "ad auth, unix/linux policy", "observe"),
    AgentStatusRow("endpoint privilege management", "connected", "ok", "host policy, elevation events", "observe"),
    AgentStatusRow("password safe", "connected", "ok", "secrets, rotation, managed accounts", "observe + act"),
    AgentStatusRow("privileged remote access", "connected", "ok", "live sessions, approvals, recordings", "observe + act"),
    AgentStatusRow("entitle", "connected", "ok", "jit grants, cloud roles, saas access", "observe + act"),
    AgentStatusRow("servicenow", "connected", "ok", "tickets, change approvals, case actions", "act"),
    AgentStatusRow("audit evidence", "connected", "ok", "summary, proof log, exports", "analyze"),
)
COMMAND_HELP: Final[tuple[tuple[str, str], ...]] = (
    ("/help", "Show this command reference."),
    ("/app", "Show the app list."),
    ("/app <name|number>", "Jump directly to an app."),
    ("/module <name|number>", "Alias for /app."),
    ("/agent", "Show the current agent roster."),
    ("/agent add <name>", "Add a new agent with a disconnected connector."),
    ("/agent remove <name>", "Remove an agent from the current roster."),
    ("/clear", "Clear conversation history across all apps."),
    ("/reset", "Clear conversation history for the current app."),
)
STORY_ENTRY_PROMPT: Final[str] = "/investigate suspicious lateral movement tied to a service account"
STORY_CONTEXT_KEY: Final[str] = "svc-backup-ops-story"
STORY_ROLE_CAPABILITIES: Final[tuple[str, ...]] = (
    "review detections",
    "inspect identity context",
    "inspect endpoint context",
    "inspect privileged session metadata",
    "compare approval state",
    "create tickets and prepare requests",
)
STORY_ROLE_RESTRICTIONS: Final[tuple[str, ...]] = (
    "full session contents",
    "stored credential details",
    "restricted secrets",
    "sensitive identity notes",
    "final session termination",
    "direct path suspension",
)
STORY_AMBIGUITY_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_scope_default_recommend",
        label="set production / 24h / triage + containment",
        summary="resolve the missing scope with the recommended preset",
        result="Scope resolved. Production, last 24 hours, triage plus containment recommendation.",
    ),
    InvestigationAction(
        key="story_scope_default_triage",
        label="set production / 24h / triage only",
        summary="resolve the missing scope without containment guidance",
        result="Scope resolved. Production, last 24 hours, triage only.",
    ),
    InvestigationAction(
        key="story_customize_scope",
        label="customize scope",
        summary="enter a custom environment, time range, or goal",
        result="Scope customization opened.",
    ),
    InvestigationAction(
        key="story_show_role_limits",
        label="show role limits",
        summary="review what this operator can inspect versus what stays blocked",
        result="Role limits loaded for the current operator.",
    ),
    InvestigationAction(
        key="story_return_home",
        label="return",
        summary="leave the story entry and go back to the home view",
        result="Returned to the home view.",
    ),
)
STORY_SCOPE_CONFIRM_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_run_investigation",
        label="run investigation",
        summary="query the selected identity, session, approval, and entitlement signals",
        result="Investigation started for svc-backup-ops.",
    ),
    InvestigationAction(
        key="story_adjust_scope",
        label="adjust scope",
        summary="change the environment, time range, or goal before running",
        result="Returned to scope collection.",
    ),
    InvestigationAction(
        key="story_show_memory_state",
        label="show memory state",
        summary="review the session-scoped investigation memory now in use",
        result="Session memory state loaded.",
    ),
    InvestigationAction(
        key="story_return_to_ambiguity",
        label="return",
        summary="return to the ambiguity handling screen",
        result="Returned to ambiguity handling.",
    ),
)
STORY_SCOPE_CUSTOM_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_scope_default_recommend",
        label="set production / 24h / triage + containment",
        summary="apply the recommended production scope without typing a custom variant",
        result="Scope resolved. Production, last 24 hours, triage plus containment recommendation.",
    ),
    InvestigationAction(
        key="story_show_role_limits",
        label="show role limits",
        summary="review what the current analyst can and cannot do",
        result="Role limits loaded for the current operator.",
    ),
    InvestigationAction(
        key="story_return_to_ambiguity",
        label="return",
        summary="return to the ambiguity handling screen",
        result="Returned to ambiguity handling.",
    ),
)
STORY_ROLE_LIMITS_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_return_to_ambiguity",
        label="return",
        summary="return to the ambiguity handling screen",
        result="Returned to ambiguity handling.",
    ),
)
STORY_MEMORY_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_return_to_scope",
        label="return",
        summary="return to the scope confirmation view",
        result="Returned to scope confirmation.",
    ),
)
STORY_FINDINGS_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_assess_session_relatedness",
        label="assess session relatedness",
        summary="measure whether the active PRA session is likely tied to the same service-account activity",
        result="Session relatedness analysis opened with explicit confidence and evidence gaps.",
    ),
    InvestigationAction(
        key="story_show_privilege_path",
        label="show privilege path",
        summary="open the focused service-account path into production admin",
        result="Privilege path loaded for svc-backup-ops.",
    ),
    InvestigationAction(
        key="story_show_approval_evidence",
        label="show approval evidence",
        summary="compare PRA, Password Safe, and Entitle evidence for the current access",
        result="Approval evidence comparison opened.",
    ),
    InvestigationAction(
        key="story_list_affected_assets",
        label="list affected assets",
        summary="group the affected production assets by severity and overlap",
        result="Affected assets grouped by severity.",
    ),
    InvestigationAction(
        key="story_open_incident_review",
        label="open incident review draft",
        summary="prepare an incident review draft without executing any privileged change",
        result="Incident review draft opened.",
    ),
    InvestigationAction(
        key="story_return_to_scope",
        label="return",
        summary="return to the planner preview and scoped context",
        result="Returned to scope confirmation.",
    ),
)
STORY_SESSION_RELATEDNESS_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_list_affected_assets",
        label="show affected assets",
        summary="group assets touched by path overlap and session overlap",
        result="Affected assets grouped by severity.",
    ),
    InvestigationAction(
        key="story_show_approval_evidence",
        label="show approval evidence",
        summary="compare the approval trail against the live session and path",
        result="Approval evidence comparison opened.",
    ),
    InvestigationAction(
        key="story_compare_access_change_options",
        label="show path break options",
        summary="compare the BeyondTrust-native containment moves available",
        result="Containment options loaded.",
    ),
    InvestigationAction(
        key="story_request_approval_proof",
        label="request approval proof",
        summary="prepare a request for missing approval evidence without revealing blocked data",
        result="Approval proof request prepared and the evidence screen was refreshed.",
    ),
    InvestigationAction(
        key="story_return_to_findings",
        label="return",
        summary="return to the findings summary",
        result="Returned to findings summary.",
    ),
)
STORY_APPROVAL_EVIDENCE_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_compare_access_change_options",
        label="show path break options",
        summary="move from evidence review to containment comparison",
        result="Containment options loaded.",
    ),
    InvestigationAction(
        key="story_open_incident_review",
        label="open incident review draft",
        summary="prepare an incident review draft from the current evidence set",
        result="Incident review draft opened.",
    ),
    InvestigationAction(
        key="story_return_to_findings",
        label="return",
        summary="return to the findings summary",
        result="Returned to findings summary.",
    ),
)
STORY_PRIVILEGE_PATH_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_compare_access_change_options",
        label="show path break options",
        summary="compare the safest immediate containment options around the live path",
        result="Containment options loaded.",
    ),
    InvestigationAction(
        key="story_show_approval_evidence",
        label="show approval evidence",
        summary="compare the path with the current approval state and access artifacts",
        result="Approval evidence comparison opened.",
    ),
    InvestigationAction(
        key="story_list_affected_assets",
        label="list affected assets",
        summary="show which assets sit on the current privileged path",
        result="Affected assets grouped by severity.",
    ),
    InvestigationAction(
        key="story_return_to_findings",
        label="return",
        summary="return to the findings summary",
        result="Returned to findings summary.",
    ),
)
STORY_ASSETS_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_show_top_asset_detail",
        label="show top asset detail",
        summary="inspect the highest-priority asset with the current session context applied",
        result="Top asset detail opened.",
    ),
    InvestigationAction(
        key="story_compare_access_change_options",
        label="show path break options",
        summary="compare access change options against the current asset grouping",
        result="Containment options loaded.",
    ),
    InvestigationAction(
        key="story_compare_access_change_options",
        label="compare access change options",
        summary="review the safest immediate containment path across the affected assets",
        result="Containment options loaded.",
    ),
    InvestigationAction(
        key="story_open_incident_review",
        label="open incident review draft",
        summary="prepare an incident review draft from the grouped asset evidence",
        result="Incident review draft opened.",
    ),
    InvestigationAction(
        key="story_return_to_findings",
        label="return",
        summary="return to the findings summary",
        result="Returned to findings summary.",
    ),
)
STORY_ASSET_DETAIL_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_compare_access_change_options",
        label="show path break options",
        summary="compare the safest immediate containment moves for the top asset",
        result="Containment options loaded.",
    ),
    InvestigationAction(
        key="story_open_incident_review",
        label="open incident review draft",
        summary="prepare an incident review draft centered on the top asset",
        result="Incident review draft opened.",
    ),
    InvestigationAction(
        key="story_return_to_assets",
        label="return",
        summary="return to the affected asset grouping",
        result="Returned to the grouped asset view.",
    ),
)
STORY_CONTAINMENT_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_prepare_session_revoke_request",
        label="prepare session revoke request",
        summary="stage a reviewer-facing request to terminate the active PRA session",
        result="Prepared a reviewer-facing session revoke request.",
    ),
    InvestigationAction(
        key="story_prepare_path_suspension_request",
        label="prepare path suspension request",
        summary="stage a reviewer-facing request to suspend the reachable admin path",
        result="Prepared a reviewer-facing path suspension request.",
    ),
    InvestigationAction(
        key="story_prepare_combined_response_packet",
        label="prepare combined response packet",
        summary="stage both privileged actions and package the evidence for approval",
        result="Prepared a combined response packet for approval.",
    ),
    InvestigationAction(
        key="story_stage_incident_review",
        label="stage incident review",
        summary="prepare the incident review artifacts without executing a privileged action",
        result="Incident review staged.",
    ),
    InvestigationAction(
        key="story_return_to_findings",
        label="return",
        summary="return to the findings summary",
        result="Returned to findings summary.",
    ),
)
STORY_INCIDENT_REVIEW_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_open_approval_queue",
        label="open approval queue",
        summary="move from the incident draft to the approval queue view",
        result="Approval queue opened.",
    ),
    InvestigationAction(
        key="story_show_memory_state",
        label="show memory state",
        summary="review the active story memory feeding the incident draft",
        result="Session memory state loaded.",
    ),
    InvestigationAction(
        key="story_return_to_findings",
        label="return",
        summary="return to the findings summary",
        result="Returned to findings summary.",
    ),
)
STORY_HANDOFF_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_open_approval_queue",
        label="open approval queue",
        summary="review the staged privileged requests in the approval queue",
        result="Approval queue opened.",
    ),
    InvestigationAction(
        key="story_open_incident_review",
        label="open incident review",
        summary="open the draft incident review attached to the prepared packet",
        result="Incident review draft opened.",
    ),
    InvestigationAction(
        key="story_export_summary",
        label="export summary",
        summary="prepare a concise evidence summary for handoff and approval",
        result="Investigation summary export prepared.",
    ),
    InvestigationAction(
        key="story_show_memory_state",
        label="show memory state",
        summary="review the session memory still held for the live story",
        result="Session memory state loaded.",
    ),
    InvestigationAction(
        key="story_return_home_keep_memory",
        label="return home",
        summary="leave the handoff view but keep the active story in session memory",
        result="Returned home with the active investigation still in memory.",
    ),
)
STORY_APPROVAL_QUEUE_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_review_prepared_request",
        label="review request",
        summary="open the first staged reviewer-facing request in detail view",
        result="Prepared request opened for detailed review.",
    ),
    InvestigationAction(
        key="story_hold_prepared_request",
        label="hold request",
        summary="place the first staged request on hold pending more reviewer context",
        result="Prepared request moved to hold.",
    ),
    InvestigationAction(
        key="story_return_home_keep_memory",
        label="return home",
        summary="return to the home dashboard while keeping the current story in memory",
        result="Returned home with the active investigation still in memory.",
    ),
)
STORY_EXPORT_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_open_approval_queue",
        label="open approval queue",
        summary="review the staged requests after exporting the summary",
        result="Approval queue opened.",
    ),
    InvestigationAction(
        key="story_return_home_keep_memory",
        label="return home",
        summary="return to the dashboard while preserving the current story memory",
        result="Returned home with the active investigation still in memory.",
    ),
)
STORY_MENU_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction("story_mode_probabilistic", "Probabilistic UX thinking", "Open the probabilistic UX design lens", "Probabilistic UX thinking opened."),
    InvestigationAction("story_mode_behavior", "Behavior spec", "Open the behavior specification lens", "Behavior spec opened."),
    InvestigationAction("story_mode_memory", "Memory design", "Open the memory design lens", "Memory design opened."),
    InvestigationAction("story_mode_boundary", "Boundary and control", "Open the boundary and control lens", "Boundary and control opened."),
    InvestigationAction("story_mode_structure", "Full AI-native structure", "Open the full AI-native structure map", "Full AI-native structure opened."),
    InvestigationAction("story_mode_summary", "Demo story summary", "Open the demo story summary poster", "Demo story summary opened."),
)
STORY_MENU_RETURN_ACTIONS: Final[tuple[InvestigationAction, ...]] = (
    InvestigationAction(
        key="story_mode_return",
        label="return to story menu",
        summary="go back to the hidden story presentation menu",
        result="Returned to story menu.",
    ),
)
ACTIONABLE_ITEMS_TOKENS: Final[frozenset[str]] = frozenset({"actionable", "item", "items"})
INVESTIGATION_CASES: Final[dict[str, InvestigationCase]] = {
    "amy.miller": InvestigationCase(
        key="amy.miller",
        identity="amy.miller",
        priority="critical",
        risk_score=92,
        alert_reason="unusual sign-in with a reachable path to privileged cloud access",
        linked_systems=("okta", "entra id", "aws-prod-admin", "pra-2214"),
        top_findings=(
            "new geo and device pattern on the latest sign-in",
            "reachable inheritance path into AWS production admin",
            "one live privileged session still linked to the same identity chain",
        ),
        ai_checks=(
            "correlated the Okta sign-in with Entra risk and True Privilege graph data",
            "checked MFA outcome, device profile, and recent group inheritance",
            "matched the live PRA session against the same identity chain",
        ),
        known=(
            "mfa completed, but from a new device profile",
            "the admin path is still reachable through current group inheritance",
            "the privileged session remains open and unverified",
        ),
        unverified=(
            "whether the sign-in was user initiated",
            "whether the live session maps to approved work",
            "whether the latest Entra role changes are fully reflected",
        ),
        blast_radius="production AWS admin remains reachable from a workforce identity with an active privileged session",
        confidence="high",
        evidence_gaps=(
            "entra id role feed delayed 11m",
            "session owner attestation still pending",
            "endpoint context is older than the latest sign-in",
        ),
        business_impact="this path can reach production cloud administration and backup operations without a confirmed business need",
        recommendation="Verify the live session first. If the sign-in is not expected, break the admin path next.",
        next_actions=(
            InvestigationAction(
                key="view_live_session",
                label="view live session",
                summary="inspect the active privileged session and approval state",
                result="Live session loaded. PRA-2214 remains active, and no approved work record has been confirmed yet.",
            ),
            InvestigationAction(
                key="review_signin_timeline",
                label="review sign-in timeline",
                summary="compare device, geo, and mfa sequence",
                result="Sign-in timeline loaded. The alerting sign-in followed a new device registration and completed MFA 3 minutes before the PRA session opened.",
            ),
            InvestigationAction(
                key="compare_role_changes",
                label="compare recent role changes",
                summary="check whether access was added through recent entitlement drift",
                result="Recent role comparison loaded. A nested group update in Microsoft Entra ID appears related, but the feed delay means the latest delta is still unconfirmed.",
            ),
            InvestigationAction(
                key="show_privilege_path",
                label="show privilege path",
                summary="graph the inherited route into AWS production admin",
                result="Privilege path expanded. Current route: Okta -> Entra group inheritance -> AWS SSO -> AWS-Prod-Admin.",
            ),
            InvestigationAction(
                key="simulate_containment",
                label="simulate containment",
                summary="preview the access impact of removing the risky path",
                result="Containment simulation prepared. Expiring the inherited admin path would block AWS production admin access without affecting Amy's standard workforce apps.",
            ),
            InvestigationAction(
                key="return_to_queue",
                label="return to queue",
                summary="leave the case summary and return to the actionable queue",
                result="Returned focus to the actionable queue.",
            ),
        ),
    ),
    "entra id feed": InvestigationCase(
        key="entra id feed",
        identity="entra id feed",
        priority="warning",
        risk_score=68,
        alert_reason="role and app change events are delayed, which may hide fresh privilege updates",
        linked_systems=("microsoft entra id", "identity security insights", "entitle"),
        top_findings=(
            "connector delay is now 11 minutes",
            "recent directory and app role changes are not fully reconciled",
            "two downstream correlation jobs are waiting on the refresh",
        ),
        ai_checks=(
            "checked connector freshness against the expected sync window",
            "compared queued role events with the last completed import",
            "mapped downstream analytics waiting on fresh Entra evidence",
        ),
        known=(
            "the connector is still authenticated",
            "the backlog is growing across role and app events",
            "risk decisions are currently using stale directory evidence",
        ),
        unverified=(
            "the exact role delta since the delay began",
            "whether any new privileged grants are hidden in the backlog",
        ),
        blast_radius="identity-based risk scoring and entitlement reviews may miss the newest Entra changes",
        confidence="medium",
        evidence_gaps=(
            "entra id event delta is delayed",
            "app role export has not completed the latest cycle",
        ),
        business_impact="stale directory evidence can delay response to new privilege grants or suspicious app access",
        recommendation="restore feed freshness before relying on Entra-backed exposure decisions",
        next_actions=(
            InvestigationAction("show_privilege_path", "show privilege path", "see which risky paths depend on Entra refresh", "Privilege path dependencies loaded. Three active path calculations are waiting on fresh Entra role data."),
            InvestigationAction("review_signin_timeline", "review sign-in timeline", "check whether sign-in anomalies overlap the feed delay", "Sign-in timeline overlay loaded. Two recent anomalies occurred after the Entra delay window opened."),
            InvestigationAction("verify_active_session", "verify active session", "confirm no high-risk session depends on stale Entra evidence", "Session dependency check completed. One privileged session uses access that should be re-evaluated after the feed catches up."),
            InvestigationAction("compare_role_changes", "compare recent role changes", "diff the last known role state against pending updates", "Role change comparison started. Pending Entra role events are queued but not yet reconciled into the graph."),
            InvestigationAction("simulate_containment", "simulate containment", "preview impact of pausing Entra-based automated actions", "Containment simulation prepared. Pausing Entra-driven auto-decisions would reduce false confidence but slow some remediation workflows."),
            InvestigationAction("open_linked_account_map", "open linked account map", "show systems waiting on the delayed connector", "Linked dependency map opened. Identity Security Insights and Entitle are the main downstream consumers."),
        ),
    ),
    "privileged session": InvestigationCase(
        key="privileged session",
        identity="privileged session",
        priority="warning",
        risk_score=79,
        alert_reason="one flagged privileged session remains open without completed verification",
        linked_systems=("privileged remote access", "password safe", "managed server prd-sql-02"),
        top_findings=(
            "session remains open past the expected review window",
            "command pattern diverged from the original ticket summary",
            "no attestation has been recorded by the session owner",
        ),
        ai_checks=(
            "checked the live PRA session state and recorder health",
            "compared command activity with the linked ticket summary",
            "validated the session path back to approved credentials and host scope",
        ),
        known=(
            "the session is still active",
            "the access path was approved earlier in the change window",
            "recording and command audit are available",
        ),
        unverified=(
            "whether the current activity is still in scope",
            "whether a second operator joined outside the approved plan",
        ),
        blast_radius="the session still has privileged reach into a production managed server",
        confidence="medium-high",
        evidence_gaps=(
            "owner verification pending",
            "change-ticket narrative has not been updated",
        ),
        business_impact="an unverified privileged session can extend production access beyond the approved task",
        recommendation="review the session immediately and terminate it if the operator cannot validate current activity",
        next_actions=(
            InvestigationAction("show_privilege_path", "show privilege path", "trace how the session reached the managed server", "Privilege path loaded. The session was brokered through PRA with Password Safe credentials to prd-sql-02."),
            InvestigationAction("review_signin_timeline", "review sign-in timeline", "compare session start with operator authentication events", "Session timeline loaded. The operator authenticated 6 minutes before the flagged command sequence began."),
            InvestigationAction("verify_active_session", "verify active session", "check the live session state and owner attestation", "Active session check completed. The session is live, recording is healthy, and owner attestation is still missing."),
            InvestigationAction("compare_role_changes", "compare recent role changes", "confirm no late privilege change widened the session scope", "Role comparison loaded. No new role grants were detected after the session started."),
            InvestigationAction("simulate_containment", "simulate containment", "preview the impact of terminating the live session", "Containment preview ready. Terminating the session would stop current production access without affecting approved standby access."),
            InvestigationAction("open_linked_account_map", "open linked account map", "show linked credentials, hosts, and ticket objects", "Linked account map opened. The session ties to one managed account, one production host, and one change ticket."),
        ),
    ),
    "svc-backup-old": InvestigationCase(
        key="svc-backup-old",
        identity="svc-backup-old",
        priority="medium",
        risk_score=61,
        alert_reason="dormant privileged account has no recorded disposition and still retains elevated access",
        linked_systems=("password safe", "backup vault", "active directory"),
        top_findings=(
            "no interactive use in the last 93 days",
            "vault rotation is behind the current policy target",
            "the account still maps to backup administration",
        ),
        ai_checks=(
            "checked recent sign-in and checkout activity",
            "reviewed current vault rotation and enabled state",
            "mapped the account to remaining backup administration scope",
        ),
        known=(
            "the account is still enabled",
            "backup-admin scope remains assigned",
            "no current incident references the account",
        ),
        unverified=(
            "whether the backup workflow still needs the account",
            "whether ownership has shifted to another team",
        ),
        blast_radius="dormant backup administration access remains available if the account is re-used",
        confidence="medium",
        evidence_gaps=(
            "service owner disposition is overdue",
            "current backup job dependency has not been reconfirmed",
        ),
        business_impact="unused privileged service accounts increase the risk of silent reuse in backup and recovery systems",
        recommendation="confirm ownership, then retire or rotate the account before the next review cycle",
        next_actions=(
            InvestigationAction("show_privilege_path", "show privilege path", "trace the privileged systems still reachable", "Privilege path loaded. The account still reaches backup vault administration through a legacy AD group."),
            InvestigationAction("review_signin_timeline", "review sign-in timeline", "check for any recent service or interactive use", "Usage timeline loaded. No recent interactive sign-ins were found, and the last service auth was 93 days ago."),
            InvestigationAction("verify_active_session", "verify active session", "confirm the account is not in use right now", "Active-use check completed. No current session or credential checkout is associated with svc-backup-old."),
            InvestigationAction("compare_role_changes", "compare recent role changes", "review whether the account lost or gained any backup roles", "Role comparison loaded. No meaningful role change was recorded in the last 30 days."),
            InvestigationAction("simulate_containment", "simulate containment", "preview the impact of disabling the account", "Containment preview ready. Disabling the account would not interrupt any currently observed backup activity."),
            InvestigationAction("open_linked_account_map", "open linked account map", "show linked vault objects and ownership records", "Linked account map opened. The account is tied to one vault record, one AD object, and an overdue owner review."),
        ),
    ),
}


class PathfinderPrototypeApp(App[None]):
    CSS_PATH = "styles.tcss"
    TITLE = "Pathfinder CLI"
    SUB_TITLE = "BeyondTrust Dashboard"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("up", "picker_up", "", show=False, priority=True),
        Binding("down", "picker_down", "", show=False, priority=True),
    ]

    def __init__(self, authenticated_user: str | None = None) -> None:
        super().__init__()
        self.authenticated_user = authenticated_user or "developer"
        self.user_role = "SOC Analyst II"
        self.agent_status_rows = list(AGENT_STATUS_ROWS)
        self.pending_approvals = list(PENDING_APPROVALS)
        self.module_index = 0
        self.module_picker_active = False
        self.module_picker_index = 0
        self.home_navigation_active = False
        self.home_selection_index = self._home_selection_count() - 1
        self.investigation_navigation_active = False
        self.investigation_case_key: str | None = None
        self.investigation_action_index = 0
        self.detail_navigation_active = False
        self.detail_view_key: str | None = None
        self.detail_action_index = 0
        self.detail_return_view_key: str | None = None
        self.verification_profile_key: str | None = None
        self.investigation_state_by_module: dict[str, tuple[str, int] | None] = {
            module.key: None for module in MODULES
        }
        self.detail_state_by_module: dict[str, tuple[str, int, str | None] | None] = {
            module.key: None for module in MODULES
        }
        self.verification_profile_by_module: dict[str, str | None] = {
            module.key: None for module in MODULES
        }
        self.pending_approval_state_by_key: dict[str, str] = {
            approval.key: "waiting" for approval in PENDING_APPROVALS
        }
        self.story_context_by_module: dict[str, StoryContext | None] = {
            module.key: None for module in MODULES
        }
        self.story_mode_return_state_by_module: dict[str, StoryModeReturnState | None] = {
            module.key: None for module in MODULES
        }
        self.story_context: StoryContext | None = None
        self.processing = False
        self.processing_message = ""
        self.chrome_tick = 0
        self.last_update_at = time.perf_counter()
        self.histories: dict[str, list[ConversationEntry]] = {module.key: [] for module in MODULES}
        self._initial_main_log_render_pending = True

    def compose(self) -> ComposeResult:
        with Vertical(id="root"):
            yield Static(id="top-spacer")
            with Horizontal(id="top-bar"):
                yield Static(id="top-title")
                yield Static(id="top-meta")
            yield Static(classes="section-divider", id="module-divider")
            yield RichLog(id="main-log", auto_scroll=True, highlight=False, wrap=True, markup=False)

            with Vertical(id="command-bar"):
                yield Static(id="typing-indicator")
                yield Input(
                    placeholder="",
                    id="command-input",
                )
                yield Static(id="footer-divider", classes="command-divider")
                with Horizontal(id="footer-row"):
                    yield Static(id="command-hint")
                    yield Static(id="session-status")

    def on_mount(self) -> None:
        self._render_current_module()
        self._refresh_chrome()
        self.set_interval(0.35, self._tick_ui)
        self.query_one("#command-input", Input).focus()

    def on_key(self, event: events.Key) -> None:
        if self._story_mode_active() and event.key in {"escape", "q"}:
            event.prevent_default()
            event.stop()
            current_module = self._active_module()
            if self.detail_view_key == "story_menu":
                self._close_story_mode(current_module.key)
            else:
                self.detail_navigation_active = True
                self.detail_view_key = "story_menu"
                self.detail_action_index = 0
                self.detail_return_view_key = None
                self._remember_detail_state(current_module.key)
            self._mark_updated()
            self._render_current_module()
            return

        if event.key != "enter" or self.processing:
            return

        command_input = self.query_one("#command-input", Input)
        if command_input.value.strip() or not self._has_navigation_context():
            return

        event.prevent_default()
        event.stop()
        self.action_activate_selection()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "command-input":
            return

        prompt = event.value.strip()
        event.input.value = ""
        if not prompt and self._has_navigation_context():
            self.action_activate_selection()
            return
        if not prompt or self.processing:
            return

        self.home_navigation_active = False
        self.module_picker_active = False
        self.run_worker(self._process_prompt(prompt), exclusive=True, thread=False)

    async def _process_prompt(self, prompt: str) -> None:
        command_input = self.query_one("#command-input", Input)
        command_input.disabled = True
        self.processing = True
        self.processing_message = ""

        try:
            if self._story_prompt_matches_entry(prompt):
                active_module = self._active_module()
                self.processing_message = "Checking investigation scope..."
                self._append_history(
                    active_module.key,
                    ConversationEntry(role="user", text=prompt, source_prompt=prompt),
                )
                self._mark_updated()
                self._render_current_module()
                await self._animate_processing()
                self._start_story_from_prompt(active_module.key, prompt)
                self.processing = False
                self.processing_message = ""
                self._mark_updated()
                self._render_current_module()
                return

            if prompt.startswith("/"):
                self._handle_utility_command(prompt)
                self.processing = False
                self.processing_message = ""
                self._mark_updated()
                self._render_current_module()
                return

            active_module = self._active_module()
            self.processing_message = f"Analyzing {active_module.label}..."
            self._append_history(
                active_module.key,
                ConversationEntry(role="user", text=prompt, source_prompt=prompt),
            )

            self._mark_updated()
            self._render_current_module()
            await self._animate_processing()

            if self._handle_story_followup_prompt(active_module.key, prompt):
                self.processing = False
                self.processing_message = ""
                self._mark_updated()
                self._render_current_module()
                return

            if self._matches_actionable_items_request(prompt):
                self.home_navigation_active = True
                self._clear_investigation_state(active_module.key)
                self.home_selection_index = 0
                self._append_history(
                    active_module.key,
                    ConversationEntry(
                        role="assistant",
                        text="Actionable items refreshed. Use Up/Down to select a case and Enter to open investigation.",
                        source_prompt=prompt,
                        kind="actionable_items",
                    ),
                )
                self.processing = False
                self.processing_message = ""
                self._mark_updated()
                self._render_current_module()
                return

            summary, show_table, show_metrics = self._build_response(prompt, active_module)
            self._append_history(
                active_module.key,
                ConversationEntry(
                    role="assistant",
                    text=summary,
                    source_prompt=prompt,
                    show_table=show_table,
                    show_metrics=show_metrics,
                ),
            )

            self.processing = False
            self.processing_message = ""
            self._mark_updated()
            self._render_current_module()
        finally:
            self.processing = False
            self.processing_message = ""
            command_input.disabled = False
            command_input.focus()
            self._refresh_chrome()

    def _start_story_from_prompt(self, module_key: str, prompt: str) -> None:
        self.module_picker_active = False
        self.home_navigation_active = False
        self.investigation_navigation_active = False
        self.investigation_case_key = None
        self.investigation_action_index = 0

        context = self._default_story_context()
        self._set_story_context(module_key, context)
        self._open_story_scene(
            module_key,
            "story_ambiguity",
            "Investigation request received. Scope is still missing, so Pathfinder is holding the task at the context check step.",
            source_prompt=prompt,
        )

    def _handle_story_followup_prompt(self, module_key: str, prompt: str) -> bool:
        if not self._story_context_active():
            return False

        prompt_lower = " ".join(prompt.strip().lower().split())
        context = self.story_context
        if context is None:
            return False

        if "production" in prompt_lower and "24" in prompt_lower and ("containment" in prompt_lower or "triage only" in prompt_lower):
            goal = "triage only" if "triage only" in prompt_lower else "triage + containment recommendation"
            self._apply_story_scope(
                module_key,
                environment="production",
                time_range="last 24 hours",
                goal=goal,
                source_prompt=prompt,
            )
            return True

        if "run investigation" in prompt_lower and context.environment is not None:
            self._open_story_findings(module_key, source_prompt=prompt)
            return True

        if "memory state" in prompt_lower:
            self._open_story_scene(
                module_key,
                "story_memory_state",
                "Session-scoped investigation memory loaded for the active service-account case.",
                source_prompt=prompt,
            )
            return True

        if "likely related" in prompt_lower or "privileged session" in prompt_lower and "related" in prompt_lower:
            self._open_story_scene(
                module_key,
                "story_session_relatedness",
                "Pathfinder assessed whether pra-2214 is likely tied to the same service-account activity.",
                source_prompt=prompt,
            )
            return True

        if "affected assets" in prompt_lower and "severity" in prompt_lower:
            self._open_story_scene(
                module_key,
                "story_assets",
                "Using the active investigation context, Pathfinder grouped the affected assets by severity.",
                source_prompt=prompt,
            )
            return True

        if "approval evidence" in prompt_lower or "approval proof" in prompt_lower:
            self._open_story_scene(
                module_key,
                "story_approval_evidence",
                "Pathfinder compared the current approval artifacts against the live session and privileged path.",
                source_prompt=prompt,
            )
            return True

        if "privilege path" in prompt_lower or ("path" in prompt_lower and "admin" in prompt_lower):
            self._open_story_scene(
                module_key,
                "story_privilege_path",
                "Pathfinder opened the focused privilege path tied to the active investigation.",
                source_prompt=prompt,
            )
            return True

        if "incident review" in prompt_lower:
            self._open_story_scene(
                module_key,
                "story_incident_review",
                "Incident review draft opened for the active investigation.",
                source_prompt=prompt,
            )
            return True

        if "safest immediate containment move" in prompt_lower or "containment move" in prompt_lower:
            self._open_story_scene(
                module_key,
                "story_containment",
                "Pathfinder compared the safest immediate BeyondTrust-native containment moves.",
                source_prompt=prompt,
            )
            return True

        return False

    def _apply_story_scope(
        self,
        module_key: str,
        *,
        environment: str,
        time_range: str,
        goal: str,
        source_prompt: str,
    ) -> None:
        context = self.story_context or self._default_story_context()
        context.environment = environment
        context.time_range = time_range
        context.goal = goal
        context.memory_active = True
        context.current_scene = "story_scope_confirm"
        context.selected_scope_label = f"{environment} | {time_range} | {goal}"
        self._set_story_context(module_key, context)
        self._open_story_scene(
            module_key,
            "story_scope_confirm",
            f"Scope confirmed for {context.entity}: {environment}, {time_range}, {goal}.",
            source_prompt=source_prompt,
        )

    def _open_story_findings(self, module_key: str, *, source_prompt: str) -> None:
        context = self.story_context or self._default_story_context()
        context.current_scene = "story_findings"
        self._set_story_context(module_key, context)
        self._open_story_scene(
            module_key,
            "story_findings",
            "Initial findings loaded. Pathfinder correlated identity, session, and approval signals for svc-backup-ops.",
            source_prompt=source_prompt,
        )

    def _open_story_scene(
        self,
        module_key: str,
        scene_key: str,
        text: str,
        *,
        source_prompt: str = "",
        return_view_key: str | None = None,
    ) -> None:
        context = self.story_context or self._default_story_context()
        context.current_scene = scene_key
        self._set_story_context(module_key, context)
        self.detail_navigation_active = True
        self.detail_view_key = scene_key
        self.detail_action_index = 0
        self.detail_return_view_key = return_view_key
        self._remember_detail_state(module_key)
        self._append_history(
            module_key,
            ConversationEntry(
                role="assistant",
                text=text,
                source_prompt=source_prompt,
                kind="story_scene",
                context_key=STORY_CONTEXT_KEY,
                action_key=scene_key,
            ),
        )

    def _append_story_message(self, module_key: str, text: str, *, source_prompt: str = "", action_key: str = "") -> None:
        self._append_history(
            module_key,
            ConversationEntry(
                role="assistant",
                text=text,
                source_prompt=source_prompt,
                action_key=action_key,
            ),
        )

    def _stage_story_requests(
        self,
        module_key: str,
        *,
        include_session: bool,
        include_path: bool,
        open_scene: str,
        source_prompt: str,
    ) -> None:
        context = self.story_context or self._default_story_context()
        ticket = self._ensure_story_incident_ticket(context)
        prepared_keys = self._prepared_story_approval_keys(include_session=include_session, include_path=include_path)

        if include_session:
            self._stage_story_pending_approval(
                PendingApproval(
                    key="story-pra-2214-terminate",
                    source="PRA",
                    request=f"terminate {context.active_session}",
                    requester="svc-backup-ops response",
                    resource=context.active_session,
                    waiting="new",
                    ticket=ticket,
                    duration="immediate",
                    scope="terminate the live privileged session",
                    approver="privileged-access-reviewer",
                    business_case=f"correlated privileged activity tied to {context.entity}",
                    note="prepared by Pathfinder; reviewer approval required before execution",
                    tone="risk",
                )
            )
        if include_path:
            self._stage_story_pending_approval(
                PendingApproval(
                    key="story-aws-prod-admin-suspend",
                    source="Entitle",
                    request="suspend aws-prod-admin access",
                    requester="svc-backup-ops response",
                    resource="aws-prod-admin",
                    waiting="new",
                    ticket=ticket,
                    duration="until reviewed",
                    scope=context.reachable_path,
                    approver="cloud-identity-reviewer",
                    business_case=f"break the reachable production admin path tied to {context.entity}",
                    note="prepared by Pathfinder; reviewer approval required before execution",
                    tone="risk",
                )
            )

        context.prepared_approval_keys = prepared_keys
        context.incident_review_staged = True
        self._set_story_context(module_key, context)
        self._open_story_scene(module_key, open_scene, source_prompt, source_prompt=source_prompt)

    def _handle_story_detail_action(self, module_key: str, action: InvestigationAction) -> bool:
        current_scene = self.detail_view_key or "story_ambiguity"
        context = self.story_context or self._default_story_context()

        if self._story_mode_active():
            if action.key == "story_mode_return":
                if self.detail_view_key == "story_menu":
                    self._close_story_mode(module_key)
                else:
                    self.detail_navigation_active = True
                    self.detail_view_key = "story_menu"
                    self.detail_action_index = 0
                    self.detail_return_view_key = None
                    self._remember_detail_state(module_key)
                return True
            if action.key.startswith("story_mode_"):
                self.detail_navigation_active = True
                self.detail_view_key = action.key
                self.detail_action_index = 0
                self.detail_return_view_key = "story_menu"
                self._remember_detail_state(module_key)
                return True
            return False

        if action.key == "story_scope_default_recommend":
            self._apply_story_scope(
                module_key,
                environment="production",
                time_range="last 24 hours",
                goal="triage + containment recommendation",
                source_prompt=action.label,
            )
            return True

        if action.key == "story_scope_default_triage":
            self._apply_story_scope(
                module_key,
                environment="production",
                time_range="last 24 hours",
                goal="triage only",
                source_prompt=action.label,
            )
            return True

        if action.key == "story_customize_scope":
            self._open_story_scene(module_key, "story_scope_custom", action.result, source_prompt=action.label, return_view_key=current_scene)
            return True

        if action.key == "story_show_role_limits":
            self._open_story_scene(module_key, "story_role_limits", action.result, source_prompt=action.label, return_view_key=current_scene)
            return True

        if action.key == "story_return_home":
            self._clear_detail_state(module_key)
            self._clear_story_context(module_key)
            self._append_story_message(module_key, action.result, source_prompt=action.label)
            return True

        if action.key == "story_run_investigation":
            self._open_story_findings(module_key, source_prompt=action.label)
            return True

        if action.key == "story_adjust_scope":
            self._open_story_scene(module_key, "story_scope_custom", "Scope adjustment opened.", source_prompt=action.label, return_view_key="story_scope_confirm")
            return True

        if action.key == "story_show_memory_state":
            self._open_story_scene(module_key, "story_memory_state", action.result, source_prompt=action.label, return_view_key=current_scene)
            return True

        if action.key == "story_return_to_ambiguity":
            self._open_story_scene(module_key, "story_ambiguity", self._story_scene_result_text("story_ambiguity", returned=True), source_prompt=action.label)
            return True

        if action.key == "story_return_to_scope":
            target_scene = self.detail_return_view_key or "story_scope_confirm"
            self._open_story_scene(module_key, target_scene, self._story_scene_result_text(target_scene, returned=True), source_prompt=action.label)
            return True

        if action.key == "story_assess_session_relatedness":
            self._open_story_scene(module_key, "story_session_relatedness", action.result, source_prompt=action.label)
            return True

        if action.key == "story_show_privilege_path":
            self._open_story_scene(module_key, "story_privilege_path", action.result, source_prompt=action.label)
            return True

        if action.key == "story_show_approval_evidence":
            self._open_story_scene(module_key, "story_approval_evidence", action.result, source_prompt=action.label)
            return True

        if action.key == "story_list_affected_assets":
            self._open_story_scene(module_key, "story_assets", action.result, source_prompt=action.label)
            return True

        if action.key == "story_open_incident_review":
            self._ensure_story_incident_ticket(context)
            context.incident_review_staged = True
            self._set_story_context(module_key, context)
            self._open_story_scene(module_key, "story_incident_review", action.result, source_prompt=action.label)
            return True

        if action.key == "story_return_to_findings":
            self._open_story_scene(module_key, "story_findings", self._story_scene_result_text("story_findings", returned=True), source_prompt=action.label)
            return True

        if action.key == "story_compare_access_change_options":
            self._open_story_scene(module_key, "story_containment", action.result, source_prompt=action.label)
            return True

        if action.key == "story_request_approval_proof":
            context.approval_proof_requested = True
            self._set_story_context(module_key, context)
            self._open_story_scene(module_key, "story_approval_evidence", action.result, source_prompt=action.label)
            return True

        if action.key == "story_show_top_asset_detail":
            self._open_story_scene(module_key, "story_asset_detail", action.result, source_prompt=action.label, return_view_key="story_assets")
            return True

        if action.key == "story_return_to_assets":
            self._open_story_scene(module_key, "story_assets", self._story_scene_result_text("story_assets", returned=True), source_prompt=action.label)
            return True

        if action.key == "story_prepare_session_revoke_request":
            self._stage_story_requests(
                module_key,
                include_session=True,
                include_path=False,
                open_scene="story_handoff",
                source_prompt=action.result,
            )
            return True

        if action.key == "story_prepare_path_suspension_request":
            self._stage_story_requests(
                module_key,
                include_session=False,
                include_path=True,
                open_scene="story_handoff",
                source_prompt=action.result,
            )
            return True

        if action.key == "story_prepare_combined_response_packet":
            self._stage_story_requests(
                module_key,
                include_session=True,
                include_path=True,
                open_scene="story_handoff",
                source_prompt=action.result,
            )
            return True

        if action.key == "story_stage_incident_review":
            self._ensure_story_incident_ticket(context)
            context.incident_review_staged = True
            self._set_story_context(module_key, context)
            self._open_story_scene(module_key, "story_incident_review", action.result, source_prompt=action.label)
            return True

        if action.key == "story_open_approval_queue":
            self._open_story_scene(module_key, "story_approval_queue", action.result, source_prompt=action.label)
            return True

        if action.key == "story_export_summary":
            self._ensure_story_incident_ticket(context)
            context.export_ready = True
            self._set_story_context(module_key, context)
            self._open_story_scene(module_key, "story_export", action.result, source_prompt=action.label)
            return True

        if action.key == "story_return_home_keep_memory":
            self._clear_detail_state(module_key)
            self._append_story_message(module_key, action.result, source_prompt=action.label)
            return True

        if action.key == "story_review_prepared_request":
            approval_key = self._story_primary_prepared_key()
            if approval_key is None:
                self._open_story_scene(module_key, "story_approval_queue", "No staged approval request is currently available for review.", source_prompt=action.label)
                return True
            self.detail_navigation_active = True
            self.detail_view_key = f"approval_detail:{approval_key}"
            self.detail_action_index = 0
            self.detail_return_view_key = "story_approval_queue"
            self._remember_detail_state(module_key)
            approval = self._pending_approval_for_key(approval_key)
            if approval is not None:
                self._append_history(
                    module_key,
                    ConversationEntry(
                        role="assistant",
                        text=action.result,
                        kind="home_action",
                        context_key="",
                        action_key=f"approval_detail:{approval.key}",
                    ),
                )
            return True

        if action.key == "story_hold_prepared_request":
            approval_key = self._story_primary_prepared_key()
            if approval_key is not None:
                self.pending_approval_state_by_key[approval_key] = "on_hold"
            self._open_story_scene(module_key, "story_approval_queue", action.result, source_prompt=action.label)
            return True

        return False

    def action_picker_up(self) -> None:
        if self.processing:
            return

        if self.module_picker_active:
            picker_modules = self._picker_modules()
            if picker_modules:
                self.module_picker_index = (self.module_picker_index - 1) % len(picker_modules)
            self._mark_updated()
            self._render_current_module()
            return

        detail_actions = self._active_detail_actions()
        if self.detail_navigation_active and detail_actions:
            self.detail_action_index = (self.detail_action_index - 1) % len(detail_actions)
            self._remember_detail_state(self._active_module().key)
            self._mark_updated()
            self._render_current_module()
            return

        active_case = self._active_investigation_case()
        if self.investigation_navigation_active and active_case is not None and active_case.next_actions:
            self.investigation_action_index = (self.investigation_action_index - 1) % len(active_case.next_actions)
            self.investigation_navigation_active = True
            self._remember_investigation_state(self._active_module().key)
            self._mark_updated()
            self._render_current_module()
            return

        if not self.home_navigation_active:
            self.home_navigation_active = True
            self.home_selection_index = self._home_selection_count() - 1
        else:
            self.home_selection_index = max(0, self.home_selection_index - 1)
        self._mark_updated()
        self._render_current_module()

    def action_picker_down(self) -> None:
        if self.processing:
            return

        if self.module_picker_active:
            picker_modules = self._picker_modules()
            if picker_modules:
                self.module_picker_index = (self.module_picker_index + 1) % len(picker_modules)
            self._mark_updated()
            self._render_current_module()
            return

        detail_actions = self._active_detail_actions()
        if self.detail_navigation_active and detail_actions:
            self.detail_action_index = (self.detail_action_index + 1) % len(detail_actions)
            self._remember_detail_state(self._active_module().key)
            self._mark_updated()
            self._render_current_module()
            return

        active_case = self._active_investigation_case()
        if self.investigation_navigation_active and active_case is not None and active_case.next_actions:
            self.investigation_action_index = (self.investigation_action_index + 1) % len(active_case.next_actions)
            self.investigation_navigation_active = True
            self._remember_investigation_state(self._active_module().key)
            self._mark_updated()
            self._render_current_module()
            return

        if not self.home_navigation_active:
            return

        if self.home_selection_index >= self._home_selection_count() - 1:
            self.home_navigation_active = False
            self.query_one("#command-input", Input).focus()
        else:
            self.home_selection_index += 1
        self._mark_updated()
        self._render_current_module()

    def _handle_utility_command(self, prompt: str) -> None:
        command = prompt.strip()
        command_lower = command.lower()
        module = self._active_module()

        if command_lower == "/help":
            self._append_history(
                module.key,
                ConversationEntry(
                    role="assistant",
                    text="Command reference",
                    kind="help",
                ),
            )
            return

        if command_lower == "/clear":
            for key in self.histories:
                self.histories[key].clear()
                self.investigation_state_by_module[key] = None
                self.detail_state_by_module[key] = None
                self.verification_profile_by_module[key] = None
                self.story_context_by_module[key] = None
                self.story_mode_return_state_by_module[key] = None
            self.home_navigation_active = False
            self.module_picker_active = False
            self._clear_investigation_state(module.key)
            self._append_history(
                module.key,
                ConversationEntry(role="assistant", text="Cleared conversation history across all apps."),
            )
            return

        if command_lower == "/reset":
            self.histories[module.key].clear()
            self.home_navigation_active = False
            self.module_picker_active = False
            self._clear_investigation_state(module.key)
            self._append_history(
                module.key,
                ConversationEntry(role="assistant", text=f"Cleared conversation history for {module.label}."),
            )
            return

        if command_lower == "/story":
            self._open_story_mode(module.key)
            return

        if command_lower.startswith("/module") or command_lower.startswith("/app"):
            self._handle_module_command(command)
            return

        if command_lower.startswith("/agent"):
            self._handle_agent_command(command)
            return

        self._append_history(
            module.key,
            ConversationEntry(role="assistant", text="Unknown command. Type /help for available commands."),
        )

    def _handle_module_command(self, command: str) -> None:
        parts = command.split(maxsplit=1)
        current_module = self._active_module()

        if len(parts) == 1 or parts[1].strip().lower() == "list":
            self.module_picker_active = True
            self.home_navigation_active = False
            self.module_picker_index = self._picker_index_for_active_module()
            return

        target = parts[1].strip()
        next_index = self._resolve_module_index(target)
        if next_index is None:
            self._append_history(
                current_module.key,
                ConversationEntry(
                    role="assistant",
                    text=f'App "{target}" was not found. Use /app to list options.',
                ),
            )
            return

        self._set_active_module_index(next_index)
        new_module = self._active_module()
        self._append_history(
            new_module.key,
            ConversationEntry(role="assistant", text=f"Switched to {new_module.label}."),
        )

    def _handle_agent_command(self, command: str) -> None:
        parts = command.split(maxsplit=2)
        current_module = self._active_module()
        self.investigation_navigation_active = False

        if len(parts) == 1 or parts[1].lower() in {"list", "status"}:
            self._append_history(
                current_module.key,
                ConversationEntry(
                    role="assistant",
                    text="Agent roster loaded. Add or remove agents as needed from this prototype view.",
                    source_prompt="agent status",
                    show_table=True,
                ),
            )
            return

        action = parts[1].lower()
        if action not in {"add", "remove"}:
            self._append_history(
                current_module.key,
                ConversationEntry(
                    role="assistant",
                    text='Unknown /agent command. Use "/agent", "/agent add <name>", or "/agent remove <name>".',
                ),
            )
            return

        if len(parts) < 3 or not parts[2].strip():
            self._append_history(
                current_module.key,
                ConversationEntry(
                    role="assistant",
                    text=f'Usage: /agent {action} <name>',
                ),
            )
            return

        agent_name = parts[2].strip()
        if action == "add":
            self._add_agent(current_module.key, agent_name)
            return

        self._remove_agent(current_module.key, agent_name)

    def _resolve_module_index(self, target: str) -> int | None:
        picker_modules = self._picker_modules()
        if target.isdigit():
            index = int(target) - 1
            if 0 <= index < len(picker_modules):
                target_key = picker_modules[index].key
                for module_index, module in enumerate(MODULES):
                    if module.key == target_key:
                        return module_index
            return None

        normalized_target = self._normalize_module_name(target)
        for index, module in enumerate(MODULES):
            if module.key == "pathfinder":
                continue
            normalized_label = self._normalize_module_name(module.label)
            normalized_key = self._normalize_module_name(module.key)
            if normalized_target in {normalized_label, normalized_key}:
                return index
        return None

    def _normalize_module_name(self, value: str) -> str:
        return " ".join(value.replace("_", " ").replace("-", " ").lower().split())

    def _normalize_agent_name(self, value: str) -> str:
        return " ".join(value.replace("_", " ").replace("-", " ").lower().split())

    def _matches_actionable_items_request(self, prompt: str) -> bool:
        tokens = set(re.findall(r"[a-z0-9]+", prompt.lower()))
        return "actionable" in tokens and bool(tokens & {"item", "items"})

    def _investigation_case_for_attention(self, attention: AttentionItem) -> InvestigationCase | None:
        return INVESTIGATION_CASES.get(attention.subject)

    def _has_navigation_context(self) -> bool:
        return any(
            (
                self.module_picker_active,
                self.detail_navigation_active,
                self.investigation_navigation_active,
                self.home_navigation_active,
            )
        )

    def _active_investigation_case(self) -> InvestigationCase | None:
        if not self.investigation_case_key:
            return None
        return INVESTIGATION_CASES.get(self.investigation_case_key)

    def _selected_investigation_action(self) -> InvestigationAction | None:
        active_case = self._active_investigation_case()
        if active_case is None:
            return None
        return active_case.next_actions[self.investigation_action_index]

    def _active_detail_actions(self) -> tuple[InvestigationAction, ...]:
        if self.detail_view_key == "story_ambiguity":
            return STORY_AMBIGUITY_ACTIONS
        if self.detail_view_key == "story_scope_confirm":
            return STORY_SCOPE_CONFIRM_ACTIONS
        if self.detail_view_key == "story_scope_custom":
            return STORY_SCOPE_CUSTOM_ACTIONS
        if self.detail_view_key == "story_role_limits":
            return STORY_ROLE_LIMITS_ACTIONS
        if self.detail_view_key == "story_memory_state":
            return STORY_MEMORY_ACTIONS
        if self.detail_view_key == "story_findings":
            return STORY_FINDINGS_ACTIONS
        if self.detail_view_key == "story_session_relatedness":
            return STORY_SESSION_RELATEDNESS_ACTIONS
        if self.detail_view_key == "story_approval_evidence":
            return STORY_APPROVAL_EVIDENCE_ACTIONS
        if self.detail_view_key == "story_privilege_path":
            return STORY_PRIVILEGE_PATH_ACTIONS
        if self.detail_view_key == "story_assets":
            return STORY_ASSETS_ACTIONS
        if self.detail_view_key == "story_asset_detail":
            return STORY_ASSET_DETAIL_ACTIONS
        if self.detail_view_key == "story_containment":
            return STORY_CONTAINMENT_ACTIONS
        if self.detail_view_key == "story_incident_review":
            return STORY_INCIDENT_REVIEW_ACTIONS
        if self.detail_view_key == "story_handoff":
            return STORY_HANDOFF_ACTIONS
        if self.detail_view_key == "story_approval_queue":
            return STORY_APPROVAL_QUEUE_ACTIONS
        if self.detail_view_key == "story_export":
            return STORY_EXPORT_ACTIONS
        if self.detail_view_key == "story_menu":
            return STORY_MENU_ACTIONS
        if self.detail_view_key and self.detail_view_key.startswith("story_mode_"):
            return STORY_MENU_RETURN_ACTIONS
        if self.detail_view_key == "live_session":
            return LIVE_SESSION_FOLLOWUP_ACTIONS
        if self.detail_view_key == "target_activity":
            return TARGET_ACTIVITY_FOLLOWUP_ACTIONS
        if self.detail_view_key == "privilege_path":
            return PRIVILEGE_PATH_FOLLOWUP_ACTIONS
        if self.detail_view_key == "containment":
            return CONTAINMENT_FOLLOWUP_ACTIONS
        if self.detail_view_key == "verification":
            return VERIFICATION_FOLLOWUP_ACTIONS
        if self.detail_view_key == "true_privilege_graph":
            return self._true_privilege_graph_actions()
        if self.detail_view_key and self.detail_view_key.startswith("graph_focus:"):
            return GRAPH_FOCUS_ACTIONS
        if self.detail_view_key == "pending_approvals":
            return self._pending_approval_queue_actions()
        if self.detail_view_key and self.detail_view_key.startswith("approval_detail:"):
            return PENDING_APPROVAL_DETAIL_ACTIONS
        return ()

    def _active_story_detail_actions(self, detail_view_key: str | None = None) -> tuple[InvestigationAction, ...]:
        scene_key = detail_view_key or self.detail_view_key
        if scene_key == "story_ambiguity":
            return STORY_AMBIGUITY_ACTIONS
        if scene_key == "story_scope_confirm":
            return STORY_SCOPE_CONFIRM_ACTIONS
        if scene_key == "story_scope_custom":
            return STORY_SCOPE_CUSTOM_ACTIONS
        if scene_key == "story_role_limits":
            return STORY_ROLE_LIMITS_ACTIONS
        if scene_key == "story_memory_state":
            return STORY_MEMORY_ACTIONS
        if scene_key == "story_findings":
            return STORY_FINDINGS_ACTIONS
        if scene_key == "story_session_relatedness":
            return STORY_SESSION_RELATEDNESS_ACTIONS
        if scene_key == "story_approval_evidence":
            return STORY_APPROVAL_EVIDENCE_ACTIONS
        if scene_key == "story_privilege_path":
            return STORY_PRIVILEGE_PATH_ACTIONS
        if scene_key == "story_assets":
            return STORY_ASSETS_ACTIONS
        if scene_key == "story_asset_detail":
            return STORY_ASSET_DETAIL_ACTIONS
        if scene_key == "story_containment":
            return STORY_CONTAINMENT_ACTIONS
        if scene_key == "story_incident_review":
            return STORY_INCIDENT_REVIEW_ACTIONS
        if scene_key == "story_handoff":
            return STORY_HANDOFF_ACTIONS
        if scene_key == "story_approval_queue":
            return STORY_APPROVAL_QUEUE_ACTIONS
        if scene_key == "story_export":
            return STORY_EXPORT_ACTIONS
        if scene_key == "story_menu":
            return STORY_MENU_ACTIONS
        if scene_key and scene_key.startswith("story_mode_"):
            return STORY_MENU_RETURN_ACTIONS
        return ()

    def _set_verification_profile(self, module_key: str, profile_key: str | None) -> None:
        self.verification_profile_by_module[module_key] = profile_key
        if self._active_module().key == module_key:
            self.verification_profile_key = profile_key

    def _verification_profile_for_action(self, action_key: str) -> str | None:
        if action_key in {"revoke_session", "revoke_session_now"}:
            return "revoke_session"
        if action_key in {"remove_inherited_admin_link", "remove_admin_link"}:
            return "remove_admin_link"
        if action_key == "do_both_actions":
            return "do_both_actions"
        return None

    def _detail_action_label(self, action: InvestigationAction) -> str:
        if self.detail_view_key == "containment" and action.key == "cancel_return":
            return {
                "privilege_path": "return to privilege path",
                "target_activity": "return to activity review",
                "live_session": "return to session summary",
                "summary": "return to case summary",
            }.get(self.detail_return_view_key, "return")
        return action.label

    def _detail_action_summary(self, action: InvestigationAction) -> str:
        if self.detail_view_key == "containment" and action.key == "cancel_return":
            return {
                "privilege_path": "leave containment planning and go back to the privilege path review",
                "target_activity": "leave containment planning and go back to the target activity review",
                "live_session": "leave containment planning and go back to the session summary",
                "summary": "leave containment planning and go back to the case summary",
            }.get(self.detail_return_view_key, action.summary)
        return action.summary

    def _selected_detail_action(self) -> InvestigationAction | None:
        detail_actions = self._active_detail_actions()
        if not self.detail_navigation_active or not detail_actions:
            return None
        bounded_index = max(0, min(self.detail_action_index, len(detail_actions) - 1))
        return detail_actions[bounded_index]

    def _add_agent(self, module_key: str, agent_name: str) -> None:
        normalized_name = self._normalize_agent_name(agent_name)
        for row in self.agent_status_rows:
            if self._normalize_agent_name(row.agent) == normalized_name:
                self._append_history(
                    module_key,
                    ConversationEntry(
                        role="assistant",
                        text=f'Agent "{row.agent}" already exists in the current roster.',
                        source_prompt="agent status",
                        show_table=True,
                    ),
                )
                return

        created_agent = AgentStatusRow(
            agent=agent_name,
            connector="disconnected",
            connector_level="risk",
            access="scope pending",
            role="observe",
        )
        self.agent_status_rows.append(created_agent)
        self._append_history(
            module_key,
            ConversationEntry(
                role="assistant",
                text=f'Added agent "{agent_name}" with a disconnected connector. Update access scope when you are ready.',
                source_prompt="agent status",
                show_table=True,
            ),
        )

    def _remove_agent(self, module_key: str, agent_name: str) -> None:
        normalized_name = self._normalize_agent_name(agent_name)
        for index, row in enumerate(self.agent_status_rows):
            if self._normalize_agent_name(row.agent) == normalized_name:
                removed = self.agent_status_rows.pop(index)
                self._append_history(
                    module_key,
                    ConversationEntry(
                        role="assistant",
                        text=f'Removed agent "{removed.agent}" from the current roster.',
                        source_prompt="agent status",
                        show_table=True,
                    ),
                )
                return

        self._append_history(
            module_key,
            ConversationEntry(
                role="assistant",
                text=f'Agent "{agent_name}" was not found in the current roster.',
                source_prompt="agent status",
                show_table=True,
            ),
        )

    def _append_history(self, module_key: str, entry: ConversationEntry) -> None:
        self.histories[module_key].append(entry)

    def _clear_investigation_state(self, module_key: str) -> None:
        self.investigation_state_by_module[module_key] = None
        self.detail_state_by_module[module_key] = None
        self.verification_profile_by_module[module_key] = None
        self.story_context_by_module[module_key] = None
        self.story_mode_return_state_by_module[module_key] = None
        if self._active_module().key != module_key:
            return
        self.detail_navigation_active = False
        self.detail_view_key = None
        self.detail_action_index = 0
        self.detail_return_view_key = None
        self.verification_profile_key = None
        self.investigation_navigation_active = False
        self.investigation_case_key = None
        self.investigation_action_index = 0
        self.story_context = None

    def _remember_investigation_state(self, module_key: str) -> None:
        if not self.investigation_navigation_active or not self.investigation_case_key:
            self.investigation_state_by_module[module_key] = None
            return
        self.investigation_state_by_module[module_key] = (
            self.investigation_case_key,
            self.investigation_action_index,
        )

    def _restore_investigation_state(self, module_key: str) -> None:
        saved_state = self.investigation_state_by_module.get(module_key)
        if saved_state is None:
            self.investigation_navigation_active = False
            self.investigation_case_key = None
            self.investigation_action_index = 0
            return

        case_key, action_index = saved_state
        investigation_case = INVESTIGATION_CASES.get(case_key)
        if investigation_case is None or not investigation_case.next_actions:
            self.investigation_state_by_module[module_key] = None
            self.investigation_navigation_active = False
            self.investigation_case_key = None
            self.investigation_action_index = 0
            return

        bounded_index = max(0, min(action_index, len(investigation_case.next_actions) - 1))
        self.investigation_navigation_active = True
        self.investigation_case_key = investigation_case.key
        self.investigation_action_index = bounded_index
        self.investigation_state_by_module[module_key] = (investigation_case.key, bounded_index)

    def _clear_detail_state(self, module_key: str) -> None:
        self.detail_state_by_module[module_key] = None
        self.verification_profile_by_module[module_key] = None
        if self._active_module().key != module_key:
            return
        self.detail_navigation_active = False
        self.detail_view_key = None
        self.detail_action_index = 0
        self.detail_return_view_key = None
        self.verification_profile_key = None

    def _remember_detail_state(self, module_key: str) -> None:
        if not self.detail_navigation_active or not self.detail_view_key:
            self.detail_state_by_module[module_key] = None
            return
        self.detail_state_by_module[module_key] = (
            self.detail_view_key,
            self.detail_action_index,
            self.detail_return_view_key,
        )

    def _restore_detail_state(self, module_key: str) -> None:
        saved_state = self.detail_state_by_module.get(module_key)
        if saved_state is None:
            self.detail_navigation_active = False
            self.detail_view_key = None
            self.detail_action_index = 0
            self.verification_profile_key = None
            return

        detail_view_key, action_index, return_view_key = saved_state
        if detail_view_key in {
            "story_ambiguity",
            "story_scope_confirm",
            "story_scope_custom",
            "story_role_limits",
            "story_memory_state",
            "story_findings",
            "story_session_relatedness",
            "story_approval_evidence",
            "story_privilege_path",
            "story_assets",
            "story_asset_detail",
            "story_containment",
            "story_incident_review",
            "story_handoff",
            "story_approval_queue",
            "story_export",
            "story_menu",
        } or detail_view_key.startswith("story_mode_"):
            detail_actions = self._active_story_detail_actions(detail_view_key)
        elif detail_view_key == "live_session":
            detail_actions = LIVE_SESSION_FOLLOWUP_ACTIONS
        elif detail_view_key == "target_activity":
            detail_actions = TARGET_ACTIVITY_FOLLOWUP_ACTIONS
        elif detail_view_key == "privilege_path":
            detail_actions = PRIVILEGE_PATH_FOLLOWUP_ACTIONS
        elif detail_view_key == "containment":
            detail_actions = CONTAINMENT_FOLLOWUP_ACTIONS
        elif detail_view_key == "verification":
            detail_actions = VERIFICATION_FOLLOWUP_ACTIONS
        elif detail_view_key == "true_privilege_graph":
            detail_actions = self._true_privilege_graph_actions()
        elif detail_view_key.startswith("graph_focus:"):
            detail_actions = GRAPH_FOCUS_ACTIONS
        elif detail_view_key == "pending_approvals":
            detail_actions = self._pending_approval_queue_actions()
        elif detail_view_key.startswith("approval_detail:"):
            detail_actions = PENDING_APPROVAL_DETAIL_ACTIONS
        else:
            detail_actions = ()

        if not detail_actions:
            self.detail_state_by_module[module_key] = None
            self.detail_navigation_active = False
            self.detail_view_key = None
            self.detail_action_index = 0
            self.verification_profile_key = None
            return

        bounded_index = max(0, min(action_index, len(detail_actions) - 1))
        self.detail_navigation_active = True
        self.detail_view_key = detail_view_key
        self.detail_action_index = bounded_index
        self.detail_return_view_key = return_view_key
        self.verification_profile_key = self.verification_profile_by_module.get(module_key)
        self.detail_state_by_module[module_key] = (detail_view_key, bounded_index, return_view_key)

    def _picker_modules(self) -> tuple[ModuleSpec, ...]:
        return tuple(module for module in MODULES if module.key != "pathfinder")

    def _picker_index_for_active_module(self) -> int:
        picker_modules = self._picker_modules()
        active_key = self._active_module().key
        for index, module in enumerate(picker_modules):
            if module.key == active_key:
                return index
        return 0

    def _picker_module_at_current_index(self) -> ModuleSpec:
        picker_modules = self._picker_modules()
        if not picker_modules:
            return self._active_module()
        bounded_index = max(0, min(self.module_picker_index, len(picker_modules) - 1))
        return picker_modules[bounded_index]

    def _active_module(self) -> ModuleSpec:
        return MODULES[self.module_index]

    def _set_active_module_index(self, module_index: int) -> None:
        self.module_index = module_index
        self.module_picker_index = self._picker_index_for_active_module()
        self.module_picker_active = False
        self.home_navigation_active = False
        self._restore_story_context(self._active_module().key)
        self._restore_investigation_state(self._active_module().key)
        self._restore_detail_state(self._active_module().key)

    def _build_scene_renderables(self, scene_key: str | None) -> list[object] | None:
        if scene_key == "portfolio_cover":
            return self._build_portfolio_cover_renderables()
        if scene_key == "temp_sunset_scene":
            return self._build_temp_sunset_scene_renderables()
        if scene_key == "story_menu":
            return self._build_story_menu_renderables()
        if scene_key and scene_key.startswith("story_mode_"):
            return self._build_story_mode_renderables(scene_key)
        return None

    def _scene_chrome_label(self, scene_key: str | None = None) -> str | None:
        if scene_key is None:
            scene_key = self.detail_view_key
        if scene_key == "portfolio_cover":
            return "Cover"
        if scene_key == "temp_sunset_scene":
            return "Loading"
        if scene_key == "story_menu" or (scene_key and scene_key.startswith("story_mode_")):
            return "Story"
        return None

    def _scene_footer_hint(self, scene_key: str | None = None) -> Text | None:
        if scene_key is None:
            scene_key = self.detail_view_key
        if scene_key == "portfolio_cover":
            text = Text()
            text.append("Portfolio cover", style=f"bold {PALETTE['orange_primary']}")
            text.append(" | ", style=PALETTE["line"])
            text.append("screenshot-ready scene", style=PALETTE["text_main"])
            text.append(" | ", style=PALETTE["line"])
            text.append("type /reset to return", style=PALETTE["text_muted"])
            return text
        if scene_key == "temp_sunset_scene":
            text = Text()
            text.append("Temp loading scene", style=f"bold {PALETTE['orange_primary']}")
            text.append(" | ", style=PALETTE["line"])
            text.append("loading-screen style PATHFINDER CLI splash", style=PALETTE["text_main"])
            text.append(" | ", style=PALETTE["line"])
            text.append("type /reset to return", style=PALETTE["text_muted"])
            return text
        if scene_key == "story_menu" or (scene_key and scene_key.startswith("story_mode_")):
            text = Text()
            text.append("hidden story mode", style=f"bold {PALETTE['orange_primary']}")
            text.append(" | ", style=PALETTE["line"])
            text.append("presentation-ready design lens", style=PALETTE["text_main"])
            text.append(" | ", style=PALETTE["line"])
            text.append("Esc or q returns", style=PALETTE["text_muted"])
            return text
        return None

    def _render_current_module(self) -> None:
        log = self.query_one("#main-log", RichLog)
        log.auto_scroll = not self._initial_main_log_render_pending
        log.clear()

        scene_renderables = self._build_scene_renderables(self.detail_view_key)
        if scene_renderables is not None:
            for renderable in scene_renderables:
                log.write(renderable)
                log.write("")
            self._initial_main_log_render_pending = False
            self._refresh_chrome()
            return

        if self.module_picker_active:
            log.write(Text("App picker", style=f"bold {PALETTE['orange_soft']}"))
            log.write(
                Text(
                    "Use Up/Down and Enter to select, or /app <name|number>.",
                    style=PALETTE["text_muted"],
                )
            )
            log.write("")
            for line in self._build_picker_lines():
                log.write(line)
            self._initial_main_log_render_pending = False
            self._refresh_chrome()
            return

        log.write(Text("Overview", style=f"bold {PALETTE['orange_soft']}"))
        log.write("")
        log.write(self._build_overview_table())
        log.write("")
        for renderable in self._build_module_dashboard_renderables(self._active_module()):
            log.write(renderable)
            log.write("")
        log.write(Text(self._separator(), style=PALETTE["line"]))
        log.write("")

        log.write(Text("Actionable items", style=f"bold {PALETTE['orange_soft']}"))
        log.write("")
        for index, item in enumerate(ATTENTION_ITEMS, start=1):
            headline, detail = self._build_attention_lines(item, selected=self._is_attention_selected(index - 1))
            log.write(headline)
            log.write(detail)
            log.write("")

        log.write(Text("Analyst options", style=f"bold {PALETTE['orange_soft']}"))
        log.write("")
        for index, action in enumerate(HOME_ACTIONS, start=1):
            log.write(self._build_home_action_line(index, action, selected=self._is_action_selected(index - 1)))

        active_history = self.histories[self._active_module().key]
        if active_history or self.processing:
            log.write("")
            log.write(Text(self._separator(), style=PALETTE["line"]))
            log.write("")
            log.write(Text("Conversation", style=f"bold {PALETTE['orange_soft']}"))
            log.write("")
            for index, entry in enumerate(active_history):
                if index > 0:
                    log.write(Text(self._conversation_separator(), style=PALETTE["line"]))
                    log.write("")
                log.write(self._build_conversation_header(entry))
                log.write("")
                for renderable in self._build_conversation_body(entry, self._active_module()):
                    log.write(renderable)
                log.write("")
            if self.processing:
                if active_history:
                    log.write(Text(self._conversation_separator(), style=PALETTE["line"]))
                    log.write("")
                log.write(self._build_processing_conversation_header())
                log.write("")
                log.write(self._build_processing_status_line())
                log.write("")

        self._initial_main_log_render_pending = False
        self._refresh_chrome()

    def _build_overview_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_header=False,
            show_lines=True,
            border_style=PALETTE["line"],
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column(style=PALETTE["text_main"], no_wrap=True, min_width=18)
        table.add_column(min_width=18)
        table.add_column(min_width=22)
        table.add_column(min_width=24)

        for row in OVERVIEW_ROWS:
            status = Text()
            status.append("Status: ", style=PALETTE["text_muted"])
            status.append(row.status, style=self._status_style(row.status_level))

            metric_a = Text()
            metric_a.append(f"{row.metric_a_label}: ", style=PALETTE["text_muted"])
            metric_a.append(str(row.metric_a_value), style=f"bold {PALETTE['text_main']}")

            metric_b = Text()
            metric_b.append(f"{row.metric_b_label}: ", style=PALETTE["text_muted"])
            metric_b.append(str(row.metric_b_value), style=f"bold {PALETTE['text_main']}")

            table.add_row(
                Text(row.label, style=PALETTE["text_main"]),
                status,
                metric_a,
                metric_b,
            )

        return table

    def _build_module_dashboard_renderables(self, module: ModuleSpec, *, compact: bool = False) -> list[object]:
        if module.key == "password_safe":
            return self._build_password_safe_dashboard_renderables(module, compact=compact)

        renderables: list[object] = []
        renderables.append(self._build_module_dashboard_header_text(module, compact=compact))
        renderables.append(self._build_module_dashboard_callout_panel(module, compact=compact))
        renderables.append(self._build_module_metric_chart_table(module))
        renderables.append(self._build_module_risk_mix_panel(module, compact=compact))
        renderables.append(self._build_module_heatmap_table(module))
        return renderables

    def _build_password_safe_dashboard_renderables(self, module: ModuleSpec, *, compact: bool = False) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_module_dashboard_header_text(module, compact=compact))
        renderables.append(self._build_password_safe_status_text())
        renderables.append(Text(""))
        renderables.append(self._build_password_safe_operating_model_panel(compact=compact))
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Product lanes"))
        renderables.append(self._build_password_safe_lanes_table())

        if compact:
            return renderables

        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Managed account hygiene"))
        renderables.append(self._build_password_safe_control_table())
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Approval & checkout pressure"))
        renderables.append(self._build_password_safe_approval_pressure_table())
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Session oversight"))
        renderables.append(self._build_password_safe_session_table())
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Secrets & non-human access"))
        renderables.append(self._build_password_safe_secrets_table())
        return renderables

    def _build_password_safe_status_text(self) -> Text:
        waiting = sum(
            1
            for approval in self._all_pending_approvals()
            if approval.source == "Password Safe" and self._pending_approval_state(approval.key) == "waiting"
        )
        break_glass = sum(
            1
            for approval in self._all_pending_approvals()
            if approval.source == "Password Safe"
            and "break-glass" in approval.request.lower()
            and self._pending_approval_state(approval.key) == "waiting"
        )
        text = Text()
        text.append(f"{waiting} approvals waiting", style=f"bold {PALETTE['violet']}")
        text.append("   ", style=PALETTE["text_main"])
        text.append(f"{break_glass} break-glass review aging", style=self._status_style("warn"))
        text.append("   ", style=PALETTE["text_main"])
        text.append("rotations overdue: ", style=PALETTE["text_muted"])
        text.append("9", style=self._status_style("risk"))
        text.append("   ", style=PALETTE["text_main"])
        text.append("secrets in safes: ", style=PALETTE["text_muted"])
        text.append("318", style=f"bold {PALETTE['teal']}")
        return text

    def _build_password_safe_operating_model_panel(self, *, compact: bool = False) -> Panel:
        text = Text()
        text.append("Discovery scans", style=f"bold {PALETTE['blue_text']}")
        text.append(" -> ", style=PALETTE["line"])
        text.append("Managed accounts", style=f"bold {PALETTE['teal_text']}")
        text.append(" -> ", style=PALETTE["line"])
        text.append("Requests / approvals", style=f"bold {PALETTE['amber_text']}")
        text.append(" -> ", style=PALETTE["line"])
        text.append("Sessions", style=f"bold {PALETTE['red_text']}")
        text.append(" -> ", style=PALETTE["line"])
        text.append("Secrets Safe / APIs", style=f"bold {PALETTE['violet_text']}")
        text.append("\n", style=PALETTE["text_main"])
        text.append(
            "Modeled on BeyondTrust Password Safe's main operating surfaces: automated onboarding, managed account control, "
            "request approval, monitored privileged sessions, and secret delivery for human and non-human access.",
            style=PALETTE["text_main"],
        )
        if not compact:
            text.append("\n", style=PALETTE["text_main"])
            text.append(
                "Design focus: give the analyst a fast read on where checkout pressure, rotation hygiene, and non-human secret use are drifting.",
                style=PALETTE["text_muted"],
            )
        return Panel(
            text,
            title="Operating model",
            box=TABLE_BOX,
            expand=True,
            border_style=PALETTE["line"],
            padding=(0, 1),
        )

    def _build_password_safe_lanes_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Lane", min_width=20)
        table.add_column("Live signal", min_width=24)
        table.add_column("Control plane", min_width=28)
        table.add_column("Why it matters", min_width=30)

        for lane in PASSWORD_SAFE_LANES:
            table.add_row(
                Text(lane.label, style=f"bold {self._tone_text_color(lane.tone)}"),
                Text(lane.signal, style=PALETTE["text_main"]),
                Text(lane.control, style=PALETTE["text_main"]),
                Text(lane.note, style=PALETTE["text_muted"]),
            )
        return table

    def _build_password_safe_control_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Control", min_width=24)
        table.add_column("Value", no_wrap=True, min_width=14)
        table.add_column("Signal", min_width=20)
        table.add_column("Trend", no_wrap=True, min_width=8)
        table.add_column("Analyst note", min_width=34)

        for row in PASSWORD_SAFE_CONTROL_ROWS:
            table.add_row(
                Text(row.label, style=f"bold {self._tone_text_color(row.tone)}"),
                Text(row.display_value, style=PALETTE["text_main"]),
                self._bar(row.bar_value, width=18),
                Text(row.trend, style=PALETTE["text_muted"]),
                Text(row.note, style=PALETTE["text_muted"]),
            )
        return table

    def _build_password_safe_approval_pressure_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Request", min_width=20)
        table.add_column("Requester", min_width=14)
        table.add_column("Resource", min_width=18)
        table.add_column("Waiting", no_wrap=True, min_width=8)
        table.add_column("State", no_wrap=True, min_width=11)
        table.add_column("Why it is stalled", min_width=28)

        for approval in self._all_pending_approvals():
            if approval.source != "Password Safe":
                continue
            table.add_row(
                Text(approval.request, style=f"bold {PALETTE['violet']}"),
                Text(approval.requester, style=PALETTE["text_main"]),
                Text(approval.resource, style=f"bold {PALETTE['teal']}"),
                Text(approval.waiting, style=PALETTE["text_main"]),
                self._pending_approval_state_badge(approval),
                Text(approval.note, style=PALETTE["text_muted"]),
            )
        return table

    def _build_password_safe_session_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Session", min_width=16)
        table.add_column("Channel", min_width=12)
        table.add_column("State", min_width=24)
        table.add_column("Recording", min_width=18)
        table.add_column("Recommended action", min_width=30)

        for row in PASSWORD_SAFE_SESSION_ROWS:
            table.add_row(
                Text(row.session_id, style=f"bold {self._tone_text_color(row.tone)}"),
                Text(row.channel, style=PALETTE["text_main"]),
                Text(row.state, style=PALETTE["text_main"]),
                Text(row.recording, style=PALETTE["text_main"]),
                Text(row.action, style=PALETTE["text_muted"]),
            )
        return table

    def _build_password_safe_secrets_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Inventory", min_width=20)
        table.add_column("Count", no_wrap=True, min_width=12)
        table.add_column("Signal", min_width=20)
        table.add_column("Delivery", min_width=18)
        table.add_column("Analyst note", min_width=28)

        for row in PASSWORD_SAFE_SECRET_ROWS:
            table.add_row(
                Text(row.label, style=f"bold {self._tone_text_color(row.tone)}"),
                Text(row.inventory, style=PALETTE["text_main"]),
                self._bar(row.bar_value, width=18),
                Text(row.delivery, style=PALETTE["text_main"]),
                Text(row.note, style=PALETTE["text_muted"]),
            )
        return table

    def _build_module_dashboard_header_text(self, module: ModuleSpec, *, compact: bool = False) -> Text:
        text = Text()
        text.append(module.title if not compact else module.label, style=f"bold {PALETTE['orange_soft']}")
        text.append("\n", style=PALETTE["text_main"])
        text.append(module.status, style=self._status_style(module.status_level))
        text.append(" | ", style=PALETTE["line"])
        text.append(
            self._module_selection_guidance(module) if compact else "visual dashboard",
            style=PALETTE["text_muted"],
        )
        return text

    def _build_plain_overview_text(self, value: str) -> Text:
        text = Text()
        text.append(value, style=PALETTE["text_muted"])
        return text

    def _module_dashboard_profile(self, module: ModuleSpec) -> DashboardProfile:
        return MODULE_DASHBOARD_PROFILES[module.key]

    def _module_selection_guidance(self, module: ModuleSpec) -> str:
        return MODULE_SELECTION_GUIDANCE[module.key]

    def _module_dashboard_callout(self, module: ModuleSpec) -> str:
        return MODULE_DASHBOARD_CALLOUTS[module.key]

    def _module_dashboard_signal_score(self, module: ModuleSpec) -> int:
        metric_average = round(sum(value for _, value, _ in module.metrics) / len(module.metrics))
        if module.status_level == "risk":
            return min(100, metric_average + 18)
        if module.status_level == "warn":
            return min(100, metric_average + 10)
        return metric_average

    def _build_module_dashboard_callout_panel(self, module: ModuleSpec, *, compact: bool = False) -> Panel:
        text = Text()
        text.append("Open this app when ", style=PALETTE["text_muted"])
        text.append(self._module_selection_guidance(module), style=f"bold {PALETTE['violet']}")
        text.append("\n", style=PALETTE["text_main"])
        if compact:
            text.append(self._module_dashboard_callout(module), style=PALETTE["text_muted"])
        else:
            text.append(module.overview, style=PALETTE["text_main"])
            text.append("\n", style=PALETTE["text_main"])
            text.append(self._module_dashboard_callout(module), style=PALETTE["text_muted"])
        return Panel(
            text,
            title="Analyst lens",
            box=TABLE_BOX,
            expand=True,
            border_style=PALETTE["line"],
            padding=(0, 1),
        )

    def _build_app_picker_decision_table(self) -> Table:
        table = Table(
            title="Which app should I open?",
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("#", no_wrap=True, min_width=3, justify="right")
        table.add_column("App", min_width=22)
        table.add_column("Select when", min_width=38)
        table.add_column("Status", min_width=18)
        table.add_column("Signal", min_width=14)

        for index, module in enumerate(self._picker_modules(), start=1):
            is_selected = index - 1 == self.module_picker_index
            label_style = f"bold {PALETTE['orange_primary']}" if is_selected else f"bold {PALETTE['text_main']}"
            table.add_row(
                Text(f"[{index}]", style=f"bold {PALETTE['orange_primary']}"),
                Text(module.label, style=label_style),
                Text(self._module_selection_guidance(module), style=PALETTE["text_main"]),
                Text(module.status, style=self._status_style(module.status_level)),
                self._bar(self._module_dashboard_signal_score(module), width=12),
                style=f"on {PALETTE['bg_soft']}" if is_selected else "",
            )
        return table

    def _build_module_metric_chart_table(self, module: ModuleSpec) -> Table:
        table = Table(
            title="Operational signals",
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Metric", min_width=24)
        table.add_column("Value", justify="right", min_width=8, style=PALETTE["text_main"])
        table.add_column("Bar", min_width=20)
        table.add_column("Trend", min_width=8, style=PALETTE["text_muted"])

        for label, value, trend in module.metrics:
            table.add_row(
                label,
                f"{value}%",
                self._bar(value, width=18),
                trend,
            )
        return table

    def _tone_text_color(self, tone: str) -> str:
        return {
            "ok": PALETTE["green_text"],
            "warn": PALETTE["amber_text"],
            "risk": PALETTE["red_text"],
            "info": PALETTE["blue_text"],
            "accent": PALETTE["purple_text"],
            "violet": PALETTE["violet_text"],
            "teal": PALETTE["teal_text"],
            "muted": PALETTE["slate_text"],
        }.get(tone, PALETTE["text_main"])

    def _build_module_risk_mix_panel(self, module: ModuleSpec, *, compact: bool = False) -> Panel:
        profile = self._module_dashboard_profile(module)
        chart = self._build_pie_chart_text(profile.slices, radius=3 if compact else 4, inner_ratio=0.42)
        legend = Text()
        for index, (label, value, tone) in enumerate(profile.slices):
            legend.append("■ ", style=self._tone_text_color(tone))
            legend.append(f"{label} {value}%", style=PALETTE["text_main"])
            if index < len(profile.slices) - 1:
                legend.append("\n", style=PALETTE["text_main"])
        body = Text()
        body.append_text(chart)
        body.append("\n\n", style=PALETTE["text_main"])
        body.append_text(legend)
        return Panel(
            body,
            title="Access mix",
            box=TABLE_BOX,
            expand=True,
            border_style=PALETTE["line"],
            padding=(0, 1),
        )

    def _build_pie_chart_text(
        self,
        slices: tuple[tuple[str, int, str], ...],
        *,
        radius: int = 4,
        inner_ratio: float = 0.0,
    ) -> Text:
        total = max(1, sum(value for _, value, _ in slices))
        cumulative: list[tuple[float, str]] = []
        running = 0.0
        for _, value, tone in slices:
            running += value / total
            cumulative.append((running, self._tone_text_color(tone)))

        text = Text()
        x_radius = radius * 2
        inner_cutoff = inner_ratio * inner_ratio
        for y in range(-radius, radius + 1):
            for x in range(-x_radius, x_radius + 1):
                nx = x / max(1, x_radius)
                ny = y / max(1, radius)
                distance = nx * nx + ny * ny
                if distance > 1.0 or distance < inner_cutoff:
                    text.append(" ")
                    continue
                angle = (math.atan2(-ny, nx) + (2 * math.pi)) % (2 * math.pi)
                ratio = angle / (2 * math.pi)
                for threshold, color in cumulative:
                    if ratio <= threshold:
                        text.append("█", style=f"bold {color}")
                        break
            if y < radius:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_module_heatmap_table(self, module: ModuleSpec) -> Table:
        profile = self._module_dashboard_profile(module)
        table = Table(
            title="Activity heat map",
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Signal", style=PALETTE["text_main"], min_width=12)
        for column in profile.heatmap_columns:
            table.add_column(column, justify="center", min_width=6)

        values = self._module_heatmap_values(module, len(profile.heatmap_rows), len(profile.heatmap_columns))
        for row_label, row_values in zip(profile.heatmap_rows, values, strict=True):
            cells: list[object] = [row_label]
            for value in row_values:
                cells.append(self._heatmap_cell(value))
            table.add_row(*cells)
        return table

    def _module_heatmap_values(self, module: ModuleSpec, row_count: int, column_count: int) -> tuple[tuple[int, ...], ...]:
        seed = sum(ord(char) for char in module.key)
        metric_values = tuple(metric[1] for metric in module.metrics)
        rows: list[tuple[int, ...]] = []
        for row_index in range(row_count):
            row: list[int] = []
            for column_index in range(column_count):
                metric = metric_values[(row_index + column_index) % len(metric_values)]
                value = 24 + ((seed + metric + row_index * 17 + column_index * 23) % 72)
                row.append(value)
            rows.append(tuple(row))
        return tuple(rows)

    def _heatmap_cell(self, value: int) -> Text:
        tone = "ok"
        if value >= 75:
            tone = "risk"
        elif value >= 55:
            tone = "warn"
        elif value >= 40:
            tone = "info"
        color = self._tone_text_color(tone)
        text = Text()
        text.append("██ ", style=f"bold {color}")
        text.append(f"{value:02d}", style=PALETTE["text_main"])
        return text

    def _build_attention_lines(self, item: AttentionItem, selected: bool = False) -> tuple[Text, Text]:
        headline = Text()
        marker_style = f"bold {PALETTE['orange_primary']}" if selected else PALETTE["line"]
        headline.append("> " if selected else "  ", style=marker_style)
        headline.append(f"[{item.severity}] ", style=self._status_style(item.emphasis_level))
        headline.append(item.subject, style=f"bold {PALETTE['text_main']}")

        detail = Text()
        detail.append("  ", style=PALETTE["text_main"])
        detail.append(item.summary, style=PALETTE["text_muted"])
        if selected:
            headline.stylize(f"on {PALETTE['bg_soft']}")
            detail.stylize(f"on {PALETTE['bg_soft']}")
        return headline, detail

    def _build_home_action_line(self, index: int, action: HomeAction, selected: bool = False) -> Text:
        text = Text()
        text.append(
            f"[{index}] ",
            style=f"bold {PALETTE['orange_primary']}",
        )
        text.append(
            action.label,
            style=f"bold {PALETTE['orange_primary']}" if selected else f"bold {PALETTE['text_main']}",
        )
        text.append(" | ", style=PALETTE["line"])
        text.append(action.summary, style=PALETTE["text_muted"])
        if selected:
            text.stylize(f"on {PALETTE['bg_soft']}")
        return text

    def _build_picker_lines(self) -> list[Text]:
        lines: list[Text] = []
        for index, listed_module in enumerate(self._picker_modules(), start=1):
            is_selected = index - 1 == self.module_picker_index
            marker = ">" if is_selected else " "
            marker_style = f"bold {PALETTE['orange_primary']}" if is_selected else PALETTE["text_muted"]
            label_style = f"bold {PALETTE['orange_primary']}" if is_selected else PALETTE["text_main"]

            line = Text()
            line.append(f"{marker} ", style=marker_style)
            line.append(f"{index}. {listed_module.label}", style=label_style)
            line.append(f"  [{listed_module.category}]", style=PALETTE["text_muted"])
            lines.append(line)
        return lines

    def _build_conversation_header(self, entry: ConversationEntry) -> Text:
        timestamp = time.strftime("%H:%M:%S | %m-%d-%Y", entry.created_at)
        text = Text()
        if entry.role == "assistant":
            text.append(BT_AGENT_LABEL, style=f"bold {PALETTE['orange_soft']}")
        else:
            text.append("You", style=f"bold {PALETTE['orange_primary']}")
        text.append(" (", style=PALETTE["text_muted"])
        text.append(timestamp, style=PALETTE["text_muted"])
        text.append(")", style=PALETTE["text_muted"])
        return text

    def _build_processing_conversation_header(self) -> Text:
        return self._build_conversation_header(
            ConversationEntry(role="assistant", text="", created_at=time.localtime())
        )

    def _build_processing_status_line(self) -> Text:
        text = Text()
        text.append(self._processing_spinner(), style=f"bold {PALETTE['orange_primary']}")
        text.append(" ", style=PALETTE["text_main"])
        text.append(self.processing_message or "Thinking...", style=PALETTE["text_muted"])
        return text

    def _build_conversation_body(self, entry: ConversationEntry, module: ModuleSpec) -> list[object]:
        renderables: list[object] = []

        if entry.kind == "help":
            renderables.append(self._plain_text(entry.text))
            renderables.append(Text(""))
            renderables.append(self._build_help_text())
        elif entry.kind == "actionable_items":
            renderables.append(self._plain_text(entry.text))
            renderables.append(Text(""))
            renderables.extend(self._build_actionable_items_renderables())
        elif entry.kind == "investigation":
            investigation_case = INVESTIGATION_CASES.get(entry.context_key)
            if investigation_case is not None:
                renderables.extend(self._build_investigation_renderables(investigation_case))
            else:
                renderables.append(self._plain_text(entry.text, style=PALETTE["text_muted"]))
        elif entry.kind == "investigation_action":
            investigation_renderables = self._build_investigation_action_renderables(entry)
            if investigation_renderables:
                renderables.extend(investigation_renderables)
            else:
                renderables.append(self._plain_text(entry.text))
        elif entry.kind == "story_scene":
            story_renderables = self._build_story_renderables(entry.action_key)
            if story_renderables:
                renderables.extend(story_renderables)
            else:
                renderables.append(self._plain_text(entry.text))
        elif entry.kind == "home_action":
            home_action_renderables = self._build_home_action_renderables(entry.action_key)
            if home_action_renderables:
                renderables.extend(home_action_renderables)
            else:
                renderables.append(self._plain_text(entry.text))
        else:
            renderables.append(self._plain_text(entry.text))

        if entry.show_table:
            renderables.append(Text(""))
            renderables.append(self._build_response_table(entry.source_prompt or entry.text, module))

        if entry.show_metrics:
            renderables.append(Text(""))
            renderables.append(self._build_response_metrics(entry.source_prompt or entry.text, module))

        return renderables

    def _build_help_text(self) -> Text:
        text = Text()
        for index, (command, description) in enumerate(COMMAND_HELP):
            self._append_help_command(text, command)
            text.append("  ", style=PALETTE["text_main"])
            text.append(description, style=PALETTE["text_muted"])
            if index < len(COMMAND_HELP) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _append_help_command(self, text: Text, command: str) -> None:
        parts = command.split(" ", maxsplit=1)
        text.append(parts[0], style=f"bold {PALETTE['orange_primary']}")
        if len(parts) > 1:
            text.append(" ", style=PALETTE["text_main"])
            text.append(parts[1], style=PALETTE["text_muted"])

    def _build_actionable_items_renderables(self) -> list[object]:
        renderables: list[object] = []
        for index, item in enumerate(ATTENTION_ITEMS):
            headline, detail = self._build_attention_lines(item, selected=self._is_attention_selected(index))
            renderables.append(headline)
            renderables.append(detail)
            renderables.append(Text(""))
        return renderables

    def _build_investigation_renderables(self, investigation_case: InvestigationCase) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_investigation_header_text(investigation_case))
        renderables.append(Text(""))
        renderables.append(self._build_investigation_decision_strip(investigation_case))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("AI assessment", self._build_investigation_assessment_text(investigation_case)))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Reachable path", self._build_investigation_path_text(investigation_case)))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Linked systems", self._build_investigation_linked_text(investigation_case)))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Checks completed", self._build_investigation_checks_text(investigation_case)))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Evidence gaps", self._build_investigation_gaps_text(investigation_case)))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Recommendation", self._build_investigation_recommendation_text(investigation_case)))
        renderables.append(Text(""))
        renderables.append(Text("Next actions", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_investigation_action_lines(investigation_case))
        return renderables

    def _build_section_heading(self, label: str) -> Text:
        return Text(label, style=f"bold {PALETTE['orange_soft']}")

    def _build_section_block(self, label: str, body: Text) -> Text:
        text = Text()
        text.append_text(self._build_section_heading(label))
        text.append("\n", style=PALETTE["text_main"])
        text.append_text(body)
        return text

    def _build_emphasis_panel(self, body: object) -> Panel:
        return Panel(
            body,
            box=TABLE_BOX,
            expand=True,
            border_style=PALETTE["orange_soft"],
            padding=(0, 1),
            style=f"on {PALETTE['bg_emphasis']}",
        )

    def _build_badge(self, label: str, tone: str) -> Text:
        styles = {
            "muted": f"bold {PALETTE['slate_text']} on {PALETTE['slate_bg']}",
            "info": f"bold {PALETTE['blue_text']} on {PALETTE['blue_bg']}",
            "warn": f"bold {PALETTE['amber_text']} on {PALETTE['amber_bg']}",
            "accent": f"bold {PALETTE['purple_text']} on {PALETTE['purple_bg']}",
            "risk": f"bold {PALETTE['red_text']} on {PALETTE['red_bg']}",
            "ok": f"bold {PALETTE['green_text']} on {PALETTE['green_bg']}",
            "violet": f"bold {PALETTE['violet_text']} on {PALETTE['violet_bg']}",
            "teal": f"bold {PALETTE['teal_text']} on {PALETTE['teal_bg']}",
        }
        badge = Text()
        badge.append(f" {label} ", style=styles.get(tone, styles["muted"]))
        return badge

    def _build_option_badge(self, option: str) -> Text:
        tone = {
            "A": "risk",
            "B": "info",
            "C": "ok",
        }.get(option, "warn")
        return self._build_badge(option, tone)

    def _all_pending_approvals(self) -> tuple[PendingApproval, ...]:
        return tuple(self.pending_approvals)

    def _default_story_context(self) -> StoryContext:
        return StoryContext(role_label=self.user_role)

    def _story_prompt_matches_entry(self, prompt: str) -> bool:
        normalized = " ".join(prompt.strip().lower().split())
        return normalized == STORY_ENTRY_PROMPT

    def _story_context_active(self) -> bool:
        return self.story_context is not None

    def _set_story_context(self, module_key: str, context: StoryContext | None) -> None:
        self.story_context_by_module[module_key] = context
        if self._active_module().key == module_key:
            self.story_context = context

    def _restore_story_context(self, module_key: str) -> None:
        self.story_context = self.story_context_by_module.get(module_key)

    def _clear_story_context(self, module_key: str) -> None:
        self.story_context_by_module[module_key] = None
        if self._active_module().key == module_key:
            self.story_context = None

    def _story_scene_active(self) -> bool:
        return bool(
            self.detail_view_key
            and self.detail_view_key.startswith("story_")
            and not self._story_mode_active()
        )

    def _story_mode_active(self) -> bool:
        return bool(self.detail_view_key and (self.detail_view_key == "story_menu" or self.detail_view_key.startswith("story_mode_")))

    def _capture_story_mode_return_state(self, module_key: str) -> None:
        self.story_mode_return_state_by_module[module_key] = StoryModeReturnState(
            module_picker_active=self.module_picker_active,
            home_navigation_active=self.home_navigation_active,
            investigation_navigation_active=self.investigation_navigation_active,
            investigation_case_key=self.investigation_case_key,
            investigation_action_index=self.investigation_action_index,
            detail_navigation_active=self.detail_navigation_active,
            detail_view_key=self.detail_view_key,
            detail_action_index=self.detail_action_index,
            detail_return_view_key=self.detail_return_view_key,
            verification_profile_key=self.verification_profile_key,
        )

    def _restore_story_mode_return_state(self, module_key: str) -> None:
        saved_state = self.story_mode_return_state_by_module.get(module_key)
        self.story_mode_return_state_by_module[module_key] = None
        if saved_state is None:
            self._clear_detail_state(module_key)
            return

        self.module_picker_active = saved_state.module_picker_active
        self.home_navigation_active = saved_state.home_navigation_active
        self.investigation_navigation_active = saved_state.investigation_navigation_active
        self.investigation_case_key = saved_state.investigation_case_key
        self.investigation_action_index = saved_state.investigation_action_index
        self.detail_navigation_active = saved_state.detail_navigation_active
        self.detail_view_key = saved_state.detail_view_key
        self.detail_action_index = saved_state.detail_action_index
        self.detail_return_view_key = saved_state.detail_return_view_key
        self.verification_profile_key = saved_state.verification_profile_key
        self._remember_investigation_state(module_key)
        self._remember_detail_state(module_key)
        self._set_verification_profile(module_key, saved_state.verification_profile_key)

    def _story_scene_name(self, scene_key: str) -> str:
        return {
            "story_ambiguity": "ambiguity handling",
            "story_scope_confirm": "scope confirmation",
            "story_scope_custom": "scope customization",
            "story_role_limits": "role limits",
            "story_memory_state": "memory state",
            "story_findings": "findings summary",
            "story_session_relatedness": "session relatedness",
            "story_approval_evidence": "approval evidence",
            "story_privilege_path": "privilege path",
            "story_assets": "affected assets",
            "story_asset_detail": "top asset detail",
            "story_containment": "containment options",
            "story_incident_review": "incident review draft",
            "story_handoff": "controlled handoff",
            "story_approval_queue": "approval queue",
            "story_export": "summary export",
        }.get(scene_key, "story view")

    def _story_scene_result_text(self, scene_key: str, *, returned: bool = False) -> str:
        prefix = "Returned to" if returned else "Opened"
        return f"{prefix} {self._story_scene_name(scene_key)}."

    def _story_pending_approval(self, approval_key: str) -> PendingApproval | None:
        for approval in self._all_pending_approvals():
            if approval.key == approval_key:
                return approval
        return None

    def _stage_story_pending_approval(self, approval: PendingApproval) -> None:
        for index, existing in enumerate(self.pending_approvals):
            if existing.key == approval.key:
                self.pending_approvals[index] = approval
                break
        else:
            self.pending_approvals.append(approval)
        self.pending_approval_state_by_key[approval.key] = "waiting"

    def _ensure_story_incident_ticket(self, context: StoryContext) -> str:
        if context.incident_ticket is None:
            context.incident_ticket = "INC-24817"
        return context.incident_ticket

    def _prepared_story_approval_keys(self, *, include_session: bool, include_path: bool) -> tuple[str, ...]:
        keys: list[str] = []
        if include_session:
            keys.append("story-pra-2214-terminate")
        if include_path:
            keys.append("story-aws-prod-admin-suspend")
        return tuple(keys)

    def _story_primary_prepared_key(self) -> str | None:
        context = self._story_current_context()
        if context.prepared_approval_keys:
            return context.prepared_approval_keys[0]
        return None

    def _open_story_mode(self, module_key: str) -> None:
        if not self._story_mode_active():
            self._capture_story_mode_return_state(module_key)
        self.module_picker_active = False
        self.home_navigation_active = False
        self.investigation_navigation_active = False
        self.detail_navigation_active = True
        self.detail_view_key = "story_menu"
        self.detail_action_index = 0
        self.detail_return_view_key = None
        self._remember_detail_state(module_key)

    def _close_story_mode(self, module_key: str) -> None:
        self._restore_story_mode_return_state(module_key)

    def _graph_spotlight_for_key(self, graph_key: str) -> GraphSpotlight | None:
        for spotlight in GRAPH_SPOTLIGHTS:
            if spotlight.key == graph_key:
                return spotlight
        return None

    def _graph_catalog_index_for_key(self, graph_key: str) -> int:
        for index, spotlight in enumerate(GRAPH_SPOTLIGHTS):
            if spotlight.key == graph_key:
                return index
        return 0

    def _current_graph_spotlight(self) -> GraphSpotlight | None:
        if self.detail_view_key and self.detail_view_key.startswith("graph_focus:"):
            return self._graph_spotlight_for_key(self.detail_view_key.split(":", maxsplit=1)[1])
        return None

    def _true_privilege_graph_actions(self) -> tuple[InvestigationAction, ...]:
        actions: list[InvestigationAction] = []
        for spotlight in GRAPH_SPOTLIGHTS:
            actions.append(
                InvestigationAction(
                    key=f"select_graph:{spotlight.key}",
                    label=f"view {spotlight.label}",
                    summary=f"{spotlight.scope} | {spotlight.note}",
                    result=f"Graph opened for {spotlight.label}.",
                )
            )
        return tuple(actions)

    def _pending_approval_for_key(self, approval_key: str) -> PendingApproval | None:
        for approval in self._all_pending_approvals():
            if approval.key == approval_key:
                return approval
        return None

    def _pending_approval_index(self, approval_key: str) -> int:
        for index, approval in enumerate(self._all_pending_approvals()):
            if approval.key == approval_key:
                return index
        return 0

    def _current_pending_approval(self) -> PendingApproval | None:
        if self.detail_view_key and self.detail_view_key.startswith("approval_detail:"):
            return self._pending_approval_for_key(self.detail_view_key.split(":", maxsplit=1)[1])
        selected_action = self._selected_detail_action()
        if selected_action and selected_action.key.startswith("approval_detail:"):
            return self._pending_approval_for_key(selected_action.key.split(":", maxsplit=1)[1])
        return None

    def _pending_approval_state(self, approval_key: str) -> str:
        return self.pending_approval_state_by_key.get(approval_key, "waiting")

    def _pending_approval_tone(self, approval: PendingApproval) -> str:
        state = self._pending_approval_state(approval.key)
        if state == "approved":
            return "ok"
        if state == "on_hold":
            return "info"
        return approval.tone

    def _pending_approval_state_badge(self, approval: PendingApproval) -> Text:
        state = self._pending_approval_state(approval.key)
        label = {
            "waiting": "waiting",
            "approved": "approved",
            "on_hold": "on hold",
        }.get(state, state)
        return self._build_badge(label, self._pending_approval_tone(approval))

    def _pending_approval_queue_actions(self) -> tuple[InvestigationAction, ...]:
        actions: list[InvestigationAction] = []
        for approval in self._all_pending_approvals():
            state = self._pending_approval_state(approval.key)
            actions.append(
                InvestigationAction(
                    key=f"approval_detail:{approval.key}",
                    label=f"review {approval.request}",
                    summary=f"{approval.source} | {state.replace('_', ' ')} | {approval.requester} -> {approval.resource}",
                    result=f"Approval details opened for {approval.request}.",
                )
            )
        return tuple(actions)

    def _pending_approval_selected_index(self) -> int:
        if self.detail_view_key == "pending_approvals":
            return self.detail_action_index
        approval = self._current_pending_approval()
        if approval is None:
            return 0
        return self._pending_approval_index(approval.key)

    def _build_investigation_header_text(self, investigation_case: InvestigationCase) -> Text:
        text = Text()
        text.append(investigation_case.identity, style=f"bold {PALETTE['orange_soft']}")
        text.append("\n", style=PALETTE["text_main"])
        text.append(self._investigation_header_signals(investigation_case), style=PALETTE["text_muted"])
        return text

    def _build_investigation_decision_strip(self, investigation_case: InvestigationCase) -> Text:
        text = Text()
        text.append(investigation_case.priority, style=self._status_style("risk"))
        text.append(" | ", style=PALETTE["line"])
        text.append(f"risk {investigation_case.risk_score}", style=self._status_style("warn"))
        text.append(" ", style=PALETTE["text_main"])
        text.append_text(pipe_bar(investigation_case.risk_score, width=8))
        text.append(" | ", style=PALETTE["line"])
        self._append_status_pair(text, "confidence", investigation_case.confidence, "ok")
        text.append(" | ", style=PALETTE["line"])
        self._append_status_pair(text, "blast radius", self._investigation_blast_radius_level(investigation_case), "risk")
        text.append(" | ", style=PALETTE["line"])
        self._append_status_pair(text, "session", self._investigation_session_state(investigation_case), "warn")
        return text

    def _append_status_pair(self, text: Text, label: str, value: str, level: str) -> None:
        text.append(f"{label}: ", style=PALETTE["text_muted"])
        text.append(value, style=self._status_style(level))

    def _build_investigation_assessment_text(self, investigation_case: InvestigationCase) -> Text:
        text = Text()
        lines = self._investigation_assessment_lines(investigation_case)
        for index, line in enumerate(lines):
            text.append(line, style=PALETTE["text_main"])
            if index < len(lines) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_investigation_path_text(self, investigation_case: InvestigationCase) -> Text:
        text = Text()
        text.append(investigation_case.identity, style=f"bold {PALETTE['text_main']}")
        text.append(" -> ", style=PALETTE["text_muted"])
        text.append("current group inheritance", style=PALETTE["text_main"])
        text.append(" -> ", style=PALETTE["text_muted"])
        text.append("AWS production admin", style=f"bold {PALETTE['orange_pale']}")
        return text

    def _build_investigation_linked_text(self, investigation_case: InvestigationCase) -> Text:
        text = Text()
        for index, system in enumerate(investigation_case.linked_systems):
            system_style = f"bold {PALETTE['orange_pale']}" if system in {"aws-prod-admin", "pra-2214"} else PALETTE["text_main"]
            text.append(system, style=system_style)
            if index < len(investigation_case.linked_systems) - 1:
                text.append(" | ", style=PALETTE["line"])
        return text

    def _build_investigation_checks_text(self, investigation_case: InvestigationCase) -> Text:
        text = Text()
        lines = self._investigation_check_lines(investigation_case)
        for index, item in enumerate(lines):
            text.append("+ ", style=f"bold {PALETTE['ok']}")
            text.append(item, style=PALETTE["text_main"])
            if index < len(lines) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_investigation_gaps_text(self, investigation_case: InvestigationCase) -> Text:
        text = Text()
        for index, gap in enumerate(investigation_case.evidence_gaps):
            text.append("! ", style=f"bold {PALETTE['warn']}")
            text.append(gap, style=PALETTE["text_main"] if any(token in gap for token in ("delayed", "pending")) else PALETTE["text_muted"])
            if index < len(investigation_case.evidence_gaps) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_investigation_recommendation_text(self, investigation_case: InvestigationCase) -> Text:
        return Text(investigation_case.recommendation, style=PALETTE["text_main"])

    def _build_bullet_text(self, values: tuple[str, ...]) -> Text:
        text = Text()
        for index, value in enumerate(values):
            text.append("- ", style=f"bold {PALETTE['orange_pale']}")
            text.append(value, style=PALETTE["text_main"])
            if index < len(values) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_investigation_action_lines(self, investigation_case: InvestigationCase) -> list[Text]:
        lines: list[Text] = []
        for index, action in enumerate(investigation_case.next_actions):
            selected = (
                self.investigation_navigation_active
                and self.investigation_case_key == investigation_case.key
                and self.investigation_action_index == index
            )
            line = Text()
            line.append("> " if selected else "  ", style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["line"])
            line.append(action.label, style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["text_main"])
            lines.append(line)
        return lines

    def _build_investigation_action_renderables(self, entry: ConversationEntry) -> list[object]:
        if entry.context_key != "amy.miller":
            return []
        if entry.action_key == "view_live_session":
            return self._build_live_session_renderables()
        if entry.action_key == "inspect_target_activity":
            return self._build_target_activity_renderables()
        if entry.action_key == "show_privilege_path":
            return self._build_privilege_path_renderables()
        if entry.action_key == "simulate_containment":
            return self._build_containment_renderables()
        if entry.action_key == "post_action_verification":
            return self._build_verification_renderables()
        return []

    def _story_current_context(self) -> StoryContext:
        return self.story_context or self._default_story_context()

    def _build_story_renderables(self, action_key: str) -> list[object]:
        if action_key == "story_ambiguity":
            return self._build_story_ambiguity_renderables()
        if action_key == "story_scope_confirm":
            return self._build_story_scope_confirm_renderables()
        if action_key == "story_scope_custom":
            return self._build_story_scope_custom_renderables()
        if action_key == "story_role_limits":
            return self._build_story_role_limits_renderables()
        if action_key == "story_memory_state":
            return self._build_story_memory_state_renderables()
        if action_key == "story_findings":
            return self._build_story_findings_renderables()
        if action_key == "story_session_relatedness":
            return self._build_story_session_relatedness_renderables()
        if action_key == "story_approval_evidence":
            return self._build_story_approval_evidence_renderables()
        if action_key == "story_privilege_path":
            return self._build_story_privilege_path_renderables()
        if action_key == "story_assets":
            return self._build_story_assets_renderables()
        if action_key == "story_asset_detail":
            return self._build_story_asset_detail_renderables()
        if action_key == "story_containment":
            return self._build_story_containment_renderables()
        if action_key == "story_incident_review":
            return self._build_story_incident_review_renderables()
        if action_key == "story_handoff":
            return self._build_story_handoff_renderables()
        if action_key == "story_approval_queue":
            return self._build_story_approval_queue_renderables()
        if action_key == "story_export":
            return self._build_story_export_renderables()
        return []

    def _build_story_header_text(self, title: str, subtitle: str) -> Text:
        text = Text()
        text.append(title, style=f"bold {PALETTE['orange_soft']}")
        text.append("\n", style=PALETTE["text_main"])
        text.append(subtitle, style=PALETTE["text_muted"])
        return text

    def _build_story_state_line(self, parts: tuple[tuple[str, str], ...]) -> Text:
        text = Text()
        for index, (label, tone) in enumerate(parts):
            text.append("[", style=PALETTE["line"])
            text.append(label, style=self._status_style(tone))
            text.append("]", style=PALETTE["line"])
            if index < len(parts) - 1:
                text.append(" ", style=PALETTE["text_main"])
        return text

    def _build_story_followup_lines(self, scene_key: str) -> list[Text]:
        actions = self._active_story_detail_actions(scene_key)
        lines: list[Text] = []
        for index, action in enumerate(actions):
            selected = (
                self.detail_navigation_active
                and self.detail_view_key == scene_key
                and self.detail_action_index == index
            )
            line = Text()
            line.append("> " if selected else "  ", style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["line"])
            line.append(action.label, style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["text_main"])
            if selected:
                line.stylize(f"on {PALETTE['bg_soft']}")
            lines.append(line)
        return lines

    def _build_story_memory_panel(self) -> Panel:
        context = self._story_current_context()
        text = Text()
        rows = (
            ("entity", context.entity),
            ("environment", context.environment or "missing"),
            ("time range", context.time_range or "missing"),
            ("goal", context.goal or "missing"),
        )
        width = max(len(label) for label, _ in rows) + 2
        for index, (label, value) in enumerate(rows):
            text.append(label.ljust(width), style=PALETTE["text_muted"])
            text.append(value, style=f"bold {PALETTE['text_main']}" if value != "missing" else self._status_style("warn"))
            if index < len(rows) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return Panel(text, title="Active investigation", box=TABLE_BOX, expand=True, border_style=PALETTE["line"], padding=(0, 1))

    def _build_story_ambiguity_slots_panel(self) -> Panel:
        context = self._story_current_context()
        rows = (
            ("environment", context.environment),
            ("time range", context.time_range),
            ("goal", context.goal),
            ("acting role", context.role_label),
        )
        text = Text()
        for index, (label, value) in enumerate(rows):
            text.append(label.ljust(16), style=PALETTE["text_muted"])
            text.append(". ", style=PALETTE["line"])
            if value is None:
                text.append("missing", style=self._status_style("warn"))
            else:
                text.append("resolved", style=self._status_style("ok"))
                text.append("  ", style=PALETTE["text_main"])
                text.append(value, style=PALETTE["text_main"])
            if index < len(rows) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return Panel(text, title="Missing context", box=TABLE_BOX, expand=True, border_style=PALETTE["line"], padding=(0, 1))

    def _build_story_planner_text(self) -> Text:
        steps = (
            "classify task",
            "inspect identity risk",
            "inspect live privileged session",
            "compare approval / entitlement context",
            "summarize findings",
            "recommend safe next steps",
        )
        text = Text()
        for index, step in enumerate(steps, start=1):
            text.append(f"{index}. ", style=f"bold {PALETTE['orange_primary']}")
            text.append(step, style=PALETTE["text_main"])
            if index < len(steps):
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_story_sources_text(self) -> Text:
        text = Text()
        sources = ("Identity Security Insights", "Privileged Remote Access", "Password Safe", "Entitle")
        for index, source in enumerate(sources):
            text.append("- ", style=f"bold {PALETTE['orange_pale']}")
            text.append(source, style=PALETTE["text_main"])
            if index < len(sources) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_story_restricted_text(self) -> Text:
        text = Text()
        for index, item in enumerate(STORY_ROLE_RESTRICTIONS):
            text.append("- ", style=f"bold {PALETTE['warn']}")
            text.append(item, style=PALETTE["text_main"])
            if index < len(STORY_ROLE_RESTRICTIONS) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_story_source_alignment_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Source", min_width=20)
        table.add_column("State", min_width=12)
        table.add_column("Why it matters", min_width=44)
        rows = (
            ("Identity Security Insights", "linked", "svc-backup-ops still resolves into a privileged production path"),
            ("Privileged Remote Access", "active", "pra-2214 is live and already interacting with production scope"),
            ("Password Safe", "no proof", "no attached evidence currently explains the active privileged work"),
            ("Entitle", "mismatch", "the latest production approval artifact does not cleanly match the live session"),
        )
        for source, state, note in rows:
            tone = "ok" if state == "linked" else "warn" if state in {"no proof", "mismatch"} else "accent"
            table.add_row(Text(source, style=PALETTE["text_main"]), self._build_badge(state, tone), Text(note, style=PALETTE["text_muted"]))
        return table

    def _build_story_privilege_graph_text(self) -> Text:
        context = self._story_current_context()
        text = Text()
        self._append_privilege_path_line(text, "", "ID", "accent", context.entity, f"bold {PALETTE['text_main']}")
        self._append_privilege_path_connector(text, "  ")
        self._append_privilege_path_line(text, "  +-- ", "GRP", "violet", "grp-cloud-admins", f"bold {PALETTE['violet']}")
        self._append_privilege_path_line(text, "      +-- ", "ROLE", "risk", "aws-prod-admin", self._status_style("risk"))
        self._append_privilege_path_line(text, "          +-- ", "SESSION", "teal", context.active_session, f"bold {PALETTE['teal']}", suffix="ACTIVE", suffix_style=self._status_style("warn"))
        self._append_privilege_path_line(text, "          +-- ", "APPROVAL", "warn", "evidence missing", self._status_style("warn"))
        self._append_privilege_path_line(text, "          +-- ", "SCOPE", "info", "production", PALETTE["text_main"])
        return text

    def _build_story_timeline_text(self) -> Text:
        text = Text()
        rows = (
            ("19:32", "OPEN", "session opened"),
            ("19:34", "SCOPE", "admin scope confirmed"),
            ("19:36", "REVIEW", "backup policy viewed"),
            ("19:37", "FLAG", "credential-related action attempted"),
            ("19:38", "READ", "production config read"),
        )
        for index, (time_label, tag, detail) in enumerate(rows):
            marker = "o" if index < 2 else "^"
            text.append(f"{time_label}  {marker} {tag:<7} {detail}", style=PALETTE["text_main"])
            if index < len(rows) - 1:
                text.append("\n", style=PALETTE["text_main"])
                text.append("       |", style=PALETTE["text_muted"])
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_story_signal_bars_text(self, rows: tuple[tuple[str, int, str], ...]) -> Text:
        width = max(len(label) for label, _, _ in rows) + 2
        text = Text()
        for index, (label, value, suffix) in enumerate(rows):
            text.append(label.ljust(width), style=PALETTE["text_muted"])
            text.append_text(self._bar(value, width=10))
            text.append(f" {suffix}", style=PALETTE["text_main"])
            if index < len(rows) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_story_asset_grouping_text(self) -> Text:
        text = Text()
        text.append("Critical\n", style=f"bold {PALETTE['risk']}")
        text.append("- prod-sql-07      session overlap\n", style=PALETTE["text_main"])
        text.append("\nHigh\n", style=f"bold {PALETTE['orange_pale']}")
        text.append("- prod-app-12      path overlap\n", style=PALETTE["text_main"])
        text.append("- prod-app-14      path overlap\n", style=PALETTE["text_main"])
        text.append("\nMedium\n", style=f"bold {PALETTE['teal']}")
        text.append("- prod-backup-03   behavior drift", style=PALETTE["text_main"])
        return text

    def _build_story_containment_options_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Action", min_width=25)
        table.add_column("Risk", min_width=10)
        table.add_column("Session", min_width=15)
        table.add_column("Path", min_width=12)
        table.add_column("Impact", min_width=14)
        table.add_column("Approval", min_width=10)
        rows = (
            ("revoke PRA session only", "91 -> 63", "closed", "remains", "medium", "yes"),
            ("suspend reachable path only", "91 -> 41", "may persist", "broken", "low-med", "yes"),
            ("do both after approval", "91 -> 19", "closed", "broken", "med-high", "yes"),
            ("stage incident review only", "91 -> 91", "unchanged", "unchanged", "low", "no"),
        )
        for action, risk, session, path, impact, approval in rows:
            tone = "ok" if risk.endswith("19") else "warn" if approval == "yes" else "info"
            table.add_row(
                Text(action, style=PALETTE["text_main"]),
                Text(risk, style=self._status_style("warn" if tone != "ok" else "ok")),
                Text(session, style=PALETTE["text_main"]),
                Text(path, style=PALETTE["text_main"]),
                Text(impact, style=PALETTE["text_main"]),
                self._build_badge(approval, "risk" if approval == "yes" else "ok"),
            )
        return table

    def _build_story_decision_cues_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Cue", min_width=18)
        table.add_column("Best fit", min_width=20)
        table.add_column("Why", min_width=42)
        rows = (
            ("fastest", "do both after approval", "best immediate and durable reduction once a reviewer approves"),
            ("most durable", "suspend reachable path only", "breaks future path reuse even if the current session is revalidated"),
            ("lowest disruption", "stage incident review only", "keeps evidence moving without touching production access"),
        )
        for cue, choice, why in rows:
            table.add_row(Text(cue, style=f"bold {PALETTE['orange_pale']}"), Text(choice, style=PALETTE["text_main"]), Text(why, style=PALETTE["text_muted"]))
        return table

    def _build_story_prepared_packet_text(self) -> Text:
        context = self._story_current_context()
        text = Text()
        items: list[str] = []
        if "story-pra-2214-terminate" in context.prepared_approval_keys:
            items.append(f"terminate session: {context.active_session}")
        if "story-aws-prod-admin-suspend" in context.prepared_approval_keys:
            items.append(f"suspend path: {context.reachable_path}")
        if not items:
            items.append("incident review only: no privileged action staged")
        items.extend(
            (
                f"reason: correlated privileged activity tied to {context.entity}",
                "urgency: high",
            )
        )
        for index, item in enumerate(items):
            text.append("- ", style=f"bold {PALETTE['orange_pale']}")
            text.append(item, style=PALETTE["text_main"])
            if index < len(items) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_story_prepared_queue_table(self) -> Table:
        context = self._story_current_context()
        staged = set(context.prepared_approval_keys)
        approvals = list(self._all_pending_approvals())
        approvals.sort(key=lambda approval: (approval.key not in staged, approval.source, approval.request))
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Src", min_width=10)
        table.add_column("Request", min_width=28)
        table.add_column("Requester", min_width=20)
        table.add_column("State", min_width=14)
        for approval in approvals:
            highlight = approval.key in staged
            table.add_row(
                Text(approval.source, style=f"bold {PALETTE['purple']}"),
                Text(approval.request, style=PALETTE["text_main"]),
                Text(approval.requester, style=PALETTE["text_main"]),
                self._pending_approval_state_badge(approval),
                style=f"on {PALETTE['bg_soft']}" if highlight else "",
            )
        return table

    def _build_story_ambiguity_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Ambiguity handling", "Intent received but scope is still missing"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("active investigation", "info"), ("role-aware", "ok"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Intent line", Text("Investigate suspicious lateral movement tied to a service account.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(self._build_story_ambiguity_slots_panel())
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Current role", Text("SOC Analyst II can investigate, compare approvals, and prepare requests, but cannot execute high-risk privileged changes.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Why I'm asking", Text("Pathfinder does not have enough scope yet to recommend a production-safe next move. Environment, time range, and goal are still required.", style=PALETTE["text_muted"])))
        renderables.append(Text(""))
        renderables.append(Text("Select next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_ambiguity"))
        return renderables

    def _build_story_scope_confirm_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Scope confirmation", "Session memory is now active for the current investigation"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("active investigation", "info"), ("session memory active", "ok"), ("role-aware", "ok"))))
        renderables.append(Text(""))
        renderables.append(self._build_story_memory_panel())
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Planner", self._build_story_planner_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Data sources to query", self._build_story_sources_text()))
        renderables.append(Text(""))
        renderables.append(Text("Continue", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_scope_confirm"))
        return renderables

    def _build_story_scope_custom_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Customize scope", "Pathfinder is waiting for the minimum investigation scope"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("active investigation", "info"), ("confidence: medium", "warn"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Custom input guidance", Text("Use a follow-up like: production, last 24 hours, include containment recommendations.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(self._build_story_ambiguity_slots_panel())
        renderables.append(Text(""))
        renderables.append(Text("Select next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_scope_custom"))
        return renderables

    def _build_story_role_limits_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Role limits", "Current operator boundaries for the active story"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("role-aware", "ok"), ("restricted", "warn"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Allowed in this role", self._build_bullet_text(STORY_ROLE_CAPABILITIES)))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Restricted in this role", self._build_story_restricted_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Boundary note", Text("Pathfinder can recommend and prepare reviewer-facing changes, but the analyst cannot bypass approval checks or reveal blocked data.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(Text("Select next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_role_limits"))
        return renderables

    def _build_story_memory_state_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Memory state", "Session-scoped memory for the active investigation"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("session memory active", "ok"), ("role-aware", "ok"))))
        renderables.append(Text(""))
        renderables.append(self._build_story_memory_panel())
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Retention rules", Text("Pathfinder is keeping the entity, environment, time range, and goal in session memory. It is not storing secrets, raw privileged content, or one-time credentials.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(Text("Select next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_memory_state"))
        return renderables

    def _build_story_findings_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Findings summary", "svc-backup-ops now anchors the active investigation"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("active investigation", "info"), ("role-aware", "ok"), ("restricted", "warn"), ("session memory active", "ok"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Decision strip", Text("risk 91 | active PRA session pra-2214 | reachable admin path | approval evidence missing", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("AI assessment", Text("Pathfinder linked svc-backup-ops to a reachable production admin path, an active privileged session, and an approval artifact that does not yet line up cleanly. The pattern is notable, but some evidence is still restricted or missing.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Focused path"))
        renderables.append(self._build_emphasis_panel(self._build_story_privilege_graph_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Source alignment"))
        renderables.append(self._build_story_source_alignment_table())
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Restricted in your role", self._build_story_restricted_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Recommendation", Text("Assess whether the active session is likely related, then compare approval evidence before preparing any privileged response.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(Text("Investigate next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_findings"))
        return renderables

    def _build_story_session_relatedness_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Session relatedness", "Likely related, not confirmed"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("confidence: medium", "warn"), ("role-aware", "ok"), ("active investigation", "info"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Supporting signals", self._build_bullet_text(("temporal overlap between svc-backup-ops activity and pra-2214", "the same reachable path still lands in aws-prod-admin", "production reads began shortly after the privileged session opened"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Missing evidence", self._build_bullet_text(("no confirmed approval evidence tied directly to the live session", "raw privileged session contents are blocked in this role", "intent is still inferred rather than proven"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Timeline"))
        renderables.append(self._build_emphasis_panel(self._build_story_timeline_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Confidence meter", self._build_story_signal_bars_text((("temporal overlap", 82, "high"), ("identity overlap", 79, "high"), ("intent certainty", 58, "medium"), ("attribution confidence", 61, "medium")))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Sensitivity", self._build_story_signal_bars_text((("session risk", 84, "high"), ("target sensitivity", 95, "critical"), ("approval confidence", 31, "low")))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Best current read", Text("The privileged session is likely related to the same service-account path, but the evidence is still short of direct attribution. Treat it as medium confidence with escalation-ready evidence.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(Text("Decide next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_session_relatedness"))
        return renderables

    def _build_story_approval_evidence_renderables(self) -> list[object]:
        context = self._story_current_context()
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Approval evidence", "Role-aware comparison across PRA, Password Safe, and Entitle"))
        renderables.append(Text(""))
        labels = [("role-aware", "ok"), ("restricted", "warn")]
        if context.approval_proof_requested:
            labels.append(("approval proof requested", "info"))
        renderables.append(self._build_story_state_line(tuple(labels)))
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Evidence comparison"))
        renderables.append(self._build_story_source_alignment_table())
        renderables.append(Text(""))
        renderables.append(self._build_section_block("What is blocked", Text("This role can compare approval state and mismatches, but it cannot reveal restricted secrets, raw session contents, or hidden credential details.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Recommendation", Text("Use the mismatch as approval-ready evidence, then move to the containment options if the session remains active.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(Text("Decide next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_approval_evidence"))
        return renderables

    def _build_story_privilege_path_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Privilege path", "Service-account path into production admin"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("active investigation", "info"), ("approval required", "warn"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Focused path"))
        renderables.append(self._build_emphasis_panel(self._build_story_privilege_graph_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Why it matters", Text("The same group-to-role edge still exposes aws-prod-admin. Pathfinder can recommend suspending that path, but this analyst cannot execute the change directly.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Best break point", Text("grp-cloud-admins -> aws-prod-admin is the cleanest identity-native break point and is safer than broad downstream containment.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(Text("Decide next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_privilege_path"))
        return renderables

    def _build_story_assets_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Affected assets", "Using the active investigation context already in session memory"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("session memory active", "ok"), ("active investigation", "info"))))
        renderables.append(Text(""))
        renderables.append(self._build_story_memory_panel())
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Asset grouping", self._build_story_asset_grouping_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Severity bars", self._build_story_signal_bars_text((("critical", 10, "1"), ("high", 20, "2"), ("medium", 10, "1")))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Why these are grouped this way", Text("Critical assets have direct session overlap. High assets sit on the same reachable path. Medium assets show contextual drift but no direct privileged overlap yet.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Highest-priority review", Text("prod-sql-07 is the top review target because it already overlaps the live session and the reachable admin path.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(Text("Decide next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_assets"))
        return renderables

    def _build_story_asset_detail_renderables(self) -> list[object]:
        context = self._story_current_context()
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Field", min_width=18, style=PALETTE["text_muted"])
        table.add_column("Value", min_width=28)
        table.add_column("Signal", min_width=14)
        rows = (
            ("asset", Text(context.top_asset, style=f"bold {PALETTE['teal']}"), self._build_badge("critical", "risk")),
            ("relationship", Text("session overlap + path overlap", style=PALETTE["text_main"]), self._build_badge("linked", "accent")),
            ("latest signal", Text("production config read at 19:38", style=PALETTE["text_main"]), self._build_badge("recent", "warn")),
            ("review priority", Text("review before any broader production spread", style=PALETTE["text_main"]), self._build_badge("top", "ok")),
        )
        for label, value, signal in rows:
            table.add_row(label, value, signal)

        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Top asset detail", "Focused review target inside the active investigation"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("active investigation", "info"), ("critical asset", "risk"), ("session memory active", "ok"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Asset detail"))
        renderables.append(table)
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Why Pathfinder surfaced this first", Text("prod-sql-07 is the highest-priority review because the asset already overlaps the live privileged session and sits directly on the reachable production admin path.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Suggested next move", Text("Use this asset detail as supporting evidence when comparing path-break options or preparing an incident review packet.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(Text("Decide next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_asset_detail"))
        return renderables

    def _build_story_containment_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Containment options", "BeyondTrust-native access moves, not downstream host isolation"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("active investigation", "info"), ("approval required", "warn"), ("role-aware", "ok"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Current posture", Text("Current risk is 91. pra-2214 is still active, the reachable admin path remains intact, and approval evidence is still incomplete.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Containment options"))
        renderables.append(self._build_story_containment_options_table())
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Risk reduction view", self._build_story_signal_bars_text((("current risk", 91, "91"), ("revoke session", 63, "63"), ("suspend path", 41, "41"), ("do both", 19, "19")))))
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Decision cues"))
        renderables.append(self._build_story_decision_cues_table())
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Recommended response", Text("Prepare the combined response packet. It delivers the strongest reduction while keeping the analyst inside role boundaries and leaving the reviewer in control of the privileged change.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Boundary check", Text("This role can recommend and prepare reviewer-facing actions. It cannot finalize privileged session termination or reachable-path suspension without approval.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(Text("Decide next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_containment"))
        return renderables

    def _build_story_incident_review_renderables(self) -> list[object]:
        context = self._story_current_context()
        ticket = self._ensure_story_incident_ticket(context)
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Incident review draft", "Evidence is packaged, but privileged execution is still blocked"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("role-aware", "ok"), ("restricted", "warn"), ("session memory active", "ok"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Draft summary", Text(f"{ticket} ties together the active PRA session, the reachable admin path, approval mismatch, and the grouped affected assets for reviewer handoff.", style=PALETTE['text_main'])))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Prepared evidence", self._build_bullet_text(("session timeline attached", "privilege path summary attached", "approval mismatch attached", "affected asset grouping attached"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Why this stays a draft", Text("The SOC analyst can create the review and prepare the recommendation, but privileged remediation still requires a reviewer to approve the staged change.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(Text("Decide next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_incident_review"))
        return renderables

    def _build_story_handoff_renderables(self) -> list[object]:
        context = self._story_current_context()
        ticket = self._ensure_story_incident_ticket(context)
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Controlled handoff", "Approval-ready packet prepared without executing the privileged change"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("approval required", "warn"), ("session memory active", "ok"), ("active investigation", "info"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Prepared for approval", self._build_story_prepared_packet_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Created artifacts", Text(f"incident review: {ticket}\napproval workflow: pending reviewer\nsession memory: active", style=PALETTE['text_main'])))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Why execution is blocked", Text("The recommended privileged actions are high-impact and production-linked. Pathfinder can package the request and evidence, but a reviewer must approve before execution.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Next safe actions", Text("Open the approval queue, review the draft incident record, or export the summary while keeping the live investigation in session memory.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(Text("Decide next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_handoff"))
        return renderables

    def _build_story_approval_queue_renderables(self) -> list[object]:
        context = self._story_current_context()
        staged_count = len(context.prepared_approval_keys)
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Approval queue", "Staged requests are visible but still waiting on reviewer action"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("approval required", "warn"), ("review pending", "info"), ("session memory active", "ok"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Queue focus", Text(f"{staged_count} prepared request(s) from the active story are highlighted below for reviewer handoff.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(self._build_story_prepared_queue_table())
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Boundary note", Text("The main demo path stops here. Pathfinder can stage, review, and hold requests, but it does not auto-approve privileged changes.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(Text("Decide next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_approval_queue"))
        return renderables

    def _build_story_export_renderables(self) -> list[object]:
        context = self._story_current_context()
        ticket = self._ensure_story_incident_ticket(context)
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Summary export", "Concise handoff package prepared for reviewers and incident partners"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("export ready", "ok"), ("session memory active", "ok"), ("role-aware", "ok"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Export includes", self._build_bullet_text((f"incident review reference: {ticket}", "service-account findings summary", "session timeline and confidence read", "approval mismatch comparison", "affected asset grouping and recommended path break"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Export posture", Text("This export is evidence-first and concise. It is designed to move the case forward without exposing blocked secrets or raw session contents.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.append(Text("Decide next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines("story_export"))
        return renderables

    def _build_story_menu_lines(self) -> list[Text]:
        lines: list[Text] = []
        for index, action in enumerate(STORY_MENU_ACTIONS, start=1):
            selected = self.detail_navigation_active and self.detail_view_key == "story_menu" and self.detail_action_index == index - 1
            line = Text()
            line.append(f"[{index}] ", style=f"bold {PALETTE['orange_primary']}")
            line.append(action.label, style=f"bold {PALETTE['orange_primary']}" if selected else f"bold {PALETTE['text_main']}")
            line.append(" | ", style=PALETTE["line"])
            line.append(action.summary, style=PALETTE["text_muted"])
            if selected:
                line.stylize(f"on {PALETTE['bg_soft']}")
            lines.append(line)
        return lines

    def _build_story_mode_body_text(self, lines: tuple[str, ...]) -> Text:
        text = Text()
        for index, line in enumerate(lines):
            if line == "":
                text.append("\n", style=PALETTE["text_main"])
            elif line.startswith("[") and line.endswith("]"):
                text.append(line, style=PALETTE["text_muted"])
            elif line in {"Probabilistic UX thinking", "Behavior spec", "Memory design", "Boundary and control", "Full AI-native structure", "Demo story summary", "Key idea"}:
                text.append(line, style=f"bold {PALETTE['orange_soft']}")
            elif line.startswith("Pathfinder should") or line.startswith("Security investigation assistant") or line.startswith("Summary") or line.startswith("Why it matters") or line.startswith("Evidence") or line.startswith("Recommendation") or line.startswith("Approval needed"):
                text.append(line, style=PALETTE["text_main"])
            elif line.startswith("Can ") or line.startswith("Does ") or line.startswith("Is ") or line.startswith("What ") or line.startswith("Who ") or line.startswith("How "):
                text.append(line, style=f"bold {PALETTE['text_main']}")
            elif "->" in line:
                text.append(line, style=PALETTE["text_main"])
            else:
                text.append(line, style=PALETTE["text_main"])
            if index < len(lines) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_story_menu_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_story_header_text("Story mode", "Hidden presentation views for screenshots and blog use"))
        renderables.append(Text(""))
        renderables.append(self._build_story_state_line((("story mode", "info"), ("presentation only", "warn"))))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Select a design lens", Text("These views are poster-like references for the AI-native Pathfinder concept. They do not change runtime state or approvals.", style=PALETTE["text_main"])))
        renderables.append(Text(""))
        renderables.extend(self._build_story_menu_lines())
        renderables.append(Text(""))
        renderables.append(Text("Use Up/Down and Enter to open a poster. Esc or q returns.", style=PALETTE["text_muted"]))
        return renderables

    def _build_story_mode_renderables(self, scene_key: str) -> list[object]:
        content: dict[str, tuple[str, ...]] = {
            "story_mode_probabilistic": (
                "[story mode] [design lens]",
                "",
                "Probabilistic UX thinking",
                "",
                "User request",
                "   ->",
                "Can Pathfinder identify intent?",
                "   ->",
                "Does it have enough context?",
                "   +-- No -> Ask 1 focused question",
                "   +-- Yes",
                "         ->",
                "Can it support a recommendation with evidence?",
                "   +-- No -> Show uncertainty + next best step",
                "   +-- Yes",
                "         ->",
                "Is the next action high risk?",
                "   +-- Yes -> Require approval",
                "   +-- No -> Continue",
                "",
                "Key idea",
                "Pathfinder should not pretend certainty.",
                "It should narrow the task, expose uncertainty, and pause before risky action.",
            ),
            "story_mode_behavior": (
                "[story mode] [design lens]",
                "",
                "Behavior spec",
                "",
                "What Pathfinder is",
                "   ->",
                "Security investigation assistant",
                "",
                "Who it is helping",
                "   ->",
                "SOC analyst / incident responder",
                "",
                "How it should speak",
                "   ->",
                "Concise, operational, evidence-first",
                "",
                "What it can do",
                "   ->",
                "Review detections",
                "Inspect identities",
                "Inspect endpoint context",
                "Recommend next steps",
                "Create tickets",
                "",
                "What it must not do",
                "   ->",
                "Pretend certainty",
                "Reveal restricted data",
                "Execute sensitive actions without approval",
                "",
                "How it should respond",
                "   ->",
                "Summary",
                "Why it matters",
                "Evidence",
                "Recommendation",
                "Approval needed: yes / no",
            ),
            "story_mode_memory": (
                "[story mode] [design lens]",
                "",
                "Memory design",
                "",
                "Turn memory",
                "   ->",
                "What was just said",
                "",
                "Session memory",
                "   ->",
                "Current incident",
                "Selected entities",
                "Time range",
                "Active filters",
                "",
                "User preference memory",
                "   ->",
                "Concise vs detailed output",
                "Preferred evidence style",
                "",
                "Org memory",
                "   ->",
                "Playbooks",
                "Escalation paths",
                "Naming conventions",
                "",
                "Never save by default",
                "   ->",
                "Secrets",
                "One-time tokens",
                "Privileged credentials",
                "Sensitive raw data",
            ),
            "story_mode_boundary": (
                "[story mode] [design lens]",
                "",
                "Boundary and control",
                "",
                "Model helps with",
                "   ->",
                "Summarization",
                "Prioritization",
                "Hypothesis generation",
                "Recommendation drafting",
                "",
                "Deterministic systems handle",
                "   ->",
                "Permission checks",
                "Policy checks",
                "Tool access",
                "Audit logging",
                "",
                "Human owns",
                "   ->",
                "Approval for sensitive remediation",
                "Final accountability",
                "Escalation decisions",
                "",
                "If blocked",
                "   ->",
                "Explain why",
                "Offer safe next steps",
                "Do not silently fail",
            ),
            "story_mode_structure": (
                "[story mode] [internal map]",
                "",
                "Full AI-native structure",
                "",
                "User intent",
                "   ->",
                "Intent classification",
                "   ->",
                "Context check",
                "   +-- Missing context -> Ask follow-up",
                "   +-- Enough context",
                "         ->",
                "Planner chooses steps + tools",
                "         ->",
                "Evidence gathering",
                "         ->",
                "Reasoning + summarization",
                "         ->",
                "Guardrails / policy / permission checks",
                "   +-- Blocked -> Refuse + explain",
                "   +-- Risky -> Pause for approval",
                "   +-- Safe",
                "         ->",
                "Action or recommendation",
                "         ->",
                "Audit log",
                "         ->",
                "Memory update by retention rules",
            ),
            "story_mode_summary": (
                "[story mode] [internal map]",
                "",
                "Demo story summary",
                "",
                "1. User starts with an ambiguous investigation request",
                "2. Pathfinder asks for missing scope",
                "3. User clarifies environment, timeframe, and goal",
                "4. Pathfinder investigates within role permissions",
                "5. Pathfinder explains what is known vs restricted",
                "6. User asks a follow-up without repeating context",
                "7. Pathfinder uses session memory",
                "8. Pathfinder recommends a BeyondTrust-native containment path but stops at approval",
                "9. Pathfinder prepares safe next steps",
            ),
        }
        body = self._build_story_mode_body_text(content.get(scene_key, ("[story mode]", "", "Unavailable", "", "Return to the story menu.",)))
        renderables: list[object] = []
        renderables.append(body)
        renderables.append(Text(""))
        renderables.append(Text("Return", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_story_followup_lines(scene_key))
        return renderables

    def _build_home_action_renderables(self, action_key: str) -> list[object]:
        scene_renderables = self._build_scene_renderables(action_key)
        if scene_renderables is not None:
            return scene_renderables
        if action_key == "true_privilege_graph":
            return self._build_identity_graph_renderables()
        if action_key.startswith("graph_focus:"):
            spotlight = self._graph_spotlight_for_key(action_key.split(":", maxsplit=1)[1])
            if spotlight is not None:
                return self._build_identity_graph_focus_renderables(spotlight)
        if action_key == "live_session_queue":
            return self._build_live_session_queue_renderables()
        if action_key == "pending_approvals":
            return self._build_pending_approvals_renderables()
        if action_key.startswith("approval_detail:"):
            approval = self._pending_approval_for_key(action_key.split(":", maxsplit=1)[1])
            if approval is not None:
                return self._build_pending_approval_detail_renderables(approval)
        return []

    def _build_portfolio_cover_renderables(self) -> list[object]:
        return [
            self._build_portfolio_cover_panel(),
            Align.center(self._build_portfolio_cover_caption_text()),
        ]

    def _build_portfolio_cover_panel(self) -> Panel:
        body = Group(
            Align.center(self._build_portfolio_cover_decor_line(primary=True)),
            Text(""),
            Align.center(self._build_portfolio_cover_timeline_text(top=True)),
            Text(""),
            Align.center(self._build_portfolio_cover_wordmark_text()),
            Text(""),
            Align.center(self._build_portfolio_cover_subtitle_text()),
            Text(""),
            Align.center(gradient_bar(0.94, width=28)),
            Text(""),
            Align.center(self._build_portfolio_cover_timeline_text(top=False)),
            Text(""),
            Align.center(self._build_portfolio_cover_decor_line(primary=False)),
        )
        return Panel(
            body,
            title="Pathfinder CLI cover",
            subtitle="terminal-native Pathfinder platform concept",
            box=TABLE_BOX,
            expand=True,
            border_style=PALETTE["line"],
            padding=(1, 2),
        )

    def _build_portfolio_cover_wordmark_text(self) -> Text:
        text = Text()
        for index, line in enumerate(PORTFOLIO_COVER_WORDMARK):
            style = f"bold {PALETTE['orange_primary']}"
            if index >= 5:
                style = f"bold {PALETTE['orange_soft']}"
            text.append(line, style=style)
            if index < len(PORTFOLIO_COVER_WORDMARK) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_portfolio_cover_subtitle_text(self) -> Text:
        text = Text()
        text.append("terminal-native Pathfinder platform concept", style=f"bold {PALETTE['text_main']}")
        text.append("\n", style=PALETTE["text_main"])
        text.append(
            "a CLI playground for trying Pathfinder dashboard ideas, UI flows, and feature interactions",
            style=PALETTE["text_muted"],
        )
        text.append("\n", style=PALETTE["text_main"])
        text.append(
            "built to explore how the platform can feel inside a focused investigation terminal",
            style=PALETTE["text_muted"],
        )
        return text

    def _build_portfolio_cover_timeline_text(self, *, top: bool) -> Text:
        text = Text()
        segments = (
            (". .", PALETTE["text_muted"]),
            (" /\\ ", PALETTE["teal"]),
            (" . . . ", PALETTE["text_muted"]),
            (" + ", PALETTE["orange_primary"]),
            (" . . ", PALETTE["text_muted"]),
            (" /\\ ", PALETTE["violet"] if top else PALETTE["orange_soft"]),
            (" . . . ", PALETTE["text_muted"]),
            (" + ", PALETTE["teal"] if top else PALETTE["orange_primary"]),
            (" . .", PALETTE["text_muted"]),
        )
        for segment, color in segments:
            text.append(segment, style=f"bold {color}" if segment.strip() in {"/\\", "+"} else color)
        text.append("  ", style=PALETTE["text_main"])
        text.append("Pathfinder signal path" if top else "CLI interaction path", style=f"bold {PALETTE['orange_soft']}")
        text.append("  ", style=PALETTE["text_main"])
        for segment, color in reversed(segments):
            text.append(segment, style=f"bold {color}" if segment.strip() in {"/\\", "+"} else color)
        return text

    def _build_portfolio_cover_decor_line(self, *, primary: bool) -> Text:
        text = Text()
        shapes = (
            (".", PALETTE["text_muted"]),
            ("+", PALETTE["orange_primary"]),
            ("/\\", PALETTE["teal"]),
            (".", PALETTE["text_muted"]),
            ("+", PALETTE["violet"]),
            ("/\\", PALETTE["orange_soft"]),
            (".", PALETTE["text_muted"]),
            ("+", PALETTE["teal"]),
            ("/\\", PALETTE["orange_primary"]),
            (".", PALETTE["text_muted"]),
            ("+", PALETTE["orange_soft"]),
            ("/\\", PALETTE["violet"]),
        )
        if not primary:
            shapes = tuple(reversed(shapes))
        for index, (shape, color) in enumerate(shapes):
            text.append(shape, style=f"bold {color}" if shape != "." else color)
            if index < len(shapes) - 1:
                text.append("   ", style=PALETTE["text_main"])
        return text

    def _build_portfolio_cover_caption_text(self) -> Text:
        text = Text()
        text.append("Pathfinder CLI concept scene", style=f"bold {PALETTE['orange_primary']}")
        text.append(" | ", style=PALETTE["line"])
        text.append("terminal UI playground for Pathfinder platform ideas", style=PALETTE["text_main"])
        text.append(" | ", style=PALETTE["line"])
        text.append("type /reset to return to the dashboard", style=PALETTE["text_muted"])
        return text

    def _build_temp_sunset_scene_renderables(self) -> list[object]:
        return [
            self._build_temp_sunset_scene_panel(),
            Align.center(self._build_temp_sunset_scene_caption_text()),
        ]

    def _build_temp_sunset_scene_panel(self) -> Panel:
        body = Group(
            Align.center(self._build_temp_sunset_scene_shape_band(top=True)),
            Text(""),
            Align.center(self._build_temp_sunset_scene_wordmark_group()),
            Text(""),
            Align.center(self._build_temp_sunset_scene_status_text()),
            Text(""),
            Align.center(gradient_bar(0.31, width=38)),
            Text(""),
            Align.center(self._build_temp_sunset_scene_step_text()),
            Text(""),
            Align.center(self._build_temp_sunset_scene_shape_band(top=False)),
        )
        return Panel(
            body,
            title="Temp Pathfinder loading scene",
            subtitle="BeyondTrust loading-screen study",
            box=TABLE_BOX,
            expand=True,
            border_style=PALETTE["line"],
            padding=(1, 2),
        )

    def _build_temp_sunset_scene_shape_band(self, *, top: bool) -> Text:
        text = Text()
        if top:
            segments = (
                ("[]", PALETTE["orange_soft"]),
                ("   ", PALETTE["text_main"]),
                ("<>", PALETTE["line"]),
                ("      ", PALETTE["text_main"]),
                ("/\\", PALETTE["orange_primary"]),
                ("    ", PALETTE["text_main"]),
                ("[]", PALETTE["yellow"]),
                ("      ", PALETTE["text_main"]),
                ("<>", PALETTE["orange_soft"]),
                ("    ", PALETTE["text_main"]),
                ("/\\", PALETTE["line"]),
                ("      ", PALETTE["text_main"]),
                ("[]", PALETTE["orange_primary"]),
            )
        else:
            segments = (
                ("/\\", PALETTE["line"]),
                ("__", PALETTE["orange_soft"]),
                ("   ", PALETTE["text_main"]),
                ("<>", PALETTE["orange_primary"]),
                ("      ", PALETTE["text_main"]),
                ("[]", PALETTE["yellow"]),
                ("    ", PALETTE["text_main"]),
                ("/\\", PALETTE["orange_soft"]),
                ("__", PALETTE["line"]),
                ("      ", PALETTE["text_main"]),
                ("<>", PALETTE["orange_primary"]),
                ("   ", PALETTE["text_main"]),
                ("[]", PALETTE["line"]),
            )
        for segment, color in segments:
            style = f"bold {color}" if segment.strip() else color
            text.append(segment, style=style)
        return text

    def _build_temp_sunset_scene_wordmark_group(self) -> Group:
        renderables: list[object] = []
        for index, word in enumerate(TEMP_SUNSET_SCENE_WORDMARK):
            for line in self._build_temp_sunset_scene_word_lines(word):
                renderables.append(line)
            if index < len(TEMP_SUNSET_SCENE_WORDMARK) - 1:
                renderables.append(Text(""))
        return Group(*renderables)

    def _build_temp_sunset_scene_word_lines(self, word: str) -> list[Text]:
        bitmap_rows = self._temp_sunset_scene_bitmap_rows(word)
        occupied = {
            (x, y)
            for y, row in enumerate(bitmap_rows)
            for x, cell in enumerate(row)
            if cell == "1"
        }
        outline = {
            (x, y)
            for x, y in occupied
            if any((x + dx, y + dy) not in occupied for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        }
        near_shadow = {(x + 1, y + 1) for x, y in outline}
        mid_shadow = {(x + 2, y + 2) for x, y in outline}

        width = max((len(row) for row in bitmap_rows), default=0) + 2
        height = len(bitmap_rows) + 2
        lines: list[Text] = []

        for y in range(height):
            line = Text()
            for x in range(width):
                if (x, y) in occupied:
                    color = PALETTE["orange_soft"] if y <= 2 else PALETTE["orange_primary"]
                    line.append("\u2588", style=f"bold {color}")
                elif (x, y) in near_shadow:
                    line.append("\u2593", style=f"bold {PALETTE['orange_soft']}")
                elif (x, y) in mid_shadow:
                    line.append("\u2592", style=f"bold {PALETTE['line']}")
                else:
                    line.append(" ", style=PALETTE["text_main"])
            lines.append(line)
        return lines

    def _temp_sunset_scene_bitmap_rows(self, word: str) -> tuple[str, ...]:
        font_height = len(next(iter(TEMP_SUNSET_SCENE_FONT.values())))
        rows = [""] * font_height
        gap_size = 2 if len(word) <= 3 else 1
        for index, character in enumerate(word):
            pattern = TEMP_SUNSET_SCENE_FONT[character]
            for row_index, segment in enumerate(pattern):
                rows[row_index] += segment
                if index < len(word) - 1:
                    rows[row_index] += "0" * gap_size
        return tuple(rows)

    def _build_temp_sunset_scene_status_text(self) -> Text:
        text = Text()
        text.append("\\", style=f"bold {PALETTE['orange_primary']}")
        text.append(" establishing trusted pathfinder cli session", style=f"bold {PALETTE['orange_primary']}")
        text.append("  ", style=PALETTE["text_main"])
        text.append(self.authenticated_user, style=PALETTE["text_main"])
        return text

    def _build_temp_sunset_scene_step_text(self) -> Text:
        text = Text()
        text.append("\\", style=f"bold {PALETTE['orange_primary']}")
        text.append(" step 2/5 ", style=f"bold {PALETTE['orange_primary']}")
        text.append("|", style=PALETTE["line"])
        text.append(" scene geometry and gradient pass in progress", style=f"bold {PALETTE['orange_primary']}")
        return text

    def _build_temp_sunset_scene_caption_text(self) -> Text:
        text = Text()
        text.append("PATHFINDER CLI loading concept", style=f"bold {PALETTE['orange_primary']}")
        text.append(" | ", style=PALETTE["line"])
        text.append("block wordmark with layered offsets, gradient bar, and geometric accents", style=PALETTE["text_main"])
        text.append(" | ", style=PALETTE["line"])
        text.append("type /reset to return to the dashboard", style=PALETTE["text_muted"])
        return text

    def _build_live_session_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_live_session_header_text())
        renderables.append(Text(""))
        renderables.append(self._build_live_session_status_text())
        renderables.append(Text(""))
        renderables.append(
            self._build_section_block("Session assessment", self._build_live_session_assessment_text())
        )
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Session details"))
        renderables.append(self._build_live_session_details_table())
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Why this matters", self._build_live_session_impact_text()))
        renderables.append(Text(""))
        renderables.append(
            self._build_section_block("Recommended next step", self._build_live_session_recommendation_text())
        )
        renderables.append(Text(""))
        renderables.append(Text("Investigate next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_live_session_followup_lines())
        return renderables

    def _build_live_session_header_text(self) -> Text:
        text = Text()
        text.append("Live session: ", style=PALETTE["text_muted"])
        text.append("pra-2214", style=f"bold {PALETTE['orange_soft']}")
        text.append("\n", style=PALETTE["text_main"])
        text.append("amy.miller", style=f"bold {PALETTE['text_main']}")
        text.append(" | ", style=PALETTE["line"])
        text.append("active privileged session", style=self._status_style("ok"))
        text.append(" | ", style=PALETTE["line"])
        text.append("aws-prod-admin", style=f"bold {PALETTE['orange_pale']}")
        return text

    def _build_live_session_status_text(self) -> Text:
        text = Text()
        text.append("[", style=PALETTE["line"])
        text.append("active", style=self._status_style("ok"))
        text.append("]", style=PALETTE["line"])
        text.append("   ", style=PALETTE["text_main"])
        text.append("opened 14m ago", style=PALETTE["text_main"])
        text.append("   ", style=PALETTE["text_main"])
        text.append("target: ", style=PALETTE["text_muted"])
        text.append("aws-prod-admin", style=f"bold {PALETTE['orange_pale']}")
        text.append("   ", style=PALETTE["text_main"])
        text.append("approval: ", style=PALETTE["text_muted"])
        text.append("not confirmed", style=self._status_style("risk"))
        return text

    def _build_live_session_assessment_text(self) -> Text:
        text = Text()
        text.append(
            "The session is still active and mapped to the same identity chain as the flagged sign-in.",
            style=PALETTE["text_main"],
        )
        text.append("\n", style=PALETTE["text_main"])
        text.append("No approved work record or attestation has been matched yet.", style=PALETTE["text_main"])
        return text

    def _build_live_session_details_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Field", style=PALETTE["text_muted"], no_wrap=True, min_width=16)
        table.add_column("Value", min_width=20)
        table.add_column("Signal", no_wrap=True, min_width=12)

        rows = (
            ("user", Text("amy.miller", style=f"bold {PALETTE['text_main']}"), self._build_badge("identity", "info")),
            ("session id", Text("pra-2214", style=f"bold {PALETTE['orange_soft']}"), self._build_badge("tracked", "accent")),
            ("status", Text("active", style=self._status_style("ok")), self._build_badge("live", "ok")),
            ("opened", Text("14m ago", style=PALETTE["text_main"]), self._build_badge("recent", "warn")),
            ("target", Text("aws-prod-admin", style=f"bold {PALETTE['orange_pale']}"), self._build_badge("admin", "accent")),
            ("source", Text("new device profile", style=PALETTE["text_main"]), self._build_badge("new", "info")),
            ("approval record", Text("not found", style=self._status_style("risk")), self._build_badge("critical", "risk")),
            ("attestation", Text("pending", style=self._status_style("warn")), self._build_badge("follow up", "warn")),
        )

        for field, value, signal in rows:
            table.add_row(field, value, signal)
        return table

    def _build_live_session_impact_text(self) -> Text:
        text = Text()
        text.append(
            "A live privileged session is still open on a production-linked admin target without confirmed business justification.",
            style=PALETTE["text_main"],
        )
        return text

    def _build_live_session_recommendation_text(self) -> Text:
        text = Text()
        text.append("Inspect target activity next. ", style=PALETTE["text_main"])
        text.append(
            "If the activity looks unjustified, request approval proof or revoke the session.",
            style=f"bold {PALETTE['text_main']}",
        )
        return text

    def _build_live_session_followup_lines(self) -> list[Text]:
        lines: list[Text] = []
        for index, action in enumerate(LIVE_SESSION_FOLLOWUP_ACTIONS):
            selected = (
                self.detail_navigation_active
                and self.detail_view_key == "live_session"
                and self.detail_action_index == index
            )
            line = Text()
            line.append(
                "> " if selected else "  ",
                style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["line"],
            )
            line.append(
                action.label,
                style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["text_main"],
            )
            if selected:
                line.stylize(f"on {PALETTE['bg_soft']}")
            lines.append(line)
        return lines

    def _build_target_activity_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_target_activity_header_text())
        renderables.append(Text(""))
        renderables.append(self._build_target_activity_status_text())
        renderables.append(Text(""))
        renderables.append(
            self._build_section_block("Activity assessment", self._build_target_activity_assessment_text())
        )
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Sensitivity", self._build_target_activity_sensitivity_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Recent activity"))
        renderables.append(self._build_emphasis_panel(self._build_target_activity_timeline_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Flagged actions", self._build_target_activity_flagged_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Why this matters", self._build_target_activity_impact_text()))
        renderables.append(Text(""))
        renderables.append(
            self._build_section_block("Recommended action", self._build_target_activity_recommendation_text())
        )
        renderables.append(Text(""))
        renderables.append(Text("Decide next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_target_activity_followup_lines())
        return renderables

    def _build_target_activity_header_text(self) -> Text:
        text = Text()
        text.append("Target activity: ", style=PALETTE["text_muted"])
        text.append("pra-2214", style=f"bold {PALETTE['orange_soft']}")
        text.append("\n", style=PALETTE["text_main"])
        text.append("amy.miller", style=f"bold {PALETTE['text_main']}")
        text.append(" | ", style=PALETTE["line"])
        text.append("aws-prod-admin", style=f"bold {PALETTE['orange_pale']}")
        text.append(" | ", style=PALETTE["line"])
        text.append("session active", style=self._status_style("ok"))
        return text

    def _build_target_activity_status_text(self) -> Text:
        text = Text()
        text.append("[", style=PALETTE["line"])
        text.append("warning", style=self._status_style("risk"))
        text.append("]", style=PALETTE["line"])
        text.append("   ", style=PALETTE["text_main"])
        text.append("privileged actions observed", style=PALETTE["text_main"])
        text.append("   ", style=PALETTE["text_main"])
        text.append("3 sensitive operations", style=f"bold {PALETTE['orange_pale']}")
        text.append("   ", style=PALETTE["text_main"])
        text.append("confidence: high", style=self._status_style("ok"))
        return text

    def _build_target_activity_assessment_text(self) -> Text:
        text = Text()
        text.append(
            "The session accessed production-linked admin scope and touched ",
            style=PALETTE["text_main"],
        )
        text.append("backup-related operations", style=f"bold {PALETTE['orange_pale']}")
        text.append(
            "\nwithin 6 minutes of opening. The behavior is elevated for this identity and is not yet tied\n"
            "to an approved task.",
            style=PALETTE["text_main"],
        )
        return text

    def _build_target_activity_sensitivity_text(self) -> Text:
        rows = (
            ("session risk", 8, "high"),
            ("target sensitivity", 10, "critical"),
            ("approval confidence", 3, "low"),
        )
        label_width = max(len(label) for label, _, _ in rows) + 1
        text = Text()
        for index, (label, filled, level) in enumerate(rows):
            self._append_target_activity_sensitivity_line(text, label, label_width, filled, level)
            if index < len(rows) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _append_target_activity_sensitivity_line(
        self,
        text: Text,
        label: str,
        label_width: int,
        filled: int,
        level: str,
    ) -> None:
        width = 10
        clamped_filled = max(0, min(width, filled))
        text.append(label.ljust(label_width), style=PALETTE["text_muted"])
        text.append("█" * clamped_filled, style=PALETTE["text_main"])
        text.append("░" * (width - clamped_filled), style=PALETTE["line"])
        text.append(" ", style=PALETTE["text_main"])
        text.append(level, style=self._target_activity_sensitivity_level_style(level))

    def _target_activity_sensitivity_level_style(self, level: str) -> str:
        return {
            "high": self._status_style("warn"),
            "critical": self._status_style("risk"),
            "low": self._status_style("risk"),
        }.get(level, PALETTE["text_main"])

    def _build_target_activity_timeline_text(self) -> Text:
        entries = (
            ("19:32", "●", "OPEN", "info", "session opened", PALETTE["text_main"]),
            ("19:34", "●", "SCOPE", "accent", "admin scope confirmed", PALETTE["text_main"]),
            ("19:36", "▲", "REVIEW", "warn", "backup policy viewed", self._status_style("warn")),
            ("19:37", "▲", "FLAG", "risk", "credential-related action attempted", self._status_style("risk")),
            ("19:38", "▲", "READ", "info", "production config read", f"bold {PALETTE['teal']}"),
        )
        text = Text()
        for index, (timestamp, glyph, marker, tone, label, style) in enumerate(entries):
            text.append(f"{timestamp}  ", style=PALETTE["text_muted"])
            text.append(glyph, style=style)
            text.append("  ", style=PALETTE["text_main"])
            text.append_text(self._build_badge(marker, tone))
            text.append("  ", style=PALETTE["text_main"])
            text.append(label, style=style)
            if index < len(entries) - 1:
                text.append("\n", style=PALETTE["text_main"])
                text.append("       |", style=PALETTE["line"])
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_target_activity_flagged_text(self) -> Text:
        text = Text()
        flagged_actions = (
            ("backup policy viewed", "shows privileged backup scope", self._status_style("warn")),
            ("credential-related action attempted", "strongest indicator for active misuse", self._status_style("risk")),
            ("production config accessed", "confirms production-linked reach", f"bold {PALETTE['orange_pale']}"),
        )
        for index, (label, detail, style) in enumerate(flagged_actions):
            text.append("⚑ ", style=style)
            text.append(label, style=style)
            text.append(" | ", style=PALETTE["line"])
            text.append(detail, style=PALETTE["text_muted"])
            if index < len(flagged_actions) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_target_activity_impact_text(self) -> Text:
        text = Text()
        text.append(
            "The session is active, privileged, and already interacting with sensitive production controls.",
            style=PALETTE["text_main"],
        )
        return text

    def _build_target_activity_recommendation_text(self) -> Text:
        text = Text()
        text.append(
            "Show the privilege path now to confirm the best containment break point before taking action.",
            style=f"bold {PALETTE['text_main']}",
        )
        return text

    def _build_target_activity_followup_lines(self) -> list[Text]:
        lines: list[Text] = []
        for index, action in enumerate(TARGET_ACTIVITY_FOLLOWUP_ACTIONS):
            selected = (
                self.detail_navigation_active
                and self.detail_view_key == "target_activity"
                and self.detail_action_index == index
            )
            line = Text()
            line.append(
                "> " if selected else "  ",
                style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["line"],
            )
            line.append(
                action.label,
                style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["text_main"],
            )
            if selected:
                line.stylize(f"on {PALETTE['bg_soft']}")
            lines.append(line)
        return lines

    def _build_privilege_path_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_privilege_path_header_text())
        renderables.append(Text(""))
        renderables.append(self._build_privilege_path_status_text())
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Focused path"))
        renderables.append(self._build_emphasis_panel(self._build_privilege_path_graph_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Path assessment", self._build_privilege_path_assessment_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Best break point", self._build_privilege_path_breakpoint_text()))
        renderables.append(Text(""))
        renderables.append(Text("Decide next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_privilege_path_followup_lines())
        return renderables

    def _build_privilege_path_header_text(self) -> Text:
        text = Text()
        text.append("Privilege path", style=f"bold {PALETTE['orange_soft']}")
        text.append("\n", style=PALETTE["text_main"])
        text.append("amy.miller", style=f"bold {PALETTE['text_main']}")
        text.append(" | ", style=PALETTE["line"])
        text.append("reachable admin chain", style=PALETTE["text_main"])
        text.append(" | ", style=PALETTE["line"])
        text.append("blast radius review", style=PALETTE["text_muted"])
        return text

    def _build_privilege_path_status_text(self) -> Text:
        text = Text()
        text.append("[", style=PALETTE["line"])
        text.append("critical", style=self._status_style("risk"))
        text.append("]", style=PALETTE["line"])
        text.append("   ", style=PALETTE["text_main"])
        text.append("path active", style=self._status_style("risk"))
        text.append("   ", style=PALETTE["text_main"])
        text.append("risky role: ", style=PALETTE["text_muted"])
        text.append("aws-prod-admin", style=self._status_style("risk"))
        text.append("   ", style=PALETTE["text_main"])
        text.append("session: ", style=PALETTE["text_muted"])
        text.append("pra-2214", style=f"bold {PALETTE['orange_soft']}")
        text.append(" ", style=PALETTE["text_main"])
        text.append("active", style=self._status_style("warn"))
        text.append("   ", style=PALETTE["text_main"])
        text.append("break point tagged", style=f"bold {PALETTE['orange_pale']}")
        return text

    def _append_privilege_path_connector(self, text: Text, prefix: str) -> None:
        text.append(prefix, style=PALETTE["line"])
        text.append("|\n", style=PALETTE["line"])

    def _append_privilege_path_line(
        self,
        text: Text,
        prefix: str,
        badge: str,
        badge_tone: str,
        label: str,
        label_style: str,
        *,
        suffix: str = "",
        suffix_style: str | None = None,
    ) -> None:
        text.append(prefix, style=PALETTE["line"])
        text.append_text(self._build_badge(badge, badge_tone))
        text.append(" ", style=PALETTE["text_main"])
        text.append(label, style=label_style)
        if suffix:
            text.append("  ", style=PALETTE["text_main"])
            text.append(suffix, style=suffix_style or PALETTE["text_muted"])
        text.append("\n", style=PALETTE["text_main"])

    def _build_privilege_path_graph_text(self) -> Text:
        text = Text()
        self._append_privilege_path_line(
            text,
            "",
            "ID",
            "info",
            "amy.miller",
            f"bold {PALETTE['text_main']}",
        )
        self._append_privilege_path_connector(text, "  ")
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "GROUP",
            "accent",
            "grp-cloud-admins",
            f"bold {PALETTE['orange_pale']}",
        )
        self._append_privilege_path_connector(text, "      ")
        self._append_privilege_path_line(
            text,
            "      +-- ",
            "BREAK",
            "warn",
            "cut inherited admin edge here",
            f"bold {PALETTE['text_main']}",
        )
        self._append_privilege_path_connector(text, "      ")
        self._append_privilege_path_line(
            text,
            "      +-- ",
            "ROLE",
            "risk",
            "aws-prod-admin",
            self._status_style("risk"),
            suffix="CRITICAL",
            suffix_style=f"bold {PALETTE['orange_pale']}",
        )
        self._append_privilege_path_line(
            text,
            "          +-- ",
            "OP",
            "accent",
            "production backup operations",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "          +-- ",
            "OP",
            "info",
            "production config read",
            f"bold {PALETTE['orange_pale']}",
        )
        self._append_privilege_path_line(
            text,
            "          +-- ",
            "LIVE",
            "ok",
            "pra-2214",
            f"bold {PALETTE['orange_soft']}",
            suffix="ACTIVE",
            suffix_style=self._status_style("warn"),
        )
        return text

    def _build_privilege_path_assessment_text(self) -> Text:
        text = Text()
        text.append(
            "The flagged identity still reaches AWS production admin through one inherited group-to-role\n"
            "edge. That edge is the cleanest break point, and the live PRA session shows the path is in use now.",
            style=PALETTE["text_main"],
        )
        return text

    def _build_privilege_path_breakpoint_text(self) -> Text:
        text = Text()
        text.append(
            "Simulate containment first. Then remove or suspend the inherited admin link before additional privileged actions occur.\n",
            style=PALETTE["text_main"],
        )
        text.append("recommended break point: ", style=PALETTE["text_muted"])
        text.append("grp-cloud-admins", style=f"bold {PALETTE['orange_pale']}")
        text.append(" -> ", style=PALETTE["line"])
        text.append("aws-prod-admin", style=self._status_style("risk"))
        text.append("  ", style=PALETTE["text_main"])
        text.append("[break here]\n", style=f"bold {PALETTE['orange_soft']}")
        text.append(
            "Cuts the inherited admin edge while leaving Amy's standard workforce identity intact.",
            style=PALETTE["text_muted"],
        )
        return text

    def _build_privilege_path_followup_lines(self) -> list[Text]:
        lines: list[Text] = []
        for index, action in enumerate(PRIVILEGE_PATH_FOLLOWUP_ACTIONS):
            selected = (
                self.detail_navigation_active
                and self.detail_view_key == "privilege_path"
                and self.detail_action_index == index
            )
            line = Text()
            line.append(
                "> " if selected else "  ",
                style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["line"],
            )
            line.append(
                action.label,
                style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["text_main"],
            )
            if selected:
                line.stylize(f"on {PALETTE['bg_soft']}")
            lines.append(line)
        return lines

    def _build_containment_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_containment_header_text())
        renderables.append(Text(""))
        renderables.append(self._build_containment_status_text())
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Containment options"))
        renderables.append(self._build_containment_matrix_table())
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Decision cues"))
        renderables.append(self._build_containment_assessment_table())
        renderables.append(Text(""))
        renderables.append(
            self._build_section_block("Recommended response", self._build_containment_recommendation_text())
        )
        renderables.append(Text(""))
        renderables.append(Text("Decide next", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_containment_followup_lines())
        return renderables

    def _build_containment_header_text(self) -> Text:
        text = Text()
        text.append("Containment simulation", style=f"bold {PALETTE['orange_soft']}")
        text.append("\n", style=PALETTE["text_main"])
        text.append("amy.miller", style=f"bold {PALETTE['text_main']}")
        text.append(" | ", style=PALETTE["line"])
        text.append("aws-prod-admin", style=f"bold {PALETTE['orange_pale']}")
        text.append(" | ", style=PALETTE["line"])
        text.append("response options compared", style=PALETTE["text_muted"])
        return text

    def _build_containment_status_text(self) -> Text:
        text = Text()
        text.append("[", style=PALETTE["line"])
        text.append("critical", style=self._status_style("risk"))
        text.append("]", style=PALETTE["line"])
        text.append("   ", style=PALETTE["text_main"])
        text.append("current risk 92", style=self._status_style("risk"))
        text.append("   ", style=PALETTE["text_main"])
        text.append("live session active", style=self._status_style("risk"))
        text.append("   ", style=PALETTE["text_main"])
        text.append("admin path reachable", style=f"bold {PALETTE['orange_pale']}")
        text.append("   ", style=PALETTE["text_main"])
        text.append("decision required", style=PALETTE["text_main"])
        return text

    def _build_containment_matrix_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Opt", no_wrap=True, min_width=5)
        table.add_column("Action", min_width=23)
        table.add_column("Risk", no_wrap=True, min_width=9)
        table.add_column("Session", no_wrap=True, min_width=11)
        table.add_column("Path", no_wrap=True, min_width=8)
        table.add_column("Impact", no_wrap=True, min_width=10)
        table.add_column("Review", no_wrap=True, min_width=8)

        rows = (
            ("A", "revoke session only", "92 -> 61", "closed", "remains", "medium", "YES"),
            ("B", "remove admin link only", "92 -> 38", "may persist", "broken", "low-med", "YES"),
            ("C", "do both", "92 -> 18", "closed", "broken", "med-high", "YES"),
        )
        for option, action, risk, session, path, impact, review in rows:
            action_style = f"bold {PALETTE['text_main']}" if option == "C" else PALETTE["text_main"]
            risk_style = {
                "A": self._status_style("risk"),
                "B": self._status_style("warn"),
                "C": self._status_style("ok"),
            }[option]
            impact_style = {
                "medium": PALETTE["orange_pale"],
                "low-med": PALETTE["yellow"],
                "med-high": self._status_style("warn"),
            }[impact]
            table.add_row(
                self._build_option_badge(option),
                Text(action, style=action_style),
                Text(risk, style=risk_style),
                Text(session, style=PALETTE["text_main"]),
                Text(path, style=self._status_style("risk") if path == "remains" else self._status_style("ok")),
                Text(impact, style=impact_style),
                self._build_badge(review, "warn"),
                style=f"on {PALETTE['bg_soft']}" if option == "C" else "",
            )
        return table

    def _build_containment_recommendation_text(self) -> Text:
        text = Text()
        text.append("Do both now. ", style=PALETTE["text_main"])
        text.append(
            "This is the fastest total reduction for a critical case with a live session, a reachable admin path, and no confirmed business approval.\n",
            style=f"bold {PALETTE['text_main']}",
        )
        text.append("Incident review should be staged in parallel because sensitive operations were already observed.", style=PALETTE["text_muted"])
        return text

    def _build_containment_followup_lines(self) -> list[Text]:
        lines: list[Text] = []
        for index, action in enumerate(CONTAINMENT_FOLLOWUP_ACTIONS):
            selected = (
                self.detail_navigation_active
                and self.detail_view_key == "containment"
                and self.detail_action_index == index
            )
            line = Text()
            line.append(
                "> " if selected else "  ",
                style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["line"],
            )
            line.append(
                self._detail_action_label(action),
                style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["text_main"],
            )
            if selected:
                line.stylize(f"on {PALETTE['bg_soft']}")
            lines.append(line)
        return lines

    def _build_containment_assessment_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Cue", style=PALETTE["text_main"], min_width=24)
        table.add_column("Option", no_wrap=True, min_width=9)
        table.add_column("Why", style=PALETTE["text_muted"], min_width=34)
        table.add_column("Signal", no_wrap=True, min_width=11)

        rows = (
            (
                "Fastest total reduction",
                self._build_option_badge("C"),
                "lowest residual risk and no active path left",
                self._build_badge("good", "ok"),
            ),
            (
                "Least disruption",
                self._build_option_badge("B"),
                "breaks future path while avoiding the broadest response",
                self._build_badge("balanced", "info"),
            ),
            (
                "Highest residual risk",
                self._build_option_badge("A"),
                "session closes but the admin path still remains",
                self._build_badge("critical", "risk"),
            ),
            (
                "Incident review",
                self._build_badge("ALL", "warn"),
                "recommended with any option because sensitive reads already occurred",
                self._build_badge("required", "accent"),
            ),
        )
        for cue, option, why, signal in rows:
            table.add_row(cue, option, why, signal)
        return table

    def _verification_outcome(self) -> VerificationOutcome:
        profile_key = self.verification_profile_key or "do_both_actions"
        if profile_key == "revoke_session":
            return VerificationOutcome(
                action_applied="revoke session",
                case_state="partially contained",
                status_level="warn",
                risk_after=61,
                residual_access="reachable path still exists through grp-cloud-admins",
                recommendation="Containment reduced the immediate session risk, but the admin path still remains. Remove the inherited admin link and open incident review.",
                checks=(
                    ("ok", "live PRA session pra-2214 closed"),
                    ("warn", "inherited admin link still present"),
                    ("warn", "aws-prod-admin still reachable from amy.miller"),
                    ("ok", "no active privileged session still observed"),
                    ("risk", "sensitive production reads occurred before containment"),
                    ("warn", "business approval remains unconfirmed"),
                ),
            )
        if profile_key == "remove_admin_link":
            return VerificationOutcome(
                action_applied="remove inherited admin link",
                case_state="partially contained",
                status_level="warn",
                risk_after=38,
                residual_access="current session may still retain active privileged reach",
                recommendation="The future path is broken, but the live session may still be active. Revoke the session next and open incident review.",
                checks=(
                    ("warn", "live PRA session may still be active"),
                    ("ok", "inherited link grp-cloud-admins -> aws-prod-admin removed"),
                    ("ok", "aws-prod-admin no longer reachable through the inherited path"),
                    ("warn", "active privileged access may persist until the session is revoked"),
                    ("risk", "sensitive production reads occurred before containment"),
                    ("warn", "business approval remains unconfirmed"),
                ),
            )
        return VerificationOutcome(
            action_applied="revoke session + remove inherited admin link",
            case_state="contained, follow-up required",
            status_level="ok",
            risk_after=18,
            residual_access="none direct to aws-prod-admin",
            recommendation="Containment is verified. Open incident review before final case closure.",
            checks=(
                ("ok", "live PRA session pra-2214 closed"),
                ("ok", "inherited link grp-cloud-admins -> aws-prod-admin removed"),
                ("ok", "aws-prod-admin no longer reachable from amy.miller"),
                ("ok", "no active privileged access still observed"),
                ("risk", "sensitive production reads occurred before containment"),
                ("warn", "business approval remains unconfirmed"),
            ),
        )

    def _build_verification_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(self._build_verification_header_text())
        renderables.append(Text(""))
        renderables.append(self._build_verification_status_text())
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Verification", self._build_verification_checks_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Residual", self._build_verification_residual_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Final recommendation", self._build_verification_recommendation_text()))
        renderables.append(Text(""))
        renderables.append(Text("Next actions", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_verification_followup_lines())
        return renderables

    def _build_verification_header_text(self) -> Text:
        outcome = self._verification_outcome()
        text = Text()
        text.append("Post-action verification", style=f"bold {PALETTE['orange_soft']}")
        text.append("\n", style=PALETTE["text_main"])
        text.append("amy.miller", style=f"bold {PALETTE['text_main']}")
        text.append(" | ", style=PALETTE["line"])
        text.append(outcome.action_applied, style=f"bold {PALETTE['orange_pale']}")
        text.append(" | ", style=PALETTE["line"])
        text.append("verification checkpoint", style=PALETTE["text_muted"])
        return text

    def _build_verification_status_text(self) -> Text:
        outcome = self._verification_outcome()
        risk_after_level = "ok" if outcome.risk_after <= 20 else "warn"
        text = Text()
        text.append("[", style=PALETTE["line"])
        text.append(outcome.case_state, style=self._status_style(outcome.status_level))
        text.append("]", style=PALETTE["line"])
        text.append("   ", style=PALETTE["text_main"])
        text.append(f"risk after {outcome.risk_after}", style=self._status_style(risk_after_level))
        text.append("   ", style=PALETTE["text_main"])
        text.append("action completed", style=PALETTE["text_main"])
        text.append("   ", style=PALETTE["text_main"])
        text.append("follow-up review recommended", style=f"bold {PALETTE['orange_pale']}")
        return text

    def _build_verification_checks_text(self) -> Text:
        outcome = self._verification_outcome()
        text = Text()
        for index, (level, label) in enumerate(outcome.checks):
            marker = "[ok]" if level == "ok" else "[!]"
            marker_style = self._status_style("ok") if level == "ok" else self._status_style("warn" if level == "warn" else "risk")
            text.append(marker, style=marker_style)
            text.append(" ", style=PALETTE["text_main"])
            text.append(label, style=PALETTE["text_main"])
            if index < len(outcome.checks) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_verification_residual_text(self) -> Text:
        outcome = self._verification_outcome()
        risk_after_level = "ok" if outcome.risk_after <= 20 else "warn"
        lines = (
            ("risk before", "92  critical", self._status_style("risk")),
            ("risk after", f"{outcome.risk_after}  {'low' if outcome.risk_after <= 20 else 'elevated'}", self._status_style(risk_after_level)),
            ("residual access", outcome.residual_access, PALETTE["text_main"]),
        )
        width = max(len(label) for label, _, _ in lines) + 2
        text = Text()
        for index, (label, value, style) in enumerate(lines):
            text.append(label.ljust(width), style=PALETTE["text_muted"])
            text.append(value, style=style)
            if index < len(lines) - 1:
                text.append("\n", style=PALETTE["text_main"])
        return text

    def _build_verification_recommendation_text(self) -> Text:
        outcome = self._verification_outcome()
        text = Text()
        text.append(outcome.recommendation, style=f"bold {PALETTE['text_main']}")
        return text

    def _build_verification_followup_lines(self) -> list[Text]:
        lines: list[Text] = []
        for index, action in enumerate(VERIFICATION_FOLLOWUP_ACTIONS):
            selected = (
                self.detail_navigation_active
                and self.detail_view_key == "verification"
                and self.detail_action_index == index
            )
            line = Text()
            line.append(
                "> " if selected else "  ",
                style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["line"],
            )
            line.append(
                self._detail_action_label(action),
                style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["text_main"],
            )
            if selected:
                line.stylize(f"on {PALETTE['bg_soft']}")
            lines.append(line)
        return lines

    def _build_live_session_queue_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(Text("Live session queue", style=f"bold {PALETTE['orange_soft']}"))
        renderables.append(Text(""))
        renderables.append(self._build_live_session_queue_status_text())
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Active sessions"))
        renderables.append(self._build_live_session_queue_table())
        renderables.append(Text(""))
        renderables.append(
            self._build_section_block("Recommended next step", self._build_live_session_queue_recommendation_text())
        )
        return renderables

    def _build_live_session_queue_status_text(self) -> Text:
        text = Text()
        text.append("⚠ ", style=self._status_style("risk"))
        text.append("1 session needs immediate review", style=self._status_style("risk"))
        text.append("   ", style=PALETTE["text_main"])
        text.append("4 total active", style=PALETTE["text_main"])
        text.append("   ", style=PALETTE["text_main"])
        text.append("oldest unverified: ", style=PALETTE["text_muted"])
        text.append("14m", style=f"bold {PALETTE['orange_pale']}")
        return text

    def _build_live_session_queue_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Session", no_wrap=True, min_width=10)
        table.add_column("Operator", min_width=16)
        table.add_column("Target", min_width=16)
        table.add_column("Waiting", no_wrap=True, min_width=8)
        table.add_column("Approval", no_wrap=True, min_width=12)
        table.add_column("Signal", min_width=14)

        signals = {
            "risk": ("→ review now", self._status_style("risk")),
            "warn": ("↗ follow up", self._status_style("warn")),
            "ok": ("✓ recorded", self._status_style("ok")),
        }
        for index, row in enumerate(LIVE_SESSION_QUEUE_ROWS):
            signal_label, signal_style = signals[row.tone]
            table.add_row(
                Text(row.session_id, style=f"bold {PALETTE['violet']}"),
                Text(row.operator, style=PALETTE["text_main"]),
                Text(row.target, style=f"bold {PALETTE['teal']}"),
                Text(row.waiting, style=PALETTE["text_main"]),
                self._build_badge(row.approval, row.tone),
                Text(signal_label, style=signal_style),
                style=f"on {PALETTE['bg_soft']}" if index == 0 else "",
            )
        return table

    def _build_live_session_queue_recommendation_text(self) -> Text:
        text = Text()
        text.append(
            "Open the highest-risk session first, verify the missing approval trail, and then work down the queue by waiting time.",
            style=PALETTE["text_main"],
        )
        return text

    def _build_pending_approvals_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(Text("Pending approvals", style=f"bold {PALETTE['orange_soft']}"))
        renderables.append(Text(""))
        renderables.append(self._build_pending_approvals_status_text())
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Approval queue"))
        renderables.append(self._build_pending_approvals_table())
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Selection", self._build_pending_approvals_selection_text()))
        return renderables

    def _build_pending_approvals_status_text(self) -> Text:
        password_safe_waiting = sum(
            1 for approval in self._all_pending_approvals()
            if approval.source == "Password Safe" and self._pending_approval_state(approval.key) == "waiting"
        )
        jit_waiting = sum(
            1 for approval in self._all_pending_approvals()
            if approval.source == "Entitle" and self._pending_approval_state(approval.key) == "waiting"
        )
        production_linked = sum(
            1 for approval in self._all_pending_approvals()
            if "prod" in approval.resource.lower() and self._pending_approval_state(approval.key) != "approved"
        )
        text = Text()
        text.append(f"{password_safe_waiting} Password Safe waiting", style=f"bold {PALETTE['violet']}")
        text.append("   ", style=PALETTE["text_main"])
        text.append(f"{jit_waiting} JIT approvals pending", style=f"bold {PALETTE['teal']}")
        text.append("   ", style=PALETTE["text_main"])
        text.append("production-linked: ", style=PALETTE["text_muted"])
        text.append(str(production_linked), style=self._status_style("warn"))
        return text

    def _build_pending_approvals_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Src", no_wrap=True, min_width=13)
        table.add_column("Request", min_width=22)
        table.add_column("Requester", min_width=14)
        table.add_column("Resource", min_width=18)
        table.add_column("Waiting", no_wrap=True, min_width=8)
        table.add_column("State", no_wrap=True, min_width=11)

        selected_index = self._pending_approval_selected_index()
        allow_highlight = self.detail_navigation_active and (
            self.detail_view_key == "pending_approvals"
            or (self.detail_view_key is not None and self.detail_view_key.startswith("approval_detail:"))
        )
        for index, approval in enumerate(self._all_pending_approvals()):
            table.add_row(
                Text(approval.source, style=f"bold {PALETTE['purple']}"),
                Text(approval.request, style=PALETTE["text_main"]),
                Text(approval.requester, style=PALETTE["text_main"]),
                Text(approval.resource, style=f"bold {PALETTE['teal']}"),
                Text(approval.waiting, style=PALETTE["text_main"]),
                self._pending_approval_state_badge(approval),
                style=f"on {PALETTE['bg_soft']}" if allow_highlight and index == selected_index else "",
            )
        return table

    def _build_pending_approvals_selection_text(self) -> Text:
        approvals = self._all_pending_approvals()
        approval = approvals[self._pending_approval_selected_index()]
        text = Text()
        text.append("Selected ", style=PALETTE["text_muted"])
        text.append("→ ", style=f"bold {PALETTE['teal']}")
        text.append(approval.request, style=f"bold {PALETTE['violet']}")
        text.append(" | ", style=PALETTE["line"])
        text.append(approval.requester, style=PALETTE["text_main"])
        text.append(" -> ", style=PALETTE["line"])
        text.append(approval.resource, style=f"bold {PALETTE['teal']}")
        text.append("\n", style=PALETTE["text_main"])
        text.append("Use Up/Down and Enter to inspect the request details before approving. ", style=PALETTE["text_main"])
        text.append(approval.note, style=PALETTE["text_muted"])
        return text

    def _build_pending_approval_detail_renderables(self, approval: PendingApproval) -> list[object]:
        renderables: list[object] = []
        renderables.append(Text("Approval detail", style=f"bold {PALETTE['orange_soft']}"))
        renderables.append(Text(""))
        renderables.append(self._build_pending_approval_detail_status_text(approval))
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Request details"))
        renderables.append(self._build_pending_approval_details_table(approval))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Decision context", self._build_pending_approval_context_text(approval)))
        renderables.append(Text(""))
        renderables.append(Text("Decision options", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_pending_approval_followup_lines())
        return renderables

    def _build_pending_approval_detail_status_text(self, approval: PendingApproval) -> Text:
        text = Text()
        text.append_text(self._pending_approval_state_badge(approval))
        text.append("   ", style=PALETTE["text_main"])
        text.append(approval.source, style=f"bold {PALETTE['purple']}")
        text.append(" -> ", style=PALETTE["line"])
        text.append(approval.resource, style=f"bold {PALETTE['teal']}")
        text.append("   ", style=PALETTE["text_main"])
        text.append("ticket: ", style=PALETTE["text_muted"])
        text.append(approval.ticket, style=f"bold {PALETTE['violet']}")
        text.append("   ", style=PALETTE["text_main"])
        text.append("window: ", style=PALETTE["text_muted"])
        text.append(approval.duration, style=PALETTE["text_main"])
        return text

    def _build_pending_approval_details_table(self, approval: PendingApproval) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Field", style=PALETTE["text_muted"], no_wrap=True, min_width=15)
        table.add_column("Value", min_width=24)
        table.add_column("Signal", no_wrap=True, min_width=12)

        rows = (
            ("request", Text(approval.request, style=f"bold {PALETTE['text_main']}"), self._build_badge("review", approval.tone)),
            ("requester", Text(approval.requester, style=PALETTE["text_main"]), self._build_badge("human", "info")),
            ("resource", Text(approval.resource, style=f"bold {PALETTE['teal']}"), self._build_badge("prod", "risk" if "prod" in approval.resource.lower() else "accent")),
            ("source", Text(approval.source, style=f"bold {PALETTE['purple']}"), self._build_badge("workflow", "accent")),
            ("approver", Text(approval.approver, style=PALETTE["text_main"]), self._build_badge("owner", "info")),
            ("ticket", Text(approval.ticket, style=f"bold {PALETTE['violet']}"), self._build_badge("linked", "violet")),
            ("waiting", Text(approval.waiting, style=PALETTE["text_main"]), self._build_badge("aging", "warn")),
            ("duration", Text(approval.duration, style=PALETTE["text_main"]), self._build_badge("jit", "teal")),
            ("scope", Text(approval.scope, style=PALETTE["text_main"]), self._build_badge("limited", "muted")),
        )
        for field, value, signal in rows:
            table.add_row(field, value, signal)
        return table

    def _build_pending_approval_context_text(self, approval: PendingApproval) -> Text:
        text = Text()
        text.append("Business case ", style=PALETTE["text_muted"])
        text.append("→ ", style=f"bold {PALETTE['teal']}")
        text.append(approval.business_case, style=PALETTE["text_main"])
        text.append("\n", style=PALETTE["text_main"])
        text.append("Approval note ", style=PALETTE["text_muted"])
        text.append("→ ", style=f"bold {PALETTE['purple']}")
        text.append(approval.note, style=PALETTE["text_muted"])
        return text

    def _build_pending_approval_followup_lines(self) -> list[Text]:
        lines: list[Text] = []
        for index, action in enumerate(PENDING_APPROVAL_DETAIL_ACTIONS):
            selected = (
                self.detail_navigation_active
                and self.detail_view_key is not None
                and self.detail_view_key.startswith("approval_detail:")
                and self.detail_action_index == index
            )
            line = Text()
            line.append(
                "> " if selected else "  ",
                style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["line"],
            )
            line.append(
                action.label,
                style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["text_main"],
            )
            if selected:
                line.stylize(f"on {PALETTE['bg_soft']}")
            lines.append(line)
        return lines

    def _investigation_header_signals(self, investigation_case: InvestigationCase) -> str:
        if investigation_case.key == "amy.miller":
            return "new geo sign-in | reachable admin path | active PRA session"
        return " | ".join(investigation_case.top_findings[:3])

    def _investigation_assessment_lines(self, investigation_case: InvestigationCase) -> tuple[str, str]:
        if investigation_case.key == "amy.miller":
            return (
                "The latest sign-in passed MFA, but from a new device profile and new geography.",
                "This identity still inherits a reachable path into AWS production admin, and one live privileged session remains tied to the same identity chain.",
            )
        return (
            investigation_case.alert_reason.capitalize() + ".",
            investigation_case.recommendation.capitalize() + ".",
        )

    def _investigation_blast_radius_level(self, investigation_case: InvestigationCase) -> str:
        if investigation_case.key == "amy.miller":
            return "high"
        if investigation_case.priority == "warning":
            return "medium"
        return "medium"

    def _investigation_session_state(self, investigation_case: InvestigationCase) -> str:
        if investigation_case.key == "amy.miller":
            return "active"
        if investigation_case.key == "privileged session":
            return "active"
        return "watch"

    def _investigation_check_lines(self, investigation_case: InvestigationCase) -> tuple[str, ...]:
        if investigation_case.key == "amy.miller":
            return (
                "okta sign-in correlated",
                "mfa and device profile reviewed",
                "live PRA session matched",
                "inheritance path verified",
            )
        return investigation_case.ai_checks

    def _build_response_table(self, prompt: str, module: ModuleSpec) -> Table:
        if self._matches_agent_status_request(prompt):
            return self._build_agent_status_table()

        table = Table(
            title="Priority Breakdown",
            box=TABLE_BOX,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
        )
        table.add_column("Control", style=PALETTE["text_main"])
        table.add_column("Score", justify="right", style=PALETTE["orange_pale"])
        table.add_column("Recommended Action", style=PALETTE["text_muted"])

        terms = self._keywords(prompt)
        for index, term in enumerate(terms, start=1):
            score = 52 + ((sum(ord(ch) for ch in term) + index * 11 + len(module.label)) % 45)
            action = "tighten policy" if score < 70 else "maintain and monitor"
            table.add_row(term.title(), f"{score}%", action)
        return table

    def _build_agent_status_table(self) -> Table:
        table = Table(
            title="Agent Status",
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
        )
        table.add_column("Agent", style=PALETTE["text_main"], min_width=18)
        table.add_column("Connector", min_width=14)
        table.add_column("Access", style=PALETTE["text_muted"], min_width=24)
        table.add_column("Role", style=PALETTE["orange_pale"], min_width=14)

        for row in self.agent_status_rows:
            connector = Text(row.connector, style=self._status_style(row.connector_level))
            table.add_row(
                row.agent,
                connector,
                row.access,
                row.role,
            )

        return table

    def _build_response_metrics(self, prompt: str, module: ModuleSpec) -> Table:
        seed = sum(ord(ch) for ch in f"{prompt}:{module.key}")
        metrics = (
            ("Posture Confidence", 55 + (seed % 40)),
            ("Policy Fidelity", 48 + ((seed // 5) % 45)),
            ("Operational Readiness", 52 + ((seed // 9) % 40)),
        )

        table = Table(
            title="Signal Metrics",
            box=TABLE_BOX,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
        )
        table.add_column("Signal", style=PALETTE["text_main"])
        table.add_column("Value", justify="right", style=PALETTE["orange_pale"])
        table.add_column("Bar", style=PALETTE["orange_primary"])

        for signal, value in metrics:
            table.add_row(signal, f"{value}%", self._bar(value, width=16))
        return table

    def _build_response(self, prompt: str, module: ModuleSpec) -> tuple[str, bool, bool]:
        lower_prompt = prompt.lower()
        wants_agent_status = self._matches_agent_status_request(prompt)
        show_table = wants_agent_status or any(token in lower_prompt for token in TABLE_TOKENS)
        show_metrics = (not wants_agent_status) and any(token in lower_prompt for token in METRIC_TOKENS)

        if wants_agent_status:
            summary = (
                "Agent status loaded across BeyondTrust capabilities and connected tools. "
                "Microsoft Entra ID is the only connector with a token nearing expiry."
            )
            return summary, show_table, show_metrics

        summary = f"{module.label}: {module.status} Priority focus: {module.insights[0]}"
        return summary, show_table, show_metrics

    async def _animate_processing(self, cycles: int = 14, delay: float = 0.05) -> None:
        for _ in range(cycles):
            await asyncio.sleep(delay)

    def _separator(self) -> str:
        width = self.query_one("#main-log", RichLog).size.width or self.size.width or 96
        usable_width = max(36, width - 4)
        return "-" * usable_width

    def _conversation_separator(self) -> str:
        width = self.query_one("#main-log", RichLog).size.width or self.size.width or 96
        usable_width = max(36, width - 4)
        return ("- " * ((usable_width + 1) // 2))[:usable_width]

    def _processing_spinner(self) -> str:
        return "|/-\\"[self.chrome_tick % 4]

    def _tick_ui(self) -> None:
        if self.processing:
            self._render_current_module()
            return
        self._refresh_chrome()

    def _status_style(self, level: str) -> str:
        return f"bold {self._status_color(level)}"

    def _status_color(self, level: str) -> str:
        return {
            "ok": PALETTE["ok"],
            "warn": PALETTE["warn"],
            "warning": PALETTE["warn"],
            "risk": PALETTE["risk"],
            "medium": PALETTE["orange_pale"],
            "info": PALETTE["blue_text"],
            "accent": PALETTE["purple_text"],
            "critical": PALETTE["risk"],
            "default": PALETTE["text_main"],
        }.get(level, PALETTE["text_main"])

    def _build_footer_hint(self) -> Text:
        scene_hint = self._scene_footer_hint()
        if scene_hint is not None:
            return scene_hint
        message = FOOTER_HELP_MESSAGES[(self.chrome_tick // 12) % len(FOOTER_HELP_MESSAGES)]
        spinner = FOOTER_SPINNER_FRAMES[self.chrome_tick % len(FOOTER_SPINNER_FRAMES)]
        text = Text()
        text.append("/help", style=f"bold {PALETTE['orange_primary']}")
        text.append("  ", style=PALETTE["text_main"])
        text.append(spinner, style=f"bold {PALETTE['orange_primary']}")
        text.append(" ", style=PALETTE["text_main"])
        text.append(message, style=PALETTE["text_muted"])
        return text

    def _estimated_token_usage(self) -> int:
        estimated = BASE_SESSION_TOKEN_ESTIMATE
        for history in self.histories.values():
            for entry in history:
                estimated += max(1, math.ceil(len(entry.text) / 4))
                if entry.source_prompt:
                    estimated += max(1, math.ceil(len(entry.source_prompt) / 4))
                if entry.context_key:
                    estimated += max(1, math.ceil(len(entry.context_key) / 6))
                if entry.action_key:
                    estimated += max(1, math.ceil(len(entry.action_key) / 6))

        if self.detail_view_key:
            estimated += max(12, math.ceil(len(self.detail_view_key) / 2))
        if self.investigation_case_key:
            estimated += max(12, math.ceil(len(self.investigation_case_key) / 2))
        if self.processing:
            estimated += 96
        if any(
            (
                self.module_picker_active,
                self.home_navigation_active,
                self.investigation_navigation_active,
                self.detail_navigation_active,
            )
        ):
            estimated += 48
        return min(estimated, TOKEN_BUDGET)

    def _format_token_count(self, count: int) -> str:
        if count >= 1000:
            value = f"{count / 1000:.1f}".rstrip("0").rstrip(".")
            return f"{value}k"
        return str(count)

    def _build_top_meta(self) -> Text:
        tokens_used = self._format_token_count(self._estimated_token_usage())
        token_budget = self._format_token_count(TOKEN_BUDGET)

        text = Text()
        text.append(MODEL_PROVIDER_LABEL, style=f"bold {PALETTE['ok']}")
        text.append(" | ", style=PALETTE["line"])
        text.append(MODEL_NAME_LABEL, style=f"bold {PALETTE['orange_soft']}")
        text.append(" | ", style=PALETTE["line"])
        text.append("Tokens ", style=PALETTE["text_muted"])
        text.append(f"~{tokens_used}", style=f"bold {PALETTE['text_main']}")
        text.append("/", style=PALETTE["line"])
        text.append(token_budget, style=f"bold {PALETTE['text_main']}")
        return text

    def _mark_updated(self) -> None:
        self.last_update_at = time.perf_counter()

    def _home_selection_count(self) -> int:
        return len(ATTENTION_ITEMS) + len(HOME_ACTIONS)

    def _selected_attention_index(self) -> int | None:
        if not self.home_navigation_active or self.home_selection_index >= len(ATTENTION_ITEMS):
            return None
        return self.home_selection_index

    def _selected_action_index(self) -> int | None:
        if not self.home_navigation_active or self.home_selection_index < len(ATTENTION_ITEMS):
            return None
        return self.home_selection_index - len(ATTENTION_ITEMS)

    def _is_attention_selected(self, index: int) -> bool:
        return self._selected_attention_index() == index

    def _is_action_selected(self, index: int) -> bool:
        return self._selected_action_index() == index

    def _plain_text(self, value: str, style: str | None = None) -> Text:
        return Text(value, style=style or PALETTE["text_main"])

    def _refresh_chrome(self) -> None:
        self.chrome_tick += 1
        try:
            title = Text()
            title.append("Pathfinder", style=f"bold {PALETTE['orange_primary']}")
            title.append(" > ", style=f"bold {PALETTE['orange_primary']}")
            if self.module_picker_active:
                title_label = "Apps"
            else:
                title_label = self._scene_chrome_label() or "Overview"
            title.append(title_label, style=f"bold {PALETTE['orange_soft']}")
            self.query_one("#top-title", Static).update(title)

            self.query_one("#top-meta", Static).update(self._build_top_meta())

            typing = Text()
            spinner = self._processing_spinner() if self.processing else (">" if self.chrome_tick % 2 else "|")
            typing.append(spinner, style=f"bold {PALETTE['orange_primary']}")
            if self.processing:
                typing.append(" ", style=PALETTE["text_main"])
                typing.append(self.processing_message or "Thinking...", style=f"bold {PALETTE['text_main']}")
            self.query_one("#typing-indicator", Static).update(typing)

            self.query_one("#command-hint", Static).update(self._build_footer_hint())

            session = Text()
            session.append("Logged as: ", style=PALETTE["text_muted"])
            session.append(self.authenticated_user, style=f"bold {PALETTE['orange_primary']}")
            session.append(" | ", style=PALETTE["line"])
            session.append(self.user_role, style=PALETTE["text_main"])
            self.query_one("#session-status", Static).update(session)
        except NoMatches:
            return

    def _select_picker_module(self) -> None:
        selected_module = self._picker_module_at_current_index()
        for index, module in enumerate(MODULES):
            if module.key == selected_module.key:
                self._set_active_module_index(index)
                break
        self._mark_updated()
        self._render_current_module()
        self.query_one("#command-input", Input).focus()

    def action_activate_selection(self) -> None:
        if self.processing:
            return

        selection = self._selection_activation()
        if selection is None:
            return

        processing_message, callback = selection
        self.run_worker(
            self._perform_selection_action(processing_message, callback),
            exclusive=True,
            thread=False,
        )

    def _selection_activation(self) -> tuple[str, Callable[[], None]] | None:
        if self.module_picker_active:
            selected_module = self._picker_module_at_current_index()
            return f"Switching to {selected_module.label}...", self._select_picker_module

        if self.detail_navigation_active:
            selected_action = self._selected_detail_action()
            if selected_action is None:
                return None
            return self._detail_action_processing_message(selected_action), self._open_selected_detail_action

        if self.investigation_navigation_active:
            selected_action = self._selected_investigation_action()
            if selected_action is None:
                return None
            return self._investigation_action_processing_message(selected_action), self._open_selected_investigation_action

        if not self.home_navigation_active:
            return None

        attention_index = self._selected_attention_index()
        if attention_index is not None:
            attention = ATTENTION_ITEMS[attention_index]
            return f"Reviewing {attention.subject}...", lambda: self._open_selected_attention(attention_index)

        action_index = self._selected_action_index()
        if action_index is not None:
            action = HOME_ACTIONS[action_index]
            return self._home_action_processing_message(action), lambda: self._open_selected_action(action_index)

        return None

    async def _perform_selection_action(self, processing_message: str, callback: Callable[[], None]) -> None:
        command_input = self.query_one("#command-input", Input)
        command_input.disabled = True
        self.processing = True
        self.processing_message = processing_message
        self._render_current_module()

        try:
            await self._animate_processing(cycles=12, delay=0.06)
            callback()
        finally:
            self.processing = False
            self.processing_message = ""
            command_input.disabled = False
            command_input.focus()
            self._render_current_module()

    def _home_action_processing_message(self, action: HomeAction) -> str:
        if action.key == "true_privilege_graph":
            return "Loading graph catalog..."
        if action.key == "live_session_queue":
            return "Reviewing live session queue..."
        if action.key == "pending_approvals":
            return "Collecting approval backlog..."
        if action.key == "portfolio_cover":
            return "Preparing portfolio cover..."
        if action.key == "temp_sunset_scene":
            return "Loading temp splash scene..."
        return "Thinking..."

    def _investigation_action_processing_message(self, action: InvestigationAction) -> str:
        if action.key == "view_live_session":
            return "Compiling live session context..."
        if action.key == "show_privilege_path":
            return "Reviewing privilege path..."
        if action.key == "review_signin_timeline":
            return "Replaying sign-in timeline..."
        if action.key == "compare_role_changes":
            return "Comparing recent role changes..."
        if action.key == "simulate_containment":
            return "Comparing containment options..."
        if action.key == "return_to_queue":
            return "Returning to queue..."
        return "Thinking..."

    def _detail_action_processing_message(self, action: InvestigationAction) -> str:
        if action.key.startswith("story_mode_"):
            if action.key == "story_mode_return":
                return "Returning to story menu..."
            return "Opening story poster..."
        if action.key == "story_scope_default_recommend":
            return "Resolving investigation scope..."
        if action.key == "story_scope_default_triage":
            return "Resolving investigation scope..."
        if action.key == "story_customize_scope":
            return "Preparing scope customization..."
        if action.key == "story_show_role_limits":
            return "Reviewing role limits..."
        if action.key == "story_run_investigation":
            return "Running investigation..."
        if action.key == "story_show_memory_state":
            return "Loading session memory..."
        if action.key in {"story_assess_session_relatedness", "story_show_privilege_path"}:
            return "Reviewing correlated access signals..."
        if action.key in {"story_show_approval_evidence", "story_request_approval_proof"}:
            return "Comparing approval evidence..."
        if action.key in {"story_list_affected_assets", "story_show_top_asset_detail"}:
            return "Reviewing affected assets..."
        if action.key == "story_compare_access_change_options":
            return "Comparing containment options..."
        if action.key in {
            "story_prepare_session_revoke_request",
            "story_prepare_path_suspension_request",
            "story_prepare_combined_response_packet",
        }:
            return "Preparing approval-ready response..."
        if action.key in {"story_stage_incident_review", "story_open_incident_review"}:
            return "Opening incident review..."
        if action.key == "story_open_approval_queue":
            return "Opening approval queue..."
        if action.key == "story_export_summary":
            return "Preparing summary export..."
        if action.key in {"story_review_prepared_request", "story_hold_prepared_request"}:
            return "Reviewing staged approval..."
        if action.key in {"story_return_home", "story_return_home_keep_memory"}:
            return "Returning home..."
        if action.key.startswith("story_return_"):
            return "Returning to the previous story step..."
        if action.key.startswith("select_graph:"):
            return "Opening selected graph..."
        if action.key == "return_to_graph_catalog":
            return "Returning to graph catalog..."
        if action.key.startswith("approval_detail:"):
            return "Loading approval details..."
        if action.key == "revoke_session":
            return "Preparing session revoke..."
        if action.key == "revoke_session_now":
            return "Applying session revoke..."
        if action.key == "open_incident_review":
            return "Opening incident review..."
        if action.key == "request_approval_proof":
            return "Requesting approval evidence..."
        if action.key == "inspect_target_activity":
            return "Inspecting target activity..."
        if action.key == "compare_recent_role_changes":
            return "Comparing recent role changes..."
        if action.key == "show_privilege_path":
            return "Reviewing privilege path..."
        if action.key == "simulate_containment":
            return "Comparing containment options..."
        if action.key == "remove_inherited_admin_link":
            return "Applying admin link removal..."
        if action.key == "remove_admin_link":
            return "Applying admin link removal..."
        if action.key == "do_both_actions":
            return "Applying combined containment..."
        if action.key == "stage_incident_review":
            return "Staging incident review..."
        if action.key == "export_investigation_summary":
            return "Exporting investigation summary..."
        if action.key == "return_to_queue":
            return "Returning to queue..."
        if action.key == "close_case_as_contained":
            return "Closing contained case..."
        if action.key == "approve_pending_request":
            return "Approving request..."
        if action.key == "hold_pending_request":
            return "Holding request..."
        if action.key == "return_to_pending_approvals":
            return "Returning to approval queue..."
        if action.key == "return_to_case_summary":
            return "Returning to case summary..."
        if action.key == "return_to_session_summary":
            return "Returning to session summary..."
        if action.key == "return_to_activity_review":
            return "Returning to activity review..."
        if action.key == "cancel_return":
            return "Returning to previous step..."
        return "Thinking..."

    def _detail_action_index_for(self, detail_view_key: str, action_key: str) -> int:
        if detail_view_key == "live_session":
            actions = LIVE_SESSION_FOLLOWUP_ACTIONS
        elif detail_view_key == "target_activity":
            actions = TARGET_ACTIVITY_FOLLOWUP_ACTIONS
        elif detail_view_key == "containment":
            actions = CONTAINMENT_FOLLOWUP_ACTIONS
        elif detail_view_key == "verification":
            actions = VERIFICATION_FOLLOWUP_ACTIONS
        else:
            actions = PRIVILEGE_PATH_FOLLOWUP_ACTIONS
        for index, action in enumerate(actions):
            if action.key == action_key:
                return index
        return 0

    def _open_selected_home_item(self) -> None:
        attention_index = self._selected_attention_index()
        if attention_index is not None:
            self._open_selected_attention(attention_index)
            return

        action_index = self._selected_action_index()
        if action_index is not None:
            self._open_selected_action(action_index)

    def _open_selected_investigation_action(self) -> None:
        active_case = self._active_investigation_case()
        selected_action = self._selected_investigation_action()
        if active_case is None or selected_action is None:
            self._clear_investigation_state(self._active_module().key)
            return

        current_module = self._active_module()
        if selected_action.key == "view_live_session":
            self.detail_navigation_active = True
            self.detail_view_key = "live_session"
            self.detail_action_index = 0
            self.detail_return_view_key = None
            self._set_verification_profile(current_module.key, None)
            self._remember_detail_state(current_module.key)
        elif selected_action.key == "show_privilege_path":
            self.detail_navigation_active = True
            self.detail_view_key = "privilege_path"
            self.detail_action_index = 0
            self.detail_return_view_key = None
            self._set_verification_profile(current_module.key, None)
            self._remember_detail_state(current_module.key)
        elif selected_action.key == "simulate_containment":
            self.detail_navigation_active = True
            self.detail_view_key = "containment"
            self.detail_action_index = 0
            self.detail_return_view_key = "summary"
            self._set_verification_profile(current_module.key, None)
            self._remember_detail_state(current_module.key)
        elif selected_action.key == "return_to_queue":
            self._clear_detail_state(current_module.key)
            self.investigation_state_by_module[current_module.key] = None
            self.investigation_navigation_active = False
            self.investigation_case_key = None
            self.investigation_action_index = 0
            self.home_navigation_active = True
            self.home_selection_index = 0
        else:
            self._clear_detail_state(current_module.key)
        self._append_history(
            current_module.key,
            ConversationEntry(
                role="assistant",
                text=selected_action.result,
                kind="investigation_action",
                context_key=active_case.key,
                action_key=selected_action.key,
            ),
        )
        self._mark_updated()
        self._render_current_module()
        self.query_one("#command-input", Input).focus()

    def _open_selected_detail_action(self) -> None:
        selected_action = self._selected_detail_action()
        if selected_action is None:
            self._clear_detail_state(self._active_module().key)
            return

        current_module = self._active_module()
        if self._story_mode_active() or self._story_scene_active():
            if self._handle_story_detail_action(current_module.key, selected_action):
                self._mark_updated()
                self._render_current_module()
                self.query_one("#command-input", Input).focus()
                return

        entry_kind = "investigation_action"
        entry_action_key = selected_action.key
        entry_text = selected_action.result
        current_graph_spotlight = self._current_graph_spotlight()
        current_pending_approval = self._current_pending_approval()

        if self.detail_view_key == "true_privilege_graph" and selected_action.key.startswith("select_graph:"):
            graph_key = selected_action.key.split(":", maxsplit=1)[1]
            spotlight = self._graph_spotlight_for_key(graph_key)
            if spotlight is None:
                self._remember_detail_state(current_module.key)
            else:
                self.detail_navigation_active = True
                self.detail_view_key = f"graph_focus:{graph_key}"
                self.detail_action_index = 0
                self.detail_return_view_key = "true_privilege_graph"
                self._set_verification_profile(current_module.key, None)
                self._remember_detail_state(current_module.key)
                entry_kind = "home_action"
                entry_action_key = self.detail_view_key
                entry_text = f"Opened graph for {spotlight.label}."
        elif (
            self.detail_view_key
            and self.detail_view_key.startswith("graph_focus:")
            and selected_action.key == "return_to_graph_catalog"
        ):
            self.detail_navigation_active = True
            self.detail_view_key = "true_privilege_graph"
            self.detail_action_index = (
                self._graph_catalog_index_for_key(current_graph_spotlight.key)
                if current_graph_spotlight is not None
                else 0
            )
            self.detail_return_view_key = None
            self._set_verification_profile(current_module.key, None)
            self._remember_detail_state(current_module.key)
            entry_kind = "home_action"
            entry_action_key = "true_privilege_graph"
            entry_text = "Returned focus to the graph catalog."
        elif self.detail_view_key == "pending_approvals" and selected_action.key.startswith("approval_detail:"):
            self.detail_navigation_active = True
            self.detail_view_key = selected_action.key
            self.detail_action_index = 0
            self.detail_return_view_key = "pending_approvals"
            self._set_verification_profile(current_module.key, None)
            self._remember_detail_state(current_module.key)
            entry_kind = "home_action"
        elif (
            self.detail_view_key
            and self.detail_view_key.startswith("approval_detail:")
            and current_pending_approval is not None
            and selected_action.key in {"approve_pending_request", "hold_pending_request", "return_to_pending_approvals"}
        ):
            return_to_story_queue = self.detail_return_view_key == "story_approval_queue"
            if selected_action.key == "approve_pending_request":
                self.pending_approval_state_by_key[current_pending_approval.key] = "approved"
                entry_text = (
                    f"Approved {current_pending_approval.request} for {current_pending_approval.requester}. "
                    f"Ticket {current_pending_approval.ticket} can move forward."
                )
            elif selected_action.key == "hold_pending_request":
                self.pending_approval_state_by_key[current_pending_approval.key] = "on_hold"
                entry_text = (
                    f"Held {current_pending_approval.request} and requested more context from "
                    f"{current_pending_approval.requester}."
                )
            else:
                entry_text = "Returned focus to the pending approvals queue."

            self.detail_navigation_active = True
            self.detail_view_key = "story_approval_queue" if return_to_story_queue else "pending_approvals"
            self.detail_action_index = 0 if return_to_story_queue else self._pending_approval_index(current_pending_approval.key)
            self.detail_return_view_key = None
            self._set_verification_profile(current_module.key, None)
            self._remember_detail_state(current_module.key)
            entry_kind = "story_scene" if return_to_story_queue else "message"
            entry_action_key = "story_approval_queue" if return_to_story_queue else ""
        else:
            verification_profile = self._verification_profile_for_action(selected_action.key)
            if verification_profile is not None:
                self.detail_navigation_active = True
                self.detail_view_key = "verification"
                self.detail_action_index = 0
                self.detail_return_view_key = None
                self._set_verification_profile(current_module.key, verification_profile)
                self._remember_detail_state(current_module.key)
                entry_action_key = "post_action_verification"
            elif self.detail_view_key == "live_session" and selected_action.key == "inspect_target_activity":
                self.detail_navigation_active = True
                self.detail_view_key = "target_activity"
                self.detail_action_index = 0
                self.detail_return_view_key = None
                self._set_verification_profile(current_module.key, None)
                self._remember_detail_state(current_module.key)
            elif self.detail_view_key == "live_session" and selected_action.key == "show_privilege_path":
                self.detail_navigation_active = True
                self.detail_view_key = "privilege_path"
                self.detail_action_index = 0
                self.detail_return_view_key = None
                self._set_verification_profile(current_module.key, None)
                self._remember_detail_state(current_module.key)
            elif self.detail_view_key == "live_session" and selected_action.key == "return_to_case_summary":
                self._clear_detail_state(current_module.key)
                self.investigation_navigation_active = True
                self.investigation_action_index = 0
                entry_kind = "investigation"
                entry_action_key = ""
                entry_text = "Investigation opened for amy.miller."
            elif self.detail_view_key == "target_activity" and selected_action.key == "show_privilege_path":
                self.detail_navigation_active = True
                self.detail_view_key = "privilege_path"
                self.detail_action_index = 0
                self.detail_return_view_key = None
                self._set_verification_profile(current_module.key, None)
                self._remember_detail_state(current_module.key)
            elif self.detail_view_key == "target_activity" and selected_action.key == "simulate_containment":
                self.detail_navigation_active = True
                self.detail_view_key = "containment"
                self.detail_action_index = 0
                self.detail_return_view_key = "target_activity"
                self._set_verification_profile(current_module.key, None)
                self._remember_detail_state(current_module.key)
            elif self.detail_view_key == "target_activity" and selected_action.key == "return_to_session_summary":
                self.detail_navigation_active = True
                self.detail_view_key = "live_session"
                self.detail_action_index = 0
                self.detail_return_view_key = None
                self._set_verification_profile(current_module.key, None)
                self._remember_detail_state(current_module.key)
                entry_action_key = "view_live_session"
                entry_text = "Live session summary reloaded for pra-2214."
            elif self.detail_view_key == "privilege_path" and selected_action.key == "simulate_containment":
                self.detail_navigation_active = True
                self.detail_view_key = "containment"
                self.detail_action_index = 0
                self.detail_return_view_key = "privilege_path"
                self._set_verification_profile(current_module.key, None)
                self._remember_detail_state(current_module.key)
            elif self.detail_view_key == "privilege_path" and selected_action.key == "return_to_activity_review":
                self.detail_navigation_active = True
                self.detail_view_key = "target_activity"
                self.detail_action_index = 0
                self.detail_return_view_key = None
                self._set_verification_profile(current_module.key, None)
                self._remember_detail_state(current_module.key)
                entry_action_key = "inspect_target_activity"
                entry_text = "Target activity review reloaded for pra-2214."
            elif self.detail_view_key == "containment" and selected_action.key == "cancel_return":
                return_view_key = self.detail_return_view_key
                self._set_verification_profile(current_module.key, None)
                if return_view_key == "summary":
                    self._clear_detail_state(current_module.key)
                    self.investigation_navigation_active = True
                    self.investigation_action_index = 0
                    entry_kind = "investigation"
                    entry_action_key = ""
                    entry_text = "Investigation opened for amy.miller."
                elif return_view_key in {"live_session", "target_activity", "privilege_path"}:
                    self.detail_navigation_active = True
                    self.detail_view_key = return_view_key
                    self.detail_action_index = 0
                    self.detail_return_view_key = None
                    self._remember_detail_state(current_module.key)
                    entry_action_key = {
                        "live_session": "view_live_session",
                        "target_activity": "inspect_target_activity",
                        "privilege_path": "show_privilege_path",
                    }[return_view_key]
                    entry_text = {
                        "live_session": "Live session summary reloaded for pra-2214.",
                        "target_activity": "Target activity review reloaded for pra-2214.",
                        "privilege_path": "Privilege path review reloaded for amy.miller.",
                    }[return_view_key]
                else:
                    self._clear_detail_state(current_module.key)
            elif self.detail_view_key == "verification":
                self._clear_detail_state(current_module.key)
                self.investigation_state_by_module[current_module.key] = None
                self.investigation_navigation_active = False
                self.investigation_case_key = None
                self.investigation_action_index = 0
                self.home_navigation_active = True
                self.home_selection_index = 0
                entry_kind = "message"
                entry_action_key = ""
            else:
                self._remember_detail_state(current_module.key)

        self._append_history(
            current_module.key,
            ConversationEntry(
                role="assistant",
                text=entry_text,
                kind=entry_kind,
                context_key=self.investigation_case_key or "",
                action_key=entry_action_key,
            ),
        )
        self._mark_updated()
        self._render_current_module()
        self.query_one("#command-input", Input).focus()

    def _open_selected_attention(self, attention_index: int) -> None:
        attention = ATTENTION_ITEMS[attention_index]
        current_module = self._active_module()
        self.home_navigation_active = False
        self.module_picker_active = False
        self._clear_detail_state(current_module.key)
        investigation_case = self._investigation_case_for_attention(attention)
        if investigation_case is not None:
            self.investigation_navigation_active = True
            self.investigation_case_key = investigation_case.key
            self.investigation_action_index = 0
            self._remember_investigation_state(current_module.key)
            self._append_history(
                current_module.key,
                ConversationEntry(
                    role="assistant",
                    text=f"Investigation opened for {investigation_case.identity}.",
                    source_prompt=attention.subject,
                    kind="investigation",
                    context_key=investigation_case.key,
                ),
            )
        else:
            self._clear_investigation_state(current_module.key)
            self._append_history(
                current_module.key,
                ConversationEntry(
                    role="assistant",
                    text=self._build_attention_response(attention).plain,
                    source_prompt=attention.subject,
                ),
            )
        self._mark_updated()
        self._render_current_module()
        self.query_one("#command-input", Input).focus()

    def _open_selected_action(self, action_index: int) -> None:
        action = HOME_ACTIONS[action_index]
        current_module = self._active_module()
        self.home_navigation_active = False
        self.module_picker_active = False
        self._clear_investigation_state(current_module.key)
        if action.key == "true_privilege_graph":
            self.detail_navigation_active = True
            self.detail_view_key = "true_privilege_graph"
            self.detail_action_index = 0
            self.detail_return_view_key = None
            self._remember_detail_state(current_module.key)
        elif action.key == "pending_approvals":
            self.detail_navigation_active = True
            self.detail_view_key = "pending_approvals"
            self.detail_action_index = 0
            self.detail_return_view_key = None
            self._remember_detail_state(current_module.key)
        elif action.key == "portfolio_cover":
            self.detail_navigation_active = False
            self.detail_view_key = "portfolio_cover"
            self.detail_action_index = 0
            self.detail_return_view_key = None
        elif action.key == "temp_sunset_scene":
            self.detail_navigation_active = False
            self.detail_view_key = "temp_sunset_scene"
            self.detail_action_index = 0
            self.detail_return_view_key = None
        self._append_history(
            current_module.key,
            ConversationEntry(
                role="assistant",
                text=action.label,
                source_prompt=action.label,
                kind="home_action",
                action_key=action.key,
            ),
        )
        self._mark_updated()
        self._render_current_module()
        self.query_one("#command-input", Input).focus()

    def _build_attention_response(self, attention: AttentionItem) -> Text:
        text = Text()
        text.append(f"[{attention.severity}] ", style=self._status_style(attention.emphasis_level))
        text.append(attention.subject, style=f"bold {PALETTE['text_main']}")
        text.append("\n", style=PALETTE["text_main"])
        text.append(attention.summary, style=PALETTE["text_main"])
        text.append("\n\nRecommended actions: ", style=PALETTE["text_muted"])
        text.append(attention.detail, style=f"bold {PALETTE['text_main']}")
        return text

    def _build_identity_graph_renderables(self) -> list[object]:
        renderables: list[object] = []
        renderables.append(Text("True Privilege graph", style=f"bold {PALETTE['orange_soft']}"))
        renderables.append(Text(""))
        renderables.append(self._build_identity_graph_status_text())
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Worth-noted graphs"))
        renderables.append(self._build_identity_graph_spotlights_table())
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Focused path"))
        renderables.append(self._build_emphasis_panel(self._build_identity_graph_text()))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Why this graph matters", self._build_identity_graph_impact_text(spotlight)))
        return renderables

    def _build_identity_graph_status_text(self) -> Text:
        text = Text()
        text.append("↗ ", style=f"bold {PALETTE['teal']}")
        text.append("3 worth-noted graphs ready", style=f"bold {PALETTE['violet']}")
        text.append("   ", style=PALETTE["text_main"])
        text.append("focus: ", style=PALETTE["text_muted"])
        text.append("multi-hop production reach", style=f"bold {PALETTE['purple']}")
        text.append("   ", style=PALETTE["text_main"])
        text.append("live edge visible", style=self._status_style("warn"))
        return text

    def _build_identity_graph_spotlights_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Graph", min_width=24)
        table.add_column("Scope", min_width=24)
        table.add_column("Live edge", no_wrap=True, min_width=11)
        table.add_column("Why it matters", min_width=34)

        for index, spotlight in enumerate(GRAPH_SPOTLIGHTS):
            table.add_row(
                Text(spotlight.label, style=f"bold {PALETTE['text_main']}"),
                Text(spotlight.scope, style=PALETTE["text_muted"]),
                self._build_badge(spotlight.live_edge, spotlight.tone if spotlight.live_edge != "none" else "muted"),
                Text(spotlight.note, style=PALETTE["text_main"]),
                style=f"on {PALETTE['bg_soft']}" if index == 0 else "",
            )
        return table

    def _build_identity_graph_text(self) -> Text:
        text = Text()
        self._append_privilege_path_line(text, "", "ID", "violet", "samantha.lee", f"bold {PALETTE['text_main']}")
        self._append_privilege_path_connector(text, "  ")
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "IDP",
            "info",
            "Okta -> Entra ID -> AWS IAM Identity Center",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "GRP",
            "accent",
            "Cloud-Prod-Admins",
            f"bold {PALETTE['purple']}",
        )
        self._append_privilege_path_line(
            text,
            "  |   +-- ",
            "ROLE",
            "risk",
            "AWS-Prod-Admin",
            self._status_style("risk"),
            suffix="LIVE EDGE",
            suffix_style=self._status_style("warn"),
        )
        self._append_privilege_path_line(
            text,
            "  |   |   +-- ",
            "PERM",
            "info",
            "ec2:ModifySnapshotAttribute",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  |   |   +-- ",
            "PERM",
            "info",
            "sts:AssumeRole -> Billing-ReadOnly",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  |   +-- ",
            "ROLE",
            "warn",
            "BreakGlass-Delegates",
            f"bold {PALETTE['violet']}",
            suffix="WATCH",
            suffix_style=self._status_style("warn"),
        )
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "PRA",
            "teal",
            "pra-4981 -> prod-bastion-07",
            f"bold {PALETTE['teal']}",
            suffix="ACTIVE",
            suffix_style=self._status_style("ok"),
        )
        self._append_privilege_path_line(
            text,
            "  |   +-- ",
            "HOST",
            "accent",
            "prd-sql-02",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  |   +-- ",
            "APP",
            "violet",
            "PagerDuty prod override",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "DEV",
            "info",
            "ENG-LT-2044",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "BREAK",
            "warn",
            "suspend Cloud-Prod-Admins inheritance before brokered reuse",
            f"bold {PALETTE['text_main']}",
        )
        return text

    def _build_identity_graph_impact_text(self) -> Text:
        text = Text()
        text.append(
            "This graph starts with worthwhile graph options, then expands the selected route into a denser multi-branch map so the analyst can see where workforce identity, privileged roles, brokered sessions, and production systems intersect.",
            style=PALETTE["text_main"],
        )
        return text

    def _build_identity_graph_renderables(self) -> list[object]:
        selected_spotlight = GRAPH_SPOTLIGHTS[self._selected_graph_catalog_index()]
        renderables: list[object] = []
        renderables.append(Text("True Privilege graph", style=f"bold {PALETTE['orange_soft']}"))
        renderables.append(Text(""))
        renderables.append(self._build_identity_graph_status_text(selected_spotlight))
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Worth-noted graphs"))
        renderables.append(self._build_identity_graph_spotlights_table())
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Selection", self._build_identity_graph_selection_text(selected_spotlight)))
        return renderables

    def _build_identity_graph_focus_renderables(self, spotlight: GraphSpotlight) -> list[object]:
        renderables: list[object] = []
        renderables.append(Text("True Privilege graph", style=f"bold {PALETTE['orange_soft']}"))
        renderables.append(Text(""))
        renderables.append(self._build_identity_graph_focus_status_text(spotlight))
        renderables.append(Text(""))
        renderables.append(self._build_section_heading("Focused path"))
        renderables.append(self._build_emphasis_panel(self._build_identity_graph_text(spotlight)))
        renderables.append(Text(""))
        renderables.append(self._build_section_block("Why this graph matters", self._build_identity_graph_impact_text(spotlight)))
        renderables.append(Text(""))
        renderables.append(Text("Next actions", style=f"bold {PALETTE['orange_soft']}"))
        renderables.extend(self._build_graph_focus_followup_lines())
        return renderables

    def _selected_graph_catalog_index(self) -> int:
        if self.detail_view_key == "true_privilege_graph":
            return max(0, min(self.detail_action_index, len(GRAPH_SPOTLIGHTS) - 1))
        spotlight = self._current_graph_spotlight()
        if spotlight is not None:
            return self._graph_catalog_index_for_key(spotlight.key)
        return 0

    def _build_identity_graph_status_text(self, spotlight: GraphSpotlight) -> Text:
        text = Text()
        text.append("-> ", style=f"bold {PALETTE['teal']}")
        text.append("3 worth-noted graphs ready", style=f"bold {PALETTE['violet']}")
        text.append("   ", style=PALETTE["text_main"])
        text.append("selected: ", style=PALETTE["text_muted"])
        text.append(spotlight.label, style=f"bold {PALETTE['purple']}")
        text.append("   ", style=PALETTE["text_main"])
        text.append("openable with Enter", style=f"bold {PALETTE['teal']}")
        return text

    def _build_identity_graph_focus_status_text(self, spotlight: GraphSpotlight) -> Text:
        tone = spotlight.tone if spotlight.live_edge != "none" else "muted"
        text = Text()
        text.append(spotlight.label, style=f"bold {PALETTE['violet']}")
        text.append(" | ", style=PALETTE["line"])
        text.append(spotlight.scope, style=PALETTE["text_muted"])
        text.append(" | ", style=PALETTE["line"])
        text.append("live edge ", style=PALETTE["text_muted"])
        text.append_text(self._build_badge(spotlight.live_edge, tone))
        text.append("\n", style=PALETTE["text_main"])
        text.append(spotlight.note, style=PALETTE["text_main"])
        return text

    def _build_identity_graph_spotlights_table(self) -> Table:
        table = Table(
            box=TABLE_BOX,
            expand=True,
            show_lines=True,
            border_style=PALETTE["line"],
            header_style=f"bold {PALETTE['orange_soft']}",
            padding=(0, 1),
            pad_edge=False,
        )
        table.add_column("Graph", min_width=24)
        table.add_column("Scope", min_width=24)
        table.add_column("Live edge", no_wrap=True, min_width=11)
        table.add_column("Why it matters", min_width=34)

        selected_index = self._selected_graph_catalog_index()
        allow_highlight = self.detail_navigation_active and (
            self.detail_view_key == "true_privilege_graph"
            or (self.detail_view_key is not None and self.detail_view_key.startswith("graph_focus:"))
        )
        for index, spotlight in enumerate(GRAPH_SPOTLIGHTS):
            table.add_row(
                Text(spotlight.label, style=f"bold {PALETTE['text_main']}"),
                Text(spotlight.scope, style=PALETTE["text_muted"]),
                self._build_badge(spotlight.live_edge, spotlight.tone if spotlight.live_edge != "none" else "muted"),
                Text(spotlight.note, style=PALETTE["text_main"]),
                style=f"on {PALETTE['bg_soft']}" if allow_highlight and index == selected_index else "",
            )
        return table

    def _build_identity_graph_selection_text(self, spotlight: GraphSpotlight) -> Text:
        text = Text()
        text.append("Selected ", style=PALETTE["text_muted"])
        text.append("-> ", style=f"bold {PALETTE['teal']}")
        text.append(spotlight.label, style=f"bold {PALETTE['violet']}")
        text.append(" | ", style=PALETTE["line"])
        text.append(spotlight.scope, style=PALETTE["text_main"])
        text.append("\n", style=PALETTE["text_main"])
        text.append("Use Up/Down and Enter to open the selected graph. ", style=PALETTE["text_main"])
        text.append(spotlight.note, style=PALETTE["text_muted"])
        return text

    def _build_identity_graph_text(self, spotlight: GraphSpotlight) -> Text:
        if spotlight.key == "contractor-support-overlap":
            return self._build_contractor_support_overlap_graph_text()
        if spotlight.key == "dormant-service-branch":
            return self._build_dormant_service_branch_graph_text()
        return self._build_samantha_production_spine_graph_text()

    def _build_samantha_production_spine_graph_text(self) -> Text:
        text = Text()
        self._append_privilege_path_line(text, "", "ID", "violet", "samantha.lee", f"bold {PALETTE['text_main']}")
        self._append_privilege_path_connector(text, "  ")
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "IDP",
            "info",
            "Okta -> Entra ID -> AWS IAM Identity Center",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "GRP",
            "accent",
            "Cloud-Prod-Admins",
            f"bold {PALETTE['purple']}",
        )
        self._append_privilege_path_line(
            text,
            "  |   +-- ",
            "ROLE",
            "risk",
            "AWS-Prod-Admin",
            self._status_style("risk"),
            suffix="LIVE EDGE",
            suffix_style=self._status_style("warn"),
        )
        self._append_privilege_path_line(
            text,
            "  |   |   +-- ",
            "PERM",
            "info",
            "ec2:ModifySnapshotAttribute",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  |   |   +-- ",
            "PERM",
            "info",
            "sts:AssumeRole -> Billing-ReadOnly",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  |   |   +-- ",
            "PERM",
            "info",
            "kms:Decrypt -> finance-prod-ring",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  |   +-- ",
            "ROLE",
            "warn",
            "BreakGlass-Delegates",
            f"bold {PALETTE['violet']}",
            suffix="WATCH",
            suffix_style=self._status_style("warn"),
        )
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "PRA",
            "teal",
            "pra-4981 -> prod-bastion-07",
            f"bold {PALETTE['teal']}",
            suffix="ACTIVE",
            suffix_style=self._status_style("ok"),
        )
        self._append_privilege_path_line(
            text,
            "  |   +-- ",
            "HOST",
            "accent",
            "prd-sql-02",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  |   +-- ",
            "APP",
            "violet",
            "PagerDuty prod override",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  |   +-- ",
            "TKT",
            "info",
            "CHG-8821 patch validation",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "DEV",
            "info",
            "ENG-LT-2044",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "NET",
            "teal",
            "ZTNA finance admin lane",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "BREAK",
            "warn",
            "suspend Cloud-Prod-Admins inheritance before brokered reuse",
            f"bold {PALETTE['text_main']}",
        )
        return text

    def _build_contractor_support_overlap_graph_text(self) -> Text:
        text = Text()
        self._append_privilege_path_line(
            text,
            "",
            "ID",
            "violet",
            "ops.vendor.ext",
            f"bold {PALETTE['text_main']}",
        )
        self._append_privilege_path_connector(text, "  ")
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "IDP",
            "info",
            "Okta workforce federation",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "GRP",
            "accent",
            "Vendor-Support-L2",
            f"bold {PALETTE['purple']}",
        )
        self._append_privilege_path_line(
            text,
            "  |   +-- ",
            "GRP",
            "warn",
            "Shared-Support-Bridge",
            f"bold {PALETTE['violet']}",
            suffix="WATCH",
            suffix_style=self._status_style("warn"),
        )
        self._append_privilege_path_line(
            text,
            "  |   |   +-- ",
            "PRA",
            "teal",
            "pra-5120 -> support-bastion-02",
            f"bold {PALETTE['teal']}",
            suffix="ACTIVE",
            suffix_style=self._status_style("ok"),
        )
        self._append_privilege_path_line(
            text,
            "  |   |   |   +-- ",
            "HOST",
            "info",
            "crm-prod-app-04",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  |   +-- ",
            "SAFE",
            "risk",
            "core-support-breakglass",
            self._status_style("risk"),
            suffix="LIVE EDGE",
            suffix_style=self._status_style("warn"),
        )
        self._append_privilege_path_line(
            text,
            "  |   |   +-- ",
            "CHECK",
            "info",
            "checkout -> web-admin-emergency",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  |   |   +-- ",
            "ROLE",
            "warn",
            "prod-support-elevate",
            f"bold {PALETTE['violet']}",
        )
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "TKT",
            "teal",
            "SUP-7782 customer outage bridge",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "BREAK",
            "warn",
            "split Shared-Support-Bridge from break-glass checkout policy",
            f"bold {PALETTE['text_main']}",
        )
        return text

    def _build_dormant_service_branch_graph_text(self) -> Text:
        text = Text()
        self._append_privilege_path_line(
            text,
            "",
            "SVC",
            "accent",
            "svc-backup-old",
            f"bold {PALETTE['text_main']}",
            suffix="DORMANT",
            suffix_style=self._status_style("warn"),
        )
        self._append_privilege_path_connector(text, "  ")
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "AD",
            "info",
            "legacy backup OU",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "GRP",
            "accent",
            "Backup-Operators",
            f"bold {PALETTE['purple']}",
        )
        self._append_privilege_path_line(
            text,
            "  |   +-- ",
            "JOB",
            "violet",
            "nightly-image-retain",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  |   +-- ",
            "HOST",
            "info",
            "backup-orchestrator-01",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  |   +-- ",
            "SAFE",
            "warn",
            "backup-admin-lane",
            f"bold {PALETTE['teal']}",
            suffix="WATCH",
            suffix_style=self._status_style("warn"),
        )
        self._append_privilege_path_line(
            text,
            "  |   |   +-- ",
            "ROLE",
            "accent",
            "Legacy-Domain-Backup",
            f"bold {PALETTE['violet']}",
        )
        self._append_privilege_path_line(
            text,
            "  |   |   +-- ",
            "PERM",
            "info",
            "restore backup catalog",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  |   |   +-- ",
            "PERM",
            "info",
            "read archived domain secrets",
            PALETTE["text_main"],
        )
        self._append_privilege_path_line(
            text,
            "  +-- ",
            "BREAK",
            "warn",
            "retire the scheduled task or disable the service identity",
            f"bold {PALETTE['text_main']}",
        )
        return text

    def _build_identity_graph_impact_text(self, spotlight: GraphSpotlight | None = None) -> Text:
        text = Text()
        if spotlight is None:
            spotlight = self._current_graph_spotlight()
        if spotlight is None:
            spotlight = GRAPH_SPOTLIGHTS[self._selected_graph_catalog_index()]

        text.append(spotlight.note, style=PALETTE["text_main"])
        text.append("\n", style=PALETTE["text_main"])
        guidance = {
            "samantha-lee-prod-spine": "Start with the inherited cloud-admin group and the live PRA route, because together they keep production reach reusable.",
            "contractor-support-overlap": "Focus on the support bridge and break-glass safe together, because the overlap is what turns normal vendor access into privileged reach.",
            "dormant-service-branch": "Focus on the dormant scheduler and the backup-admin lane, because stale service identities are easy to overlook during access reviews.",
        }
        text.append(
            guidance.get(spotlight.key, "Open the graph to inspect the highest-leverage break point first."),
            style=PALETTE["text_muted"],
        )
        return text

    def _build_graph_focus_followup_lines(self) -> list[Text]:
        lines: list[Text] = []
        for index, action in enumerate(GRAPH_FOCUS_ACTIONS):
            selected = (
                self.detail_navigation_active
                and self.detail_view_key is not None
                and self.detail_view_key.startswith("graph_focus:")
                and self.detail_action_index == index
            )
            line = Text()
            line.append(
                "> " if selected else "  ",
                style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["line"],
            )
            line.append(
                action.label,
                style=f"bold {PALETTE['orange_primary']}" if selected else PALETTE["text_main"],
            )
            if selected:
                line.stylize(f"on {PALETTE['bg_soft']}")
            lines.append(line)
        return lines

    def _bar(self, value: int, width: int = 12) -> Text:
        return pipe_bar(value, width=width)

    def _keywords(self, prompt: str) -> list[str]:
        cleaned = [token.strip(".,!?;:()[]{}\"'").lower() for token in prompt.split()]
        keywords = [token for token in cleaned if len(token) > 3]
        if not keywords:
            return ["identity", "policy", "session"]
        return keywords[:4]

    def _matches_agent_status_request(self, prompt: str) -> bool:
        tokens = set(re.findall(r"[a-z0-9]+", prompt.lower()))
        if not tokens:
            return False

        if tokens & AGENT_STATUS_CORE_TOKENS and tokens & AGENT_STATUS_HINT_TOKENS:
            return True

        hint_matches = len(tokens & AGENT_STATUS_HINT_TOKENS)
        return hint_matches >= 3 and any(token in tokens for token in ("status", "health", "connection"))


if __name__ == "__main__":
    PathfinderPrototypeApp().run()
