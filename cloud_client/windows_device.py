from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import websockets


REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.provider import OpenAICompatibleProvider


DEVICE_ID = "uri-windows"
DEVICE_TYPE = "windows"

CLOUD_URL = (
    f"wss://uri-jarvis.duckdns.org/api/v1/ws/"
    f"{DEVICE_ID}?device_type={DEVICE_TYPE}"
)

TOKEN_FILE = (
    Path(os.environ.get("LOCALAPPDATA", Path.home()))
    / "Jarvis"
    / "cloud.token"
)

AI_BASE_URL = os.getenv(
    "JARVIS_WINDOWS_AI_BASE_URL",
    "http://127.0.0.1:1234/v1",
)

AI_MODEL = os.getenv(
    "JARVIS_WINDOWS_AI_MODEL",
    "jarvis-qwen",
)

AI_TIMEOUT = float(
    os.getenv(
        "JARVIS_WINDOWS_AI_TIMEOUT",
        "180",
    )
)


def load_token() -> str:
    if not TOKEN_FILE.exists():
        raise RuntimeError(
            f"Cloud token not found: {TOKEN_FILE}"
        )

    token = TOKEN_FILE.read_text(
        encoding="utf-8",
    ).strip()

    if not token:
        raise RuntimeError(
            "Cloud token file is empty"
        )

    return token


def run_local_reasoning(payload: dict) -> dict:
    text = str(payload.get("text") or "").strip()

    if not text:
        raise RuntimeError(
            "Reasoning job contains no text"
        )

    system = str(
        payload.get("system")
        or "You are JARVIS. Give a clear, accurate, practical answer."
    ).strip()

    temperature = float(
        payload.get("temperature", 0.2)
    )

    max_tokens = int(
        payload.get("max_tokens", 700)
    )

    provider = OpenAICompatibleProvider(
        base_url=AI_BASE_URL,
        model=AI_MODEL,
        api_key="lm-studio",
        timeout=AI_TIMEOUT,
    )

    message = provider.chat(
        messages=[
            {
                "role": "system",
                "content": system,
            },
            {
                "role": "user",
                "content": text,
            },
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    answer = str(
        message.get("content") or ""
    ).strip()

    if not answer:
        raise RuntimeError(
            "Windows Qwen returned no final answer"
        )

    return {
        "ok": True,
        "provider": "windows-qwen",
        "model": provider.resolve_model(),
        "text": answer,
    }


async def process_job(
    websocket,
    job: dict,
):
    job_id = str(
        job.get("job_id") or ""
    )

    job_type = str(
        job.get("job_type") or ""
    )

    payload = job.get("payload")

    if not isinstance(payload, dict):
        payload = {}

    result = {
        "type": "job_result",
        "job_id": job_id,
        "ok": False,
    }

    try:
        if job_type == "reasoning":
            worker_result = await asyncio.to_thread(
                run_local_reasoning,
                payload,
            )

            result.update(worker_result)

        else:
            result["error"] = (
                f"Unsupported Windows job type: {job_type}"
            )

    except Exception as exc:
        result["error"] = str(exc)

    await websocket.send(
        json.dumps(
            result,
            ensure_ascii=False,
        )
    )


async def heartbeat(websocket):
    while True:
        await asyncio.sleep(30)
        await websocket.send("ping")


async def run():
    token = load_token()

    while True:
        try:
            print(
                f"[V30] Connecting {DEVICE_ID} "
                f"to JARVIS Cloud..."
            )

            async with websockets.connect(
                CLOUD_URL,
                additional_headers={
                    "Authorization": f"Bearer {token}"
                },
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
            ) as websocket:

                print("[V30] CONNECTED")

                welcome = await websocket.recv()
                print("[CLOUD]", welcome)

                heartbeat_task = asyncio.create_task(
                    heartbeat(websocket)
                )

                try:
                    while True:
                        raw = await websocket.recv()
                        print("[CLOUD]", raw)

                        try:
                            message = json.loads(raw)
                        except (
                            json.JSONDecodeError,
                            TypeError,
                        ):
                            continue

                        if message.get("type") == "job":
                            await process_job(
                                websocket,
                                message,
                            )

                finally:
                    heartbeat_task.cancel()

                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass

        except KeyboardInterrupt:
            print(
                "\n[V30] Windows client stopped."
            )
            return

        except Exception as exc:
            print(
                f"[V30] Connection lost: {exc}"
            )
            print(
                "[V30] Reconnecting in 5 seconds..."
            )
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run())
