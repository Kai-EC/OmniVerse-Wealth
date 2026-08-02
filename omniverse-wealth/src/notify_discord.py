"""Discord Webhook sender (called from Node.js via subprocess).

Usage:
    python notify_discord.py '{"content": "...", "embeds": [...]}'
"""
import json
import sys
import httpx

WEBHOOK_URL = "https://discord.com/api/webhooks/1533035116308201574/AFUDeZiESYQAmTl7n8mkEU8Jp8Gh4PJu-ksPmnmPxVLyxx8g8riH-xWXP_0AV-yOAGzi"


def send(payload: dict) -> bool:
    try:
        with httpx.Client(timeout=10) as client:
            r = client.post(WEBHOOK_URL, json=payload)
            return r.status_code == 204
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python notify_discord.py '<json payload>'")
        sys.exit(1)

    payload = json.loads(sys.argv[1])
    success = send(payload)
    print("ok" if success else "failed")
    sys.exit(0 if success else 1)
