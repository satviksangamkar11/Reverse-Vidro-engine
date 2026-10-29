"""NVIDIA request scheduling with per-key rolling windows and a shared queue."""
from __future__ import annotations

import os
import queue
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = "nvidia/nemotron-3.5-super-vl-120b-a12b"


def load_env_keys(path: Path):
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                name, value = line.split("=", 1)
                values[name.strip()] = value.strip().strip('"\'')
    for i in range(1, 15):
        name = f"NVIDIA_API_KEY_{i:02d}"
        values[name] = os.getenv(name, values.get(name, ""))
    keys = [values[f"NVIDIA_API_KEY_{i:02d}"] for i in range(1, 15)]
    if any(not x for x in keys) or len(set(keys)) != 14:
        raise ValueError("Expected 14 distinct NVIDIA_API_KEY_01..14 values in .env or environment")
    return keys


class NvidiaScheduler:
    def __init__(self, keys, *, model=MODEL, reasoning_effort=None, read_timeout=300, per_key_limit=10, global_limit=10, window_seconds=60, workers=4, max_calls=20, clock=time.monotonic, sleep=time.sleep, post=requests.post):
        if not keys or per_key_limit < 1 or global_limit < 1 or window_seconds <= 0 or workers < 1 or max_calls < 0:
            raise ValueError("Invalid scheduler settings")
        self.keys = keys
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.read_timeout = read_timeout
        self.limit = per_key_limit
        self.global_limit = global_limit
        self.window = window_seconds
        self.workers = workers
        self.max_calls = max_calls
        self.clock = clock
        self.sleep = sleep
        self.post = post
        self.requests = [deque() for _ in keys]
        self.global_requests = deque()
        self.cooldown = [0.0] * len(keys)
        self.disabled = set()
        self.cursor = 0
        self.global_until = 0.0
        self.calls = 0
        self.completed = 0
        self.retries = 0
        self.errors = []
        self.lock = threading.Lock()

    def _choose_at(self, now):
        if now < self.global_until:
            return None, self.global_until - now
        while self.global_requests and self.global_requests[0] <= now - self.window:
            self.global_requests.popleft()
        if len(self.global_requests) >= self.global_limit:
            return None, self.global_requests[0] + self.window - now
        next_wait = float("inf")
        for offset in range(len(self.keys)):
            i = (self.cursor + offset) % len(self.keys)
            if i in self.disabled:
                continue
            q = self.requests[i]
            while q and q[0] <= now - self.window:
                q.popleft()
            ready = max(self.cooldown[i], q[0] + self.window if len(q) >= self.limit else now)
            if ready <= now:
                q.append(now)
                self.global_requests.append(now)
                self.cursor = (i + 1) % len(self.keys)
                return i, 0.0
            next_wait = min(next_wait, ready - now)
        return None, next_wait

    def acquire(self):
        while True:
            with self.lock:
                if self.calls >= self.max_calls:
                    return None
                i, wait = self._choose_at(self.clock())
                if i is not None:
                    self.calls += 1
                    return i
                if wait == float("inf"):
                    return None
            self.sleep(min(max(wait, 0.01), 1.0))

    def snapshot(self):
        with self.lock:
            now = self.clock()
            while self.global_requests and self.global_requests[0] <= now - self.window:
                self.global_requests.popleft()
            global_ready = max(self.global_until, self.global_requests[0] + self.window if len(self.global_requests) >= self.global_limit else now)
            available = cooling = 0
            waits = []
            for i in range(len(self.keys)):
                if i in self.disabled:
                    continue
                q = self.requests[i]
                ready = max(global_ready, self.cooldown[i], q[0] + self.window if len(q) >= self.limit else now)
                if ready <= now:
                    available += 1
                else:
                    cooling += 1; waits.append(ready - now)
            return {"completed_api_requests": self.completed, "http_attempts": self.calls, "available_keys": available, "cooling_keys": cooling, "disabled_keys": len(self.disabled), "next_eligible_seconds": round(min(waits), 1) if waits else 0, "retries": self.retries, "errors": list(self.errors[-5:])}

    @staticmethod
    def retry_after(header):
        if not header:
            return 60.0
        try:
            return max(0.0, float(header))
        except ValueError:
            try:
                return max(0.0, (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError):
                return 60.0

    def call(self, content, *, max_tokens=3500):
        payload = {"model": self.model, "messages": [{"role": "user", "content": content}], "temperature": 0.2, "max_tokens": max_tokens, "stream": False}
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        for attempt in range(3):
            i = self.acquire()
            if i is None:
                return {"status": "PENDING_BUDGET", "text": "", "usage": None}
            started = self.clock()
            try:
                response = self.post(URL, headers={"Authorization": f"Bearer {self.keys[i]}", "Content-Type": "application/json"}, json=payload, timeout=(15, self.read_timeout))
                latency = round(self.clock() - started, 2)
                if response.status_code == 429:
                    delay = self.retry_after(response.headers.get("Retry-After"))
                    with self.lock:
                        self.cooldown[i] = max(self.cooldown[i], self.clock() + delay)
                        # Scope is often ambiguous: pause the whole scheduler conservatively.
                        self.global_until = max(self.global_until, self.clock() + delay)
                        self.retries += 1
                    if attempt < 2:
                        continue
                    return {"status": "RATE_LIMITED", "text": "", "usage": None, "key_index": i + 1, "latency_sec": latency}
                if response.status_code in (401, 403):
                    with self.lock:
                        self.disabled.add(i)
                        self.errors.append(f"HTTP {response.status_code} on key slot {i + 1}")
                    return {"status": "AUTH_ERROR", "text": "", "usage": None, "key_index": i + 1, "http_status": response.status_code, "latency_sec": latency}
                if response.status_code == 402:
                    with self.lock:
                        self.disabled.update(range(len(self.keys)))
                        self.errors.append("HTTP 402 payment or credit restriction; scheduler stopped")
                    return {"status": "PAYMENT_RESTRICTION", "text": "", "usage": None, "key_index": i + 1, "http_status": 402, "latency_sec": latency}
                if 400 <= response.status_code < 500:
                    with self.lock:
                        self.errors.append(f"HTTP {response.status_code} request rejected")
                    return {"status": "CLIENT_ERROR", "text": "", "usage": None, "key_index": i + 1, "http_status": response.status_code, "latency_sec": latency}
                if 500 <= response.status_code <= 599:
                    with self.lock:
                        self.retries += 1
                    if attempt < 2:
                        self.sleep(min(8, 2 ** attempt * 2)); continue
                    return {"status": "SERVER_ERROR", "text": "", "usage": None, "key_index": i + 1, "http_status": response.status_code, "latency_sec": latency}
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"].get("content") or ""
                with self.lock:
                    self.completed += 1
                return {"status": "OK", "text": text, "usage": data.get("usage"), "key_index": i + 1, "latency_sec": latency, "http_status": response.status_code}
            except (requests.RequestException, ValueError, KeyError, IndexError) as e:
                with self.lock:
                    self.retries += 1
                    self.errors.append(f"{type(e).__name__} on key slot {i + 1}")
                if attempt < 2:
                    self.sleep(min(8, 2 ** attempt * 2)); continue
                return {"status": "ERROR", "text": "", "usage": None, "key_index": i + 1, "error": type(e).__name__}

    def run_jobs(self, jobs, on_result):
        pending = queue.Queue()
        for job in jobs:
            pending.put(job)
        def worker():
            while True:
                try:
                    job = pending.get_nowait()
                except queue.Empty:
                    return
                result = self.call(job["content"], max_tokens=job.get("max_tokens", 3500))
                on_result(job, result, self.snapshot())
                pending.task_done()
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = [executor.submit(worker) for _ in range(min(self.workers, len(jobs)))]
            for future in futures:
                future.result()
