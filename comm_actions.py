from __future__ import annotations

import time
from typing import Callable, Optional, Protocol


class HopSender(Protocol):
    def send_hop(
        self,
        *,
        model: str,
        src: str,
        dst: str,
        msg_id: str,
        payload: str,
        color: str,
        on_delivered: Optional[Callable[[], None]] = None,
        on_dropped: Optional[Callable[[], None]] = None,
    ) -> None: ...


class Logger(Protocol):
    def log(self, line: str) -> None: ...


class ViewController(Protocol):
    def set_view(self, view: str) -> None: ...


class AfterScheduler(Protocol):
    def after(self, ms: int, cb: Callable[[], None]): ...


class MetricsRecorder(Protocol):
    def record_latency(self, ms: float) -> None: ...


class RNG(Protocol):
    def randint(self, a: int, b: int) -> int: ...
    def random(self) -> float: ...
    def choice(self, seq): ...
    def uniform(self, a: float, b: float) -> float: ...


def rr_send(
    *,
    next_msg_id: Callable[[str], str],
    rng: RNG,
    log: Logger,
    scheduler: AfterScheduler,
    set_view: ViewController,
    send_hop: HopSender,
    rr_metrics: MetricsRecorder,
) -> None:
    req_id = next_msg_id("REQ")
    payload = f"GET /resource?id={rng.randint(1, 9)}"

    start = time.time()
    log.log(f"RR start {req_id}: client -> server ({payload})")

    def on_req_delivered() -> None:
        server_processing_ms = rng.randint(120, 320)

        def after_processing() -> None:
            resp_id = req_id.replace("REQ", "RESP")
            resp_payload = "200 OK"
            log.log(f"RR server processed {req_id}, send {resp_id}: server -> client")

            def on_resp_delivered() -> None:
                e2e_ms = (time.time() - start) * 1000.0
                rr_metrics.record_latency(e2e_ms)
                log.log(f"RR done {req_id}: e2e {e2e_ms:.0f} ms")

            send_hop(
                model="RR",
                src="rr_server",
                dst="rr_client",
                msg_id=resp_id,
                payload=resp_payload,
                color="#63B3ED",
                on_delivered=on_resp_delivered,
            )

        scheduler.after(server_processing_ms, after_processing)

    set_view.set_view("RR")

    send_hop(
        model="RR",
        src="rr_client",
        dst="rr_server",
        msg_id=req_id,
        payload=payload,
        color="#4FD1C5",
        on_delivered=on_req_delivered,
    )


def pubsub_publish(
    *,
    next_msg_id: Callable[[str], str],
    rng: RNG,
    log: Logger,
    set_view: ViewController,
    send_hop: HopSender,
    pubsub_metrics: MetricsRecorder,
    try_get_sub_name: Callable[[str], str],
) -> None:
    event_id = next_msg_id("EVT")
    topic = "temperature"
    value = round(rng.uniform(20.0, 34.0), 1)
    payload = f"topic={topic}, value={value}C"

    start = time.time()
    log.log(f"PUB publish {event_id}: publisher -> broker ({payload})")

    def on_to_broker() -> None:
        subs = ["sub1", "sub2", "sub3"]
        remaining = {s: True for s in subs}

        def one_done(sub_key: str) -> None:
            remaining.pop(sub_key, None)
            if not remaining:
                e2e_ms = (time.time() - start) * 1000.0
                pubsub_metrics.record_latency(e2e_ms)
                log.log(f"PUB event {event_id} finished fanout: e2e {e2e_ms:.0f} ms")

        for s in subs:
            fan_id = f"{event_id}->{try_get_sub_name(s)}"

            def delivered_cb(sub_key: str = s) -> None:
                log.log(f"PUB delivered {event_id} to {try_get_sub_name(sub_key)}")
                one_done(sub_key)

            def dropped_cb(sub_key: str = s) -> None:
                log.log(f"PUB drop {event_id} to {try_get_sub_name(sub_key)}")
                one_done(sub_key)

            send_hop(
                model="PUBSUB",
                src="broker",
                dst=s,
                msg_id=fan_id,
                payload=payload,
                color="#68D391",
                on_delivered=delivered_cb,
                on_dropped=dropped_cb,
            )

    set_view.set_view("PUBSUB")

    send_hop(
        model="PUBSUB",
        src="publisher",
        dst="broker",
        msg_id=event_id,
        payload=payload,
        color="#F6AD55",
        on_delivered=on_to_broker,
    )


def rpc_call(
    *,
    next_msg_id: Callable[[str], str],
    rng: RNG,
    log: Logger,
    scheduler: AfterScheduler,
    set_view: ViewController,
    send_hop: HopSender,
    rpc_metrics: MetricsRecorder,
) -> None:
    call_id = next_msg_id("RPC")
    method = rng.choice(["getUser", "getBalance", "createOrder", "ping"])
    args = f"id={rng.randint(1, 99)}"
    payload = f"{method}({args})"

    start = time.time()
    log.log(f"RPC call {call_id}: invoke {payload}")

    set_view.set_view("RPC")

    def on_call_arrived_server() -> None:
        server_exec_ms = rng.randint(150, 520)
        log.log(f"RPC server executing {payload} (exec={server_exec_ms} ms)")

        def after_exec() -> None:
            app_error_p = 0.15
            is_error = rng.random() < app_error_p
            ret_payload = "ERROR: Exception" if is_error else "OK"

            def on_return_done() -> None:
                e2e_ms = (time.time() - start) * 1000.0
                rpc_metrics.record_latency(e2e_ms)
                status = "ERROR" if is_error else "OK"
                log.log(
                    f"RPC done {call_id}: return {status} received, e2e {e2e_ms:.0f} ms"
                )

            send_hop(
                model="RPC",
                src="rpc_server",
                dst="rpc_sstub",
                msg_id=f"{call_id}-RET-1",
                payload=ret_payload,
                color="#FCA5A5" if is_error else "#F87171",
                on_delivered=lambda: send_hop(
                    model="RPC",
                    src="rpc_sstub",
                    dst="rpc_runtime_s",
                    msg_id=f"{call_id}-RET-2",
                    payload=ret_payload,
                    color="#FCA5A5" if is_error else "#F87171",
                    on_delivered=lambda: send_hop(
                        model="RPC",
                        src="rpc_runtime_s",
                        dst="rpc_runtime_c",
                        msg_id=f"{call_id}-RET-3",
                        payload=ret_payload,
                        color="#FCA5A5" if is_error else "#F87171",
                        on_delivered=lambda: send_hop(
                            model="RPC",
                            src="rpc_runtime_c",
                            dst="rpc_cstub",
                            msg_id=f"{call_id}-RET-4",
                            payload=ret_payload,
                            color="#FCA5A5" if is_error else "#F87171",
                            on_delivered=lambda: send_hop(
                                model="RPC",
                                src="rpc_cstub",
                                dst="rpc_client",
                                msg_id=f"{call_id}-RET-5",
                                payload=ret_payload,
                                color="#FCA5A5" if is_error else "#F87171",
                                on_delivered=on_return_done,
                            ),
                        ),
                    ),
                ),
            )

        scheduler.after(server_exec_ms, after_exec)

    send_hop(
        model="RPC",
        src="rpc_client",
        dst="rpc_cstub",
        msg_id=f"{call_id}-CALL-1",
        payload=payload,
        color="#FB7185",
        on_delivered=lambda: send_hop(
            model="RPC",
            src="rpc_cstub",
            dst="rpc_runtime_c",
            msg_id=f"{call_id}-CALL-2",
            payload=payload,
            color="#FB7185",
            on_delivered=lambda: send_hop(
                model="RPC",
                src="rpc_runtime_c",
                dst="rpc_runtime_s",
                msg_id=f"{call_id}-CALL-3",
                payload=payload,
                color="#FB7185",
                on_delivered=lambda: send_hop(
                    model="RPC",
                    src="rpc_runtime_s",
                    dst="rpc_sstub",
                    msg_id=f"{call_id}-CALL-4",
                    payload=payload,
                    color="#FB7185",
                    on_delivered=lambda: send_hop(
                        model="RPC",
                        src="rpc_sstub",
                        dst="rpc_server",
                        msg_id=f"{call_id}-CALL-5",
                        payload=payload,
                        color="#FB7185",
                        on_delivered=on_call_arrived_server,
                    ),
                ),
            ),
        ),
    )
