#!/usr/bin/env python3
"""Live demo of the OCS Intelligence public API and EC2 wait line.

Stdlib only. Reads OCS_BASE_URL and OCS_API_KEY from the repo .env
(or the environment). Never prints the key.

  python3 scripts/demo.py              # health, auth, models, 0.5b, queue
  python3 scripts/demo.py --pause      # wait for Enter between stages
  python3 scripts/demo.py --quality    # also hit the 27B model (slow)
  python3 scripts/demo.py --skip-queue # skip the 7-way concurrency blast
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CTX = ssl.create_default_context()

FAST = "qwen2.5:0.5b"
QUALITY = "qwen3.8:27b"


def load_dotenv() -> None:
    path = REPO / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_dotenv()
BASE = os.environ.get("OCS_BASE_URL", "https://ai.opencodingsociety.com/v1").rstrip("/")
ROOT = BASE[: -len("/v1")] if BASE.endswith("/v1") else "https://ai.opencodingsociety.com"
KEY = os.environ.get("OCS_API_KEY", "")


class Failed(Exception):
    pass


def banner(title: str) -> None:
    print()
    print(f"── {title} " + "─" * max(0, 56 - len(title)))


def ok(label: str, detail: str = "") -> None:
    extra = f"  {detail}" if detail else ""
    print(f"  PASS  {label}{extra}")


def fail(label: str, detail: str = "") -> None:
    extra = f"  {detail}" if detail else ""
    print(f"  FAIL  {label}{extra}")


def pause(enabled: bool) -> None:
    if enabled:
        input("  [Enter] continue  ")


def http(method: str, url: str, *, headers=None, body=None, timeout=120):
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
    }


def chat_payload(
    model: str,
    *,
    stream: bool = False,
    max_tokens: int = 40,
    prompt: str = "Say hello in one short sentence.",
) -> bytes:
    return json.dumps(
        {
            "model": model,
            "stream": stream,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()


def assistant_text(body: bytes) -> str:
    try:
        data = json.loads(body.decode())
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, json.JSONDecodeError, UnicodeDecodeError):
        return body[:160].decode("utf-8", errors="replace")


def tok_s(body: bytes) -> str:
    try:
        data = json.loads(body.decode())
        t = data.get("timings") or {}
        rate = t.get("predicted_per_second")
        n = t.get("predicted_n")
        if rate is None:
            return ""
        return f"{n} tok, {rate:.1f} tok/s"
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return ""


def stream_chat(
    model: str,
    *,
    max_tokens: int = 80,
    prompt: str = "Write a long essay about rivers.",
    timeout: float = 180,
) -> tuple[int, str, bool, float]:
    req = urllib.request.Request(
        f"{BASE}/chat/completions",
        data=chat_payload(model, stream=True, max_tokens=max_tokens, prompt=prompt),
        method="POST",
        headers=auth_headers(),
    )
    t0 = time.monotonic()
    saw_queued = False
    chunks: list[str] = []
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
            status = resp.status
            while True:
                piece = resp.read(256)
                if not piece:
                    break
                text = piece.decode("utf-8", errors="replace")
                chunks.append(text)
                if ": queued" in text:
                    saw_queued = True
            return status, "".join(chunks), saw_queued, time.monotonic() - t0
    except urllib.error.HTTPError as e:
        return (
            e.code,
            e.read().decode("utf-8", errors="replace"),
            False,
            time.monotonic() - t0,
        )


def expect(status: int, want: int, label: str, detail: str = "") -> None:
    if status == want:
        ok(label, detail)
        return
    fail(label, f"HTTP {status} (wanted {want}) {detail}".strip())
    raise Failed(label)


def stage_health() -> None:
    banner("1. The public site is up")
    status, _, body = http("GET", f"{ROOT}/healthz", timeout=15)
    expect(status, 200, "GET /healthz", body.decode()[:80])
    status, _, body = http("GET", f"{ROOT}/api/version", timeout=15)
    expect(status, 200, "Open WebUI /api/version", body.decode()[:80])


def stage_auth() -> None:
    banner("2. Auth happens before anyone joins the line")
    status, _, _ = http("GET", f"{BASE}/models", timeout=15)
    expect(status, 401, "no Bearer key → 401")
    status, _, _ = http(
        "GET",
        f"{BASE}/models",
        headers={"Authorization": "Bearer sk-wrong-key"},
        timeout=15,
    )
    expect(status, 401, "wrong key → 401")
    for i in range(5):
        status, _, _ = http(
            "POST",
            f"{BASE}/chat/completions",
            headers={
                "Authorization": "Bearer sk-wrong-key",
                "Content-Type": "application/json",
            },
            body=chat_payload(FAST, max_tokens=8),
            timeout=20,
        )
        if status != 401:
            fail("forged completions do not occupy the GPU", f"HTTP {status} on try {i+1}")
            raise Failed("forged key")
    ok("five forged completions all 401 (no GPU slot taken)")


def stage_models() -> None:
    banner("3. OpenAI-compatible /v1/models")
    status, _, body = http("GET", f"{BASE}/models", headers=auth_headers(), timeout=20)
    expect(status, 200, "GET /v1/models")
    text = body.decode()
    if FAST not in text or QUALITY not in text:
        fail("both models listed", text[:200])
        raise Failed("models")
    ok(f"lists {FAST} and {QUALITY}")
    status, _, _ = http(
        "POST",
        f"{BASE}/chat/completions",
        headers=auth_headers(),
        body=chat_payload("does-not-exist"),
        timeout=20,
    )
    expect(status, 404, "unknown model → 404 (does not join a lane)")


def stage_fast() -> None:
    banner(f"4. Fast lane  {FAST}  (2 GPUs)")
    t0 = time.monotonic()
    status, _, body = http(
        "POST",
        f"{BASE}/chat/completions",
        headers=auth_headers(),
        body=chat_payload(FAST, max_tokens=32, prompt="Say hello in one short sentence."),
        timeout=60,
    )
    dt = time.monotonic() - t0
    expect(status, 200, f"blocking completion in {dt:.1f}s", tok_s(body))
    print(f"         “{assistant_text(body)[:200]}”")


def stage_quality() -> None:
    banner(f"5. Quality lane  {QUALITY}  (5 GPUs, ~9 tok/s)")
    print("         This one thinks before it answers. Give it a moment.")
    t0 = time.monotonic()
    status, _, body = http(
        "POST",
        f"{BASE}/chat/completions",
        headers=auth_headers(),
        body=chat_payload(
            QUALITY,
            max_tokens=96,
            prompt="Name two sorting algorithms. One short sentence.",
        ),
        timeout=180,
    )
    dt = time.monotonic() - t0
    expect(status, 200, f"blocking completion in {dt:.1f}s", tok_s(body))
    print(f"         “{assistant_text(body)[:240]}”")


def stage_queue() -> None:
    banner("6. Classroom stampede — 7 Copilot tabs on the fast model")
    print("         Lane B: 2 running + 4 waiting = 6. The 7th must 429.")
    prompt = (
        "Write a long detailed essay about the history of mathematics. Keep going."
    )
    results: list[tuple[int, float, bool]] = []
    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=7) as pool:
        futs = [
            pool.submit(
                stream_chat,
                FAST,
                max_tokens=160,
                prompt=prompt,
            )
            for _ in range(7)
        ]
        for i, fut in enumerate(as_completed(futs), start=1):
            status, body, queued, dt = fut.result()
            results.append((status, dt, queued))
            tag = "WAITED (keepalive)" if queued else ""
            print(f"         #{i}  HTTP {status}  {dt:.1f}s  {tag}".rstrip())
            if status == 429:
                snippet = body.strip().replace("\n", " ")[:140]
                print(f"              {snippet}")

    n200 = sum(1 for s, _, _ in results if s == 200)
    n429 = sum(1 for s, _, _ in results if s == 429)
    elapsed = time.monotonic() - t0
    detail = f"{n200} served, {n429} rejected, wall {elapsed:.1f}s"
    if n200 == 6 and n429 == 1:
        ok("exactly six in the system, seventh 429", detail)
        return
    fail("queue math", f"wanted 6×200 + 1×429, got {detail}")
    raise Failed("queue")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pause",
        action="store_true",
        help="wait for Enter between stages (for a live walkthrough)",
    )
    parser.add_argument(
        "--quality",
        action="store_true",
        help="also demo qwen3.8:27b (slow; ~one minute)",
    )
    parser.add_argument(
        "--skip-queue",
        action="store_true",
        help="skip the 7-way concurrency blast",
    )
    args = parser.parse_args()

    if not KEY or KEY.startswith("sk-your-"):
        print("Missing OCS_API_KEY. Copy .env.example to .env and set the student key.", file=sys.stderr)
        return 2

    print("OCS Intelligence  —  live demo")
    print(f"  site   {ROOT}")
    print(f"  api    {BASE}")
    print("  key    (from .env, not printed)")

    failed: list[str] = []

    def run(fn, after: bool = True) -> None:
        try:
            fn()
        except Failed as exc:
            failed.append(str(exc))
        except Exception as exc:
            fail(fn.__name__, f"{type(exc).__name__}: {exc}")
            failed.append(fn.__name__)
        if after:
            pause(args.pause)

    run(stage_health)
    run(stage_auth)
    run(stage_models)
    run(stage_fast)
    if args.quality:
        run(stage_quality)
    if not args.skip_queue:
        run(stage_queue, after=False)
    else:
        pause(args.pause)

    print()
    if failed:
        print(f"Demo finished with {len(failed)} failure(s): {', '.join(failed)}")
        return 1
    print("Demo finished. All stages passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
