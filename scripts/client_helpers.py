"""Client helper utilities: timeout, retry, and batch submission examples.

Usage:
  python scripts\client_helpers.py http://localhost:8000

This file is a lightweight example for Team C to call the evaluate/evaluate_batch endpoints.
"""
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def make_session(retries: int = 3, backoff_factor: float = 0.3) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset(["POST", "GET"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def post_with_timeout(url: str, payload: dict, timeout: float = 0.2) -> dict:
    """POST a single evaluation request with a timeout and retries."""
    session = make_session()
    resp = session.post(url.rstrip("/") + "/evaluate", json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def submit_batch(url: str, items: list, timeout: float = 5.0) -> dict:
    """Submit a small batch to /evaluate_batch; server expected to return per-item results."""
    session = make_session()
    resp = session.post(url.rstrip("/") + "/evaluate_batch", json={"items": items}, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    import sys

    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    try:
        with open("examples/request_examples.json", "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception:
        print("Could not load examples/request_examples.json")
        raise

    print("Submitting batch to:", base)
    try:
        out = submit_batch(base, items)
        print(json.dumps(out, indent=2))
    except Exception as e:
        print("Batch submit failed:", e)
        # fallback: try single-item posts
        for it in items:
            try:
                r = post_with_timeout(base, it)
                print(json.dumps(r, indent=2))
            except Exception as ex:
                print("single submit failed:", ex)
