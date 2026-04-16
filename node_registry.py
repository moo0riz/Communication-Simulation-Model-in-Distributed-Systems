from __future__ import annotations

from typing import Dict, Optional

from models import Node


def build_nodes_by_view() -> Dict[str, Dict[str, Node]]:
    return {
        "RR": {
            "rr_client": Node("RR Client", "client", 380, 260),
            "rr_server": Node("RR Server", "server", 620, 260),
        },
        "RPC": {
            "rpc_client": Node("RPC Client", "client", 230, 260),
            "rpc_cstub": Node("Client Stub", "stub", 340, 260),
            "rpc_runtime_c": Node("RPC Runtime", "runtime", 450, 260),
            "rpc_runtime_s": Node("RPC Runtime", "runtime", 560, 260),
            "rpc_sstub": Node("Server Stub", "stub", 670, 260),
            "rpc_server": Node("RPC Server", "server", 780, 260),
        },
        "PUBSUB": {
            "publisher": Node("Publisher", "publisher", 180, 260),
            "broker": Node("Broker", "broker", 520, 260),
            "sub1": Node("Sub A", "subscriber", 860, 170),
            "sub2": Node("Sub B", "subscriber", 860, 260),
            "sub3": Node("Sub C", "subscriber", 860, 350),
        },
    }


def all_nodes(nodes_by_view: Dict[str, Dict[str, Node]]) -> Dict[str, Node]:
    out: Dict[str, Node] = {}
    for nodes in nodes_by_view.values():
        out.update(nodes)
    return out


def try_get_node(
    *,
    key: str,
    active_nodes: Dict[str, Node],
    nodes_by_view: Dict[str, Dict[str, Node]],
) -> Optional[Node]:
    if key in active_nodes:
        return active_nodes[key]
    for nodes in nodes_by_view.values():
        if key in nodes:
            return nodes[key]
    return None
