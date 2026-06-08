import os
import time
from contextlib import contextmanager


def is_perf_log_enabled():
    value = os.environ.get("PERF_LOG_ENABLED", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


@contextmanager
def perf_timer(name, **fields):
    if not is_perf_log_enabled():
        yield
        return

    started_at = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        field_text = " ".join(f"{key}={value}" for key, value in fields.items())
        suffix = f" {field_text}" if field_text else ""
        print(f"[perf] {name} elapsed_ms={elapsed_ms:.2f}{suffix}")
