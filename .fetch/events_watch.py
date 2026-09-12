"""Subscribe to the global event bus SSE and capture drill events (id + progress)."""
import json
import time
import urllib.request

URL = "http://127.0.0.1:8000/api/v1/events?stream=all&api_key=aegis-dev-key"
t0 = time.time()
try:
    req = urllib.request.Request(URL, headers={"Accept": "text/event-stream"})
    with urllib.request.urlopen(req, timeout=1500) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if not line or line.startswith(":"):
                continue
            if line.startswith("event:") or line.startswith("data:"):
                print("[%6.1fs] %s" % (time.time() - t0, line[:500]), flush=True)
            if "drill_summary" in line or "drill_done" in line:
                print("[%6.1fs] DRILL FINISHED" % (time.time() - t0), flush=True)
                break
            if time.time() - t0 > 1400:
                print("cap reached", flush=True)
                break
except Exception as e:  # noqa: BLE001
    print("ERR", type(e).__name__, str(e)[:300], flush=True)
