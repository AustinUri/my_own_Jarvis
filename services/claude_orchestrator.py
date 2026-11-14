from __future__ import annotations

from pathlib import Path

from .claude_code_local import run_claude
from .claude_project_memory import memory

REPO = Path(__file__).resolve().parents[1]

def classify(text: str) -> str:
    low = (text or "").strip().lower()
    groups = [
        ("tutor", ("teach", "explain", "tutor", "למד אותי", "תלמד אותי", "תסביר")),
        ("architecture", ("architecture", "project structure", "ארכיטקטורה", "מבנה הפרויקט")),
        ("test", ("run tests", "verify", "תריץ בדיקות", "בדיקות")),
        ("fix", ("fix", "refactor", "implement", "תתקן", "שנה את הקוד", "תממש")),
        ("review", ("review", "audit", "בדוק את הקוד", "תבדוק את הקוד", "סקור")),
    ]
    for mode, words in groups:
        if any(w in low for w in words):
            return mode
    return "review"

def explicit_model(text: str) -> str:
    low = (text or "").lower()
    if any(x in low for x in ("עם שניהם", "both models", "dual", "קוון וגמה", "גמה וקוון")):
        return "dual"
    if any(x in low for x in ("gemma", "גמה")):
        return "gemma"
    if any(x in low for x in ("qwen", "קוון", "קווין")):
        return "qwen"
    return "auto"

def is_explicit_claude_request(text: str) -> bool:
    low = (text or "").strip().lower()
    return any(x in low for x in (
        "claude", "קלוד", "code review", "code tutor",
        "בדוק את הקוד", "תבדוק את הקוד",
        "למד אותי את הקוד", "תלמד אותי את הקוד",
        "ארכיטקטורת הקוד",
    ))

def auto_model(mode: str) -> str:
    # Qwen stays primary for repository/tool-heavy work.
    # Gemma is used for explanation/teaching when no explicit choice was made.
    return "gemma" if mode == "tutor" else "qwen"

def _prompt(mode: str, task: str, prior: str, remote: bool) -> str:
    common = f"""
You are the JARVIS repository engineering specialist.
User task:
{task}

{prior}

Rules:
- Read CLAUDE.md first.
- Inspect actual repository files; never guess file contents.
- Preserve verified phone.call, real dialer, caller announcement, caller memory,
  unlock missed-call briefing, Device Bus and hybrid reasoning.
- Do not read or expose .env files, tokens or private keys.
- Never git push automatically.
- Do not claim tests passed unless they ran.
""".strip()

    if mode == "tutor":
        return common + """
Tutor mode: read-only. Explain exact files/functions, start simple, include an ASCII flow.
"""
    if mode == "architecture":
        return common + """
Architecture mode: read-only. Map components/data flow and flag Windows/Linux portability coupling.
"""
    if mode == "test":
        return common + """
Test mode: read-only unless explicitly asked to fix. Run the smallest relevant checks.
"""
    if mode == "review":
        return common + """
Review mode: read-only. Rank correctness, regression, security, lifecycle/concurrency and test findings.
"""
    if remote:
        return common + """
Remote phone request: PLAN ONLY. Do not modify repository files.
"""
    return common + """
Implementation mode: inspect git status, make the smallest safe edit, run relevant tests,
show diff summary, never commit or push automatically.
"""

def run_skill(payload: dict) -> dict:
    task = str(payload.get("text") or payload.get("task") or "").strip()
    if not task:
        return {"ok": False, "error": "Claude skill task is empty."}

    mode = str(payload.get("mode") or classify(task)).lower()
    remote = bool(payload.get("remote", False))
    wanted = str(payload.get("model") or explicit_model(task)).lower()
    if wanted == "auto":
        wanted = auto_model(mode)

    prior = memory.context(task, limit=4)
    cc_mode = "plan" if (remote or mode in {"tutor","review","architecture","test"}) else "edit"
    prompt = _prompt(mode, task, prior, remote)

    if wanted != "dual":
        result = run_claude(
            prompt,
            cwd=REPO,
            mode=cc_mode,
            model_kind=wanted,
        )
        if result.get("ok") and result.get("text"):
            memory.remember(mode, task, str(result["text"]))
        result["skill"] = mode
        result["remote"] = remote
        return result

    # Dual mode: Qwen does the repository task; Gemma reviews the result.
    primary = run_claude(
        prompt,
        cwd=REPO,
        mode=cc_mode,
        model_kind="qwen",
    )
    primary_text = str(primary.get("text") or "")
    critic_prompt = f"""
You are the second-opinion reviewer for JARVIS.
Do not edit files.
Original task:
{task}

Qwen's result:
{primary_text}

Check it for incorrect assumptions, missing risks, contradictions, and weak reasoning.
Return only useful corrections or say that no material correction was found.
""".strip()
    critic = run_claude(
        critic_prompt,
        cwd=REPO,
        mode="plan",
        model_kind="gemma",
    )

    combined = (
        "QWEN PRIMARY\n"
        + primary_text
        + "\n\nGEMMA SECOND OPINION\n"
        + str(critic.get("text") or critic.get("error") or "")
    )
    ok = bool(primary.get("ok")) and bool(critic.get("ok"))
    if ok:
        memory.remember("dual-" + mode, task, combined)

    return {
        "ok": ok,
        "provider": "claude-code-local-dual",
        "model": "qwen/qwen3.5-9b + google/gemma-4-e4b",
        "model_kind": "dual",
        "text": combined,
        "skill": mode,
        "remote": remote,
        "primary": primary,
        "critic": critic,
    }
