from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import websockets


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

LM_STUDIO_URL = os.getenv(
    "JARVIS_WINDOWS_LM_STUDIO_URL",
    "http://127.0.0.1:1234",
).rstrip("/")

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

    requested_max_tokens = int(
        payload.get("max_tokens", 700)
    )

    deep = bool(
        payload.get("deep", False)
    )

    # Qwen reasoning and final-answer tokens share the same output budget.
    # Deep work therefore gets enough room to reason AND finish its answer.
    max_tokens = (
        max(requested_max_tokens, 1200)
        if deep
        else requested_max_tokens
    )

    combined_input = (
        f"System instructions:\n{system}\n\n"
        f"User request:\n{text}"
    )

    body = {
        "model": AI_MODEL,
        "input": combined_input,
        "reasoning": "on" if deep else "off",
        "temperature": temperature,
        "max_output_tokens": max_tokens,
        "store": False,
    }

    request = Request(
        f"{LM_STUDIO_URL}/api/v1/chat",
        data=json.dumps(
            body,
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=AI_TIMEOUT,
        ) as response:
            raw = json.loads(
                response.read().decode("utf-8")
            )

    except HTTPError as exc:
        try:
            detail = exc.read().decode(
                "utf-8",
                errors="replace",
            )[:1000]
        except Exception:
            detail = ""

        raise RuntimeError(
            f"LM Studio returned HTTP {exc.code}: {detail}"
        ) from exc

    except (
        URLError,
        TimeoutError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise RuntimeError(
            f"LM Studio request failed: {exc}"
        ) from exc

    output = raw.get("output")

    if not isinstance(output, list):
        raise RuntimeError(
            "LM Studio returned no output list"
        )

    parts = []

    for item in output:
        if not isinstance(item, dict):
            continue

        if item.get("type") != "message":
            continue

        content = item.get("content")

        if isinstance(content, str) and content.strip():
            parts.append(content.strip())

    answer = "\n".join(parts).strip()

    if not answer:
        stats = raw.get("stats")

        if not isinstance(stats, dict):
            stats = {}

        reasoning_tokens = int(
            stats.get("reasoning_output_tokens") or 0
        )
        total_tokens = int(
            stats.get("total_output_tokens") or 0
        )

        # Never send the model's private reasoning trace back to Cloud Core.
        raise RuntimeError(
            "Windows Qwen produced no final answer "
            f"(reasoning_tokens={reasoning_tokens}, "
            f"total_output_tokens={total_tokens}, "
            f"budget={max_tokens})"
        )

    stats = raw.get("stats")

    if not isinstance(stats, dict):
        stats = {}

    return {
        "ok": True,
        "provider": "windows-qwen",
        "model": raw.get(
            "model_instance_id",
            AI_MODEL,
        ),
        "text": answer,
        "reasoning": "on" if deep else "off",
        "stats": stats,
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
                "`n[V30] Windows client stopped."
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
