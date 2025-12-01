"""Simple JSON-line audit logger for decisions.

Writes structured decision records to `audit.log` in the repository root.
Includes helpers for tests to read/clear the log.
"""
import json
import atexit
import json
import queue
import threading
import random
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Dict, List

_lock = RLock()
LOG_PATH = Path(__file__).resolve().parent.parent / "audit.log"

# Background batching configuration
_AUDIT_QUEUE: "queue.Queue[object]" = queue.Queue()
_BATCH_SIZE = 64
_FLUSH_INTERVAL = 0.5  # seconds
_STOP_EVENT = threading.Event()

# In-process metrics (kept simple to avoid an external dependency)
_METRICS = {
    "enqueued_count": 0,
    "dropped_count": 0,
    "flushed_batches": 0,
    "last_flush_duration_ms": 0.0,
    # decision latency aggregates (ms)
    "decision_count": 0,
    "decision_total_ms": 0.0,
    # org lookup metrics
    "org_cache_hits": 0,
    "org_cache_misses": 0,
    "org_graph_lookups": 0,
}


# Runtime toggle to disable auditing in very hot paths (opt-out)
_AUDIT_ENABLED = True

# Sampling rate in [0.0, 1.0]. When <1.0, only a fraction of decisions are enqueued.
_AUDIT_SAMPLE_RATE = 1.0


def set_audit_sample_rate(rate: float) -> None:
    """Set sampling rate for audit lines. Clamped to [0.0, 1.0]."""
    global _AUDIT_SAMPLE_RATE
    try:
        r = float(rate)
    except Exception:
        return
    if r < 0.0:
        r = 0.0
    if r > 1.0:
        r = 1.0
    _AUDIT_SAMPLE_RATE = r


def get_audit_sample_rate() -> float:
    return float(_AUDIT_SAMPLE_RATE)


def _writer_loop():
    """Background writer that flushes queued audit lines to disk in batches."""
    buffer = []
    last_flush = datetime.now(timezone.utc)
    while not _STOP_EVENT.is_set():
        try:
            # Wait for up to FLUSH_INTERVAL for a new item
            item = _AUDIT_QUEUE.get(timeout=_FLUSH_INTERVAL)
            buffer.append(item)
        except queue.Empty:
            pass

        # Flush if buffer large enough or interval elapsed
        now = datetime.now(timezone.utc)
        if buffer and (len(buffer) >= _BATCH_SIZE or (now - last_flush).total_seconds() >= _FLUSH_INTERVAL):
            try:
                start = datetime.now(timezone.utc)
                with _lock, open(LOG_PATH, "a", encoding="utf-8") as f:
                    for item in buffer:
                        # Serialize here in the background thread to keep the main path fast
                        try:
                            line = json.dumps(item, default=str)
                        except Exception:
                            # Fallback: ensure we still write something
                            line = json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "decision": str(item)}, default=str)
                        f.write(line + "\n")
                duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000.0
                # update metrics
                _METRICS["flushed_batches"] += 1
                _METRICS["last_flush_duration_ms"] = duration
            except Exception:
                # Best-effort: don't crash the thread on I/O issues
                pass
            buffer.clear()
            last_flush = now


_WRITER_THREAD = threading.Thread(target=_writer_loop, name="audit-writer", daemon=True)
_WRITER_THREAD.start()


def _enqueue_line(item: object) -> None:
    try:
        _AUDIT_QUEUE.put_nowait(item)
        _METRICS["enqueued_count"] += 1
    except queue.Full:
        # Drop on backpressure to avoid blocking critical paths
        _METRICS["dropped_count"] += 1
        pass


def increment_metric(name: str, amount: float = 1.0) -> None:
    """Increment a named in-process metric (best-effort).

    This is intentionally lightweight and safe for hot paths.
    """
    try:
        if name not in _METRICS:
            # create it as a float counter if missing
            _METRICS[name] = 0
        _METRICS[name] += amount
    except Exception:
        pass


def record_decision_latency(ms: float) -> None:
    """Record a decision latency in milliseconds (aggregated).

    The hot-path should call this with a small float value. Prometheus
    metrics are updated if available.
    """
    try:
        _METRICS["decision_count"] += 1
        _METRICS["decision_total_ms"] += float(ms)
    except Exception:
        pass
    try:
        if _PROM_METRICS is not None:
            # prefer a Histogram if available
            prom_hist = _PROM_METRICS.get("decision_latency_ms")
            if prom_hist is not None:
                prom_hist.observe(float(ms))
            else:
                # fallback: increment counters
                c = _PROM_METRICS.get("decision_count")
                t = _PROM_METRICS.get("decision_total_ms")
                if c is not None:
                    c.inc()
                if t is not None:
                    t.inc(float(ms))
    except Exception:
        pass


def record_decision(decision: Dict) -> None:
    """Enqueue a decision for asynchronous auditing.

    This function returns quickly; the background writer flushes to disk.
    """
    # Fast-path: short-circuit when auditing is disabled to reduce hot-path cost
    try:
        if not _AUDIT_ENABLED:
            return
    except Exception:
        # If for some reason the flag is inaccessible, proceed with enqueueing
        pass

    # Sampling: if sample rate < 1.0, randomly skip some decisions
    try:
        if _AUDIT_SAMPLE_RATE < 1.0:
            if random.random() >= _AUDIT_SAMPLE_RATE:
                return
    except Exception:
        # On any sampling error, fall back to enqueueing
        pass

    # Enqueue the raw entry object; serialization is performed by the background writer.
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": decision
    }
    _enqueue_line(entry)


def set_audit_enabled(enabled: bool) -> None:
    """Enable or disable auditing at runtime. When disabled, calls to
    `record_decision` return immediately and do not enqueue work.
    """
    global _AUDIT_ENABLED
    _AUDIT_ENABLED = bool(enabled)


def is_audit_enabled() -> bool:
    return bool(_AUDIT_ENABLED)


def _flush_queue_now():
    """Synchronously drain the queue and write all pending entries to disk.

    Used by tests and shutdown to guarantee persistence.
    """
    items = []
    while True:
        try:
            items.append(_AUDIT_QUEUE.get_nowait())
        except queue.Empty:
            break
    if not items:
        return
    try:
        start = datetime.now(timezone.utc)
        with _lock, open(LOG_PATH, "a", encoding="utf-8") as f:
            for item in items:
                try:
                    line = json.dumps(item, default=str)
                except Exception:
                    line = json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "decision": str(item)}, default=str)
                f.write(line + "\n")
        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000.0
        _METRICS["flushed_batches"] += 1
        _METRICS["last_flush_duration_ms"] = duration
    except Exception:
        pass


def get_audit_metrics() -> Dict[str, float]:
    """Return a snapshot of current audit metrics."""
    # shallow copy for thread-safety
    return dict(_METRICS)


def get_aggregated_metrics() -> Dict[str, float]:
    """Return aggregated metrics (including averages) useful for quick inspection.

    - decision_count: number of decision latency samples recorded
    - decision_total_ms: total decision latency in ms
    - decision_avg_ms: average decision latency (ms) or 0 if no samples
    - org_cache_hits/misses/graph_lookups as-is
    """
    m = get_audit_metrics()
    dc = float(m.get("decision_count", 0))
    dt = float(m.get("decision_total_ms", 0.0))
    avg = (dt / dc) if dc > 0 else 0.0
    return {
        "decision_count": dc,
        "decision_total_ms": dt,
        "decision_avg_ms": avg,
        "org_cache_hits": float(m.get("org_cache_hits", 0)),
        "org_cache_misses": float(m.get("org_cache_misses", 0)),
        "org_graph_lookups": float(m.get("org_graph_lookups", 0)),
    }


def reset_audit_metrics() -> None:
    """Reset metrics counters (useful for tests)."""
    _METRICS["enqueued_count"] = 0
    _METRICS["dropped_count"] = 0
    _METRICS["flushed_batches"] = 0
    _METRICS["last_flush_duration_ms"] = 0.0
    _METRICS["decision_count"] = 0
    _METRICS["decision_total_ms"] = 0.0
    _METRICS["org_cache_hits"] = 0
    _METRICS["org_cache_misses"] = 0
    _METRICS["org_graph_lookups"] = 0


# Optional Prometheus integration
_PROM_METRICS = None
try:
    from prometheus_client import Counter, Gauge, Histogram

    # create Prometheus metric placeholders
    _PROM_METRICS = {
        "enqueued_count": Counter("temporal_audit_enqueued_total", "Audit lines enqueued"),
        "dropped_count": Counter("temporal_audit_dropped_total", "Audit lines dropped due to backpressure"),
        "flushed_batches": Counter("temporal_audit_flushed_batches_total", "Number of flush batches written to disk"),
        "last_flush_duration_ms": Gauge("temporal_audit_last_flush_duration_ms", "Last flush duration in ms"),
        # histogram for decision latency in milliseconds
        "decision_latency_ms": Histogram("temporal_audit_decision_latency_ms", "Decision latency in ms")
    }
except Exception:
    _PROM_METRICS = None


def enable_prometheus_metrics(registry=None) -> bool:
    """Optional helper to (re)register Prometheus metrics if `prometheus_client` is available.

    Returns True if metrics are enabled, False otherwise.
    If a custom registry is provided, metrics will be registered there.
    """
    global _PROM_METRICS
    try:
        from prometheus_client import Counter, Gauge, CollectorRegistry
        reg = registry if registry is not None else None
        # Recreate metrics in the given registry if provided
        if reg is not None and not isinstance(reg, CollectorRegistry):
            # ignore invalid registry
            reg = None

        _PROM_METRICS = {
            "enqueued_count": Counter("temporal_audit_enqueued_total", "Audit lines enqueued", registry=reg),
            "dropped_count": Counter("temporal_audit_dropped_total", "Audit lines dropped due to backpressure", registry=reg),
            "flushed_batches": Counter("temporal_audit_flushed_batches_total", "Number of flush batches written to disk", registry=reg),
            "last_flush_duration_ms": Gauge("temporal_audit_last_flush_duration_ms", "Last flush duration in ms", registry=reg),
            "decision_latency_ms": Histogram("temporal_audit_decision_latency_ms", "Decision latency in ms", registry=reg)
        }
        return True
    except Exception:
        _PROM_METRICS = None
        return False


def read_entries() -> List[Dict]:
    # Ensure pending entries are flushed before reading
    _flush_queue_now()
    with _lock:
        if not LOG_PATH.exists():
            return []
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
    entries = [json.loads(l) for l in lines]
    return entries


def read_last_entry() -> Dict:
    entries = read_entries()
    return entries[-1] if entries else None


def clear_log() -> None:
    # Flush and clear
    _flush_queue_now()
    with _lock:
        if LOG_PATH.exists():
            try:
                LOG_PATH.unlink()
            except Exception:
                pass


def _shutdown():
    """Graceful shutdown for the background writer: flush remaining items."""
    _flush_queue_now()
    _STOP_EVENT.set()
    try:
        _WRITER_THREAD.join(timeout=1.0)
    except Exception:
        pass


atexit.register(_shutdown)
