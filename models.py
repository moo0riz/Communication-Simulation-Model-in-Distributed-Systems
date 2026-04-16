from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Node:
    name: str
    kind: str
    x: int
    y: int


@dataclass
class MessageToken:
    msg_id: str
    model: str
    src: str
    dst: str
    payload: str
    created_at: float
    hop_started_at: float
    hop_latency_ms: int
    color: str
    item_id: int
    t: float = 0.0
    duration_ms: int = 600
