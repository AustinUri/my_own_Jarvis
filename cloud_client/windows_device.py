import asyncio
import os
from pathlib import Path

import websockets


DEVICE_ID = "uri-windows"
DEVICE_TYPE = "windows"
CLOUD_URL = (
    f"wss://uri-jarvis.duckdns.org/api/v1/ws/"
    f"{DEVICE_ID}?device_type={DEVICE_TYPE}"
)

TOKEN_FILE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Jarvis" / "cloud.token"


def load_token() -> str:
    if not TOKEN_FILE.exists():
        raise RuntimeError(f"Cloud token not found: {TOKEN_FILE}")

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()

    if not token:
        raise RuntimeError("Cloud token file is empty")

    return token


async def run():
    token = load_token()

    while True:
        try:
            print(f"[V30] Connecting {DEVICE_ID} to JARVIS Cloud...")

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

                while True:
                    await websocket.send("ping")

                    reply = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=10,
                    )

                    print("[CLOUD]", reply)

                    await asyncio.sleep(30)

        except KeyboardInterrupt:
            print("\n[V30] Windows client stopped.")
            return

        except Exception as exc:
            print(f"[V30] Connection lost: {exc}")
            print("[V30] Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run())
