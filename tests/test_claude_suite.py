import os
import tempfile
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from services.claude_code_local import local_env
from services.claude_orchestrator import classify, explicit_model, auto_model
from services.claude_project_memory import ClaudeProjectMemory

def main():
    assert classify("תלמד אותי את הקוד") == "tutor"
    assert classify("בדוק את הקוד") == "review"
    assert classify("תתקן את הקוד") == "fix"

    assert explicit_model("קלוד תשתמש בגמה") == "gemma"
    assert explicit_model("קלוד תשתמש בקוון") == "qwen"
    assert explicit_model("קלוד בדוק עם שניהם") == "dual"
    assert auto_model("tutor") == "gemma"
    assert auto_model("review") == "qwen"

    os.environ["ANTHROPIC_API_KEY"] = "MUST_NOT_LEAK"
    env = local_env("qwen/qwen3.5-9b")
    assert "ANTHROPIC_API_KEY" not in env
    assert env["ANTHROPIC_BASE_URL"].startswith("http://127.0.0.1:")

    with tempfile.TemporaryDirectory() as td:
        mem = ClaudeProjectMemory(Path(td)/"m.sqlite3")
        mem.remember("review", "phone call router", "phone.call path verified")
        hits = mem.search("phone")
        assert hits

    print("PASS: skill routing")
    print("PASS: Qwen/Gemma/dual selection")
    print("PASS: Anthropic API key blocked from local route")
    print("PASS: project memory")

if __name__ == "__main__":
    main()
