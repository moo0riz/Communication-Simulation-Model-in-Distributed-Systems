from __future__ import annotations

import time
from typing import List


class Metrics:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.total_sent = 0
        self.total_delivered = 0
        self.total_dropped = 0
        self.latencies_ms: List[float] = []
        self.start_time = time.time()

    def record_latency(self, ms: float) -> None:
        self.latencies_ms.append(ms)

    @property
    def avg_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return sum(self.latencies_ms) / len(self.latencies_ms)

    @property
    def throughput_per_s(self) -> float:
        elapsed = max(1e-6, time.time() - self.start_time)
        return self.total_delivered / elapsed
