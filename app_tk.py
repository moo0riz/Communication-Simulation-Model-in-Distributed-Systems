from __future__ import annotations

import math
import random
import time
from typing import Callable, Dict, List, Optional

import tkinter as tk
from tkinter import ttk

from comm_actions import pubsub_publish, rpc_call, rr_send
from metrics import Metrics
from models import MessageToken, Node
from node_registry import build_nodes_by_view, try_get_node


class DistributedCommsSimulator(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Simulasi Model Komunikasi Terdistribusi (RR vs PubSub vs RPC)")
        self.geometry("1100x720")
        self.minsize(900, 620)

        self._rng = random.Random()
        self._msg_counter = 0
        self._active_tokens: Dict[int, MessageToken] = {}
        self._order_log: List[str] = []

        self._metrics: Dict[str, Metrics] = {
            "RR": Metrics(),
            "PUBSUB": Metrics(),
            "RPC": Metrics(),
        }

        self._auto_job: Optional[str] = None

        self._active_view = "RR"
        self._nodes_by_view: Dict[str, Dict[str, Node]] = build_nodes_by_view()
        self.nodes: Dict[str, Node] = dict(self._nodes_by_view[self._active_view])

        self.latency_var = tk.IntVar(value=250)
        self.loss_var = tk.IntVar(value=10)
        self.rate_var = tk.IntVar(value=2)
        self.auto_var = tk.BooleanVar(value=False)

        self._build_layout()
        self._render_static_scene()
        self._refresh_ui()
        self._tick()

    # ---- ViewController / Logger adapter ----

    def set_view(self, view: str) -> None:
        self._active_view = view
        if view in self._nodes_by_view:
            self.nodes = dict(self._nodes_by_view[view])
        self._render_static_scene()

    def log(self, line: str) -> None:
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {line}"
        self._order_log.append(entry)
        if len(self._order_log) > 300:
            self._order_log = self._order_log[-300:]

        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.insert(tk.END, "\n".join(self._order_log) + "\n")
        self.log_text.configure(state=tk.DISABLED)
        self.log_text.see(tk.END)

    # ---- UI ----

    def _build_layout(self) -> None:
        root = ttk.Frame(self)
        root.pack(fill=tk.BOTH, expand=True)

        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        self.left = ttk.Frame(root, padding=8)
        self.left.grid(row=0, column=0, sticky="ns", padx=(0, 6))

        self.right = ttk.Frame(root, padding=8)
        self.right.grid(row=0, column=1, sticky="nsew")
        self.right.columnconfigure(0, weight=1)
        self.right.rowconfigure(0, weight=1)

        self.tabs = ttk.Notebook(self.right)
        self.tabs.grid(row=0, column=0, sticky="nsew")

        self.main_tab = ttk.Frame(self.tabs)
        self.compare_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.main_tab, text="Simulasi")
        self.tabs.add(self.compare_tab, text="Perbandingan")

        self.main_tab.columnconfigure(0, weight=1)
        self.main_tab.rowconfigure(0, weight=1)
        self.main_tab.rowconfigure(1, weight=0)

        self.compare_tab.columnconfigure(0, weight=1)
        self.compare_tab.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.main_tab, bg="#0b1020", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        log_frame = ttk.Frame(self.main_tab)
        log_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)

        ttk.Label(log_frame, text="Order log (urutan pesan / event):").grid(
            row=0, column=0, sticky="w"
        )

        self.log_text = tk.Text(
            log_frame,
            height=8,
            wrap=tk.NONE,
            bg="#0a0f1e",
            fg="#d6deff",
            insertbackground="#d6deff",
        )
        self.log_text.grid(row=1, column=0, sticky="ew")
        self.log_text.configure(state=tk.DISABLED)

        self.compare_text = tk.Text(
            self.compare_tab,
            wrap=tk.WORD,
            bg="#0a0f1e",
            fg="#d6deff",
            insertbackground="#d6deff",
        )
        self.compare_text.grid(row=0, column=0, sticky="nsew")
        self.compare_text.configure(state=tk.DISABLED)

        ttk.Label(self.left, text="Kontrol Simulasi", font=("Helvetica", 14, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        action_box = ttk.LabelFrame(self.left, text="Aksi")
        action_box.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(action_box, text="Jalankan RR (Send Request)", command=self._rr_send).pack(
            fill=tk.X, padx=8, pady=4
        )
        ttk.Button(
            action_box,
            text="Jalankan PubSub (Publish Event)",
            command=self._pubsub_publish,
        ).pack(fill=tk.X, padx=8, pady=4)
        ttk.Button(action_box, text="Jalankan RPC (Remote Call)", command=self._rpc_call).pack(
            fill=tk.X, padx=8, pady=4
        )

        ttk.Separator(action_box).pack(fill=tk.X, padx=8, pady=6)
        ttk.Button(action_box, text="Reset metrik & log", command=self._reset).pack(
            fill=tk.X, padx=8, pady=(0, 8)
        )

        sim_box = ttk.LabelFrame(self.left, text="Parameter Jaringan")
        sim_box.pack(fill=tk.X, pady=(0, 10))

        latency_row = ttk.Frame(sim_box)
        latency_row.pack(fill=tk.X, padx=8, pady=(6, 0))
        ttk.Label(latency_row, text="Latency per hop (ms)").pack(side=tk.LEFT)
        self.latency_value_lbl = ttk.Label(latency_row, text=f"{int(self.latency_var.get())} ms")
        self.latency_value_lbl.pack(side=tk.RIGHT)

        ttk.Scale(
            sim_box,
            from_=0,
            to=1500,
            variable=self.latency_var,
            command=lambda _v: self._refresh_ui(),
        ).pack(fill=tk.X, padx=8, pady=(0, 6))

        loss_row = ttk.Frame(sim_box)
        loss_row.pack(fill=tk.X, padx=8, pady=(6, 0))
        ttk.Label(loss_row, text="Loss per hop (%)").pack(side=tk.LEFT)
        self.loss_value_lbl = ttk.Label(loss_row, text=f"{int(self.loss_var.get())}%")
        self.loss_value_lbl.pack(side=tk.RIGHT)

        ttk.Scale(
            sim_box,
            from_=0,
            to=60,
            variable=self.loss_var,
            command=lambda _v: self._refresh_ui(),
        ).pack(fill=tk.X, padx=8, pady=(0, 6))

        pub_box = ttk.LabelFrame(self.left, text="PubSub (Auto)")
        pub_box.pack(fill=tk.X, pady=(0, 10))

        ttk.Checkbutton(
            pub_box,
            text="Auto run (publish berkala)",
            variable=self.auto_var,
            command=self._toggle_auto,
        ).pack(anchor="w", padx=8, pady=(6, 4))

        rate_row = ttk.Frame(pub_box)
        rate_row.pack(fill=tk.X, padx=8, pady=(0, 0))
        ttk.Label(rate_row, text="Rate (event/detik)").pack(side=tk.LEFT)
        self.rate_value_lbl = ttk.Label(rate_row, text=f"{int(self.rate_var.get())}/s")
        self.rate_value_lbl.pack(side=tk.RIGHT)

        ttk.Scale(
            pub_box,
            from_=1,
            to=10,
            variable=self.rate_var,
            command=lambda _v: self._refresh_ui(),
        ).pack(fill=tk.X, padx=8, pady=(0, 6))

        met_box = ttk.LabelFrame(self.left, text="Metrik (Model Aktif)")
        met_box.pack(fill=tk.X, pady=(0, 10))

        self.metrics_lbl = ttk.Label(met_box, justify=tk.LEFT)
        self.metrics_lbl.pack(anchor="w", padx=8, pady=8)

    # ---- Static scene ----

    def _render_static_scene(self) -> None:
        self.canvas.delete("all")

        view = self._active_view

        if view == "RR":
            self._draw_link("rr_client", "rr_server", tag="rr_link")
        elif view == "RPC":
            self._draw_link("rpc_client", "rpc_cstub", tag="rpc_link")
            self._draw_link("rpc_cstub", "rpc_runtime_c", tag="rpc_link")
            self._draw_link("rpc_runtime_c", "rpc_runtime_s", tag="rpc_link")
            self._draw_link("rpc_runtime_s", "rpc_sstub", tag="rpc_link")
            self._draw_link("rpc_sstub", "rpc_server", tag="rpc_link")
        elif view == "PUBSUB":
            self._draw_link("publisher", "broker", tag="pub_link")
            for s in ("sub1", "sub2", "sub3"):
                self._draw_link("broker", s, tag="pub_link")

        for key, node in self.nodes.items():
            self._draw_node(key, node)

        self.canvas.create_text(
            20,
            20,
            anchor="w",
            text=f"Visualisasi Sistem (topologi: {view})",
            fill="#d6deff",
            font=("Helvetica", 13, "bold"),
        )

    def _draw_link(self, a: str, b: str, tag: str) -> None:
        na = try_get_node(key=a, active_nodes=self.nodes, nodes_by_view=self._nodes_by_view)
        nb = try_get_node(key=b, active_nodes=self.nodes, nodes_by_view=self._nodes_by_view)
        if na is None or nb is None:
            return
        self.canvas.create_line(
            na.x,
            na.y,
            nb.x,
            nb.y,
            fill="#2a355c",
            width=3,
            capstyle=tk.ROUND,
            tags=(tag,),
        )

    def _draw_node(self, key: str, node: Node) -> None:
        r = 34
        color = {
            "client": "#4FD1C5",
            "server": "#63B3ED",
            "stub": "#FDE68A",
            "runtime": "#93C5FD",
            "publisher": "#F6AD55",
            "broker": "#B794F4",
            "subscriber": "#68D391",
        }.get(node.kind, "#CBD5E0")

        self.canvas.create_oval(
            node.x - r,
            node.y - r,
            node.x + r,
            node.y + r,
            fill=color,
            outline="#0a0f1e",
            width=2,
            tags=(f"node:{key}",),
        )
        self.canvas.create_text(
            node.x,
            node.y,
            text=node.name,
            fill="#0a0f1e",
            font=("Helvetica", 11, "bold"),
            tags=(f"node:{key}",),
        )

    # ---- Actions wiring ----

    def _rr_send(self) -> None:
        rr_send(
            next_msg_id=self._next_msg_id,
            rng=self._rng,
            log=self,
            scheduler=self,
            set_view=self,
            send_hop=self.send_hop,
            rr_metrics=self._metrics["RR"],
        )

    def _pubsub_publish(self) -> None:
        pubsub_publish(
            next_msg_id=self._next_msg_id,
            rng=self._rng,
            log=self,
            set_view=self,
            send_hop=self.send_hop,
            pubsub_metrics=self._metrics["PUBSUB"],
            try_get_sub_name=self._sub_name,
        )

    def _rpc_call(self) -> None:
        rpc_call(
            next_msg_id=self._next_msg_id,
            rng=self._rng,
            log=self,
            scheduler=self,
            set_view=self,
            send_hop=self.send_hop,
            rpc_metrics=self._metrics["RPC"],
        )

    def _sub_name(self, key: str) -> str:
        n = try_get_node(key=key, active_nodes=self.nodes, nodes_by_view=self._nodes_by_view)
        return n.name if n is not None else key

    # ---- Hop + animation ----

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
    ) -> None:
        latency_ms = int(self.latency_var.get())
        loss_p = float(self.loss_var.get()) / 100.0

        self._metrics[model].total_sent += 1

        src_node = try_get_node(key=src, active_nodes=self.nodes, nodes_by_view=self._nodes_by_view)
        dst_node = try_get_node(key=dst, active_nodes=self.nodes, nodes_by_view=self._nodes_by_view)
        src_name = src_node.name if src_node is not None else src
        dst_name = dst_node.name if dst_node is not None else dst
        self.log(f"send[{model}] {msg_id}: {src_name} -> {dst_name} (lat={latency_ms}ms)")

        dropped = self._rng.random() < loss_p

        item = self._create_message_bubble(src, color)

        token = MessageToken(
            msg_id=msg_id,
            model=model,
            src=src,
            dst=dst,
            payload=payload,
            created_at=time.time(),
            hop_started_at=time.time(),
            hop_latency_ms=latency_ms,
            color=color,
            item_id=item,
            duration_ms=max(220, int(0.6 * latency_ms) + 350),
        )
        self._active_tokens[item] = token

        def finish() -> None:
            if item not in self._active_tokens:
                return

            self._active_tokens.pop(item, None)
            self.canvas.delete(item)

            if dropped:
                self._metrics[model].total_dropped += 1
                self.log(f"drop[{model}] {msg_id}: {src_name} -> {dst_name}")
                if on_dropped is not None:
                    on_dropped()
                self._refresh_ui()
                return

            self._metrics[model].total_delivered += 1
            self.log(f"deliver[{model}] {msg_id}: {dst_name} received ({payload})")
            if on_delivered is not None:
                on_delivered()
            self._refresh_ui()

        self.after(latency_ms, finish)

    def _create_message_bubble(self, src: str, color: str) -> int:
        n = try_get_node(key=src, active_nodes=self.nodes, nodes_by_view=self._nodes_by_view)
        if n is None:
            n = Node(src, "unknown", 30, 30)
        r = 8
        return self.canvas.create_oval(
            n.x - r,
            n.y - r,
            n.x + r,
            n.y + r,
            fill=color,
            outline="#0a0f1e",
            width=1,
        )

    def _tick(self) -> None:
        now = time.time()

        for item_id, token in list(self._active_tokens.items()):
            src = try_get_node(key=token.src, active_nodes=self.nodes, nodes_by_view=self._nodes_by_view)
            dst = try_get_node(key=token.dst, active_nodes=self.nodes, nodes_by_view=self._nodes_by_view)
            if src is None or dst is None:
                continue

            elapsed_ms = (now - token.hop_started_at) * 1000.0
            t = min(1.0, max(0.0, elapsed_ms / max(1.0, float(token.hop_latency_ms))))

            eased = 0.5 - 0.5 * math.cos(math.pi * t)
            x = int(src.x + (dst.x - src.x) * eased)
            y = int(src.y + (dst.y - src.y) * eased)

            r = 10
            self.canvas.coords(item_id, x - r, y - r, x + r, y + r)

        self._refresh_ui(silent=True)
        self.after(33, self._tick)

    # ---- Refresh + reset ----

    def _refresh_ui(self, silent: bool = False) -> None:
        rr = self._metrics["RR"]
        ps = self._metrics["PUBSUB"]
        rpc = self._metrics["RPC"]

        def success_rate(m: Metrics) -> float:
            if m.total_sent <= 0:
                return 0.0
            return 100.0 * (m.total_delivered / m.total_sent)

        text = (
            "Metrik (RR + PubSub + RPC)\n"
            f"Latency/hop: {int(self.latency_var.get())} ms\n"
            f"Loss/hop: {int(self.loss_var.get())}%\n"
            "\n"
            f"RR   - Sent: {rr.total_sent}, Delivered: {rr.total_delivered}, Dropped: {rr.total_dropped}"
            f"  (Success: {success_rate(rr):.1f}%)\n"
            f"RR   - Avg latency (e2e): {rr.avg_latency_ms:.0f} ms, Throughput: {rr.throughput_per_s:.2f}/s\n"
            "\n"
            f"PS   - Sent: {ps.total_sent}, Delivered: {ps.total_delivered}, Dropped: {ps.total_dropped}"
            f"  (Success: {success_rate(ps):.1f}%)\n"
            f"PS   - Avg latency (e2e): {ps.avg_latency_ms:.0f} ms, Throughput: {ps.throughput_per_s:.2f}/s\n"
            "\n"
            f"RPC  - Sent: {rpc.total_sent}, Delivered: {rpc.total_delivered}, Dropped: {rpc.total_dropped}"
            f"  (Success: {success_rate(rpc):.1f}%)\n"
            f"RPC  - Avg latency (e2e): {rpc.avg_latency_ms:.0f} ms, Throughput: {rpc.throughput_per_s:.2f}/s\n"
        )
        self.metrics_lbl.configure(text=text)

        def _pad(s: str, w: int) -> str:
            return (s + " " * w)[:w]

        headers = [
            ("Model", 6),
            ("Sent", 8),
            ("Deliv", 8),
            ("Drop", 8),
            ("Succ%", 7),
            ("AvgE2E(ms)", 12),
            ("Thr(/s)", 9),
        ]

        def row(model: str, m: Metrics, avg_ms: float) -> str:
            return "| " + " | ".join(
                [
                    _pad(model, 6),
                    _pad(str(m.total_sent), 8),
                    _pad(str(m.total_delivered), 8),
                    _pad(str(m.total_dropped), 8),
                    _pad(f"{success_rate(m):.1f}", 7),
                    _pad(f"{avg_ms:.0f}", 12),
                    _pad(f"{m.throughput_per_s:.2f}", 9),
                ]
            ) + " |\n"

        sep = "+" + "+".join(["-" * (w + 2) for _h, w in headers]) + "+\n"
        head = "| " + " | ".join([_pad(h, w) for h, w in headers]) + " |\n"

        compare = (
            "Perbandingan Model (Tabel)\n"
            "==========================\n\n"
            + sep
            + head
            + sep
            + row("RR", rr, rr.avg_latency_ms)
            + row("RPC", rpc, rpc.avg_latency_ms)
            + row("PS", ps, ps.avg_latency_ms)
            + sep
            + "\n"
            "Keterangan\n"
            "- Sent/Deliv/Drop dihitung per-hop.\n"
            "- Succ% = delivered / sent * 100.\n"
            "- AvgE2E adalah rata-rata latency end-to-end.\n"
        )

        self.compare_text.configure(state=tk.NORMAL)
        self.compare_text.delete("1.0", tk.END)
        self.compare_text.insert(tk.END, compare)
        self.compare_text.configure(state=tk.DISABLED)

        self.latency_value_lbl.configure(text=f"{int(self.latency_var.get())} ms")
        self.loss_value_lbl.configure(text=f"{int(self.loss_var.get())}%")
        self.rate_value_lbl.configure(text=f"{int(self.rate_var.get())}/s")

        if not silent:
            self.update_idletasks()

    def _reset(self) -> None:
        self.auto_var.set(False)
        self._toggle_auto()

        for item_id in list(self._active_tokens.keys()):
            self.canvas.delete(item_id)
        self._active_tokens.clear()

        for m in self._metrics.values():
            m.reset()

        self._order_log.clear()
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

        self._refresh_ui()

    def _toggle_auto(self) -> None:
        if self._auto_job is not None:
            try:
                self.after_cancel(self._auto_job)
            except Exception:
                pass
            self._auto_job = None

        if not self.auto_var.get():
            return

        def loop() -> None:
            if not self.auto_var.get():
                return
            self._pubsub_publish()
            rate = max(1, int(self.rate_var.get()))
            interval_ms = int(1000 / rate)
            self._auto_job = self.after(interval_ms, loop)

        loop()

    def _next_msg_id(self, prefix: str) -> str:
        self._msg_counter += 1
        return f"{prefix}-{self._msg_counter:04d}"
