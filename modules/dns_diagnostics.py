import socket
import time
from utils.helpers import is_ip_address, run_command

def resolve_host_addresses(domain: str) -> dict:
    start_time = time.perf_counter()
    try:
        # AF_UNSPEC fetches both IPv4 (AF_INET) and IPv6 (AF_INET6)
        addr_info = socket.getaddrinfo(domain, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        ipv4_addresses = sorted({
            info[4][0] for info in addr_info if info[0] == socket.AF_INET
        })
        ipv6_addresses = sorted({
            info[4][0] for info in addr_info if info[0] == socket.AF_INET6
        })

        return {
            "success": True,
            "ipv4": ipv4_addresses,
            "ipv6": ipv6_addresses,
            "latency_ms": elapsed_ms,
            "error": None
        }
    except socket.gaierror as e:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        error_map = {
            socket.EAI_NONAME: f"NXDOMAIN or invalid hostname: '{domain}' could not be resolved.",
            socket.EAI_AGAIN: f"Temporary DNS failure (SERVFAIL / timeout) resolving '{domain}'.",
            socket.EAI_NODATA: f"Valid domain '{domain}', but no A/AAAA records found."
        }
        reason = error_map.get(e.errno, f"DNS resolution error ({e.errno}): {e.strerror}")
        return {
            "success": False,
            "ipv4": [],
            "ipv6": [],
            "latency_ms": elapsed_ms,
            "error": reason
        }

def query_dns_records(domain: str) -> dict:
    record_types = ["CNAME", "MX", "NS", "TXT"]
    records = {}

    for rtype in record_types:
        success, output = run_command(["dig", "+short", domain, rtype], timeout=4)
        if success and output:
            records[rtype] = [line.strip() for line in output.splitlines() if line.strip()]
        else:
            records[rtype] = []

    return records

def run_dns_diagnostics(target: str) -> dict:
    target = target.strip()

    # If user supplied a raw IP address, DNS lookup is unnecessary
    if is_ip_address(target):
        return {
            "module": "dns_diagnostics",
            "status": "SKIPPED",
            "data": {
                "target": target,
                "is_ip": True,
                "ipv4": [target] if ":" not in target else [],
                "ipv6": [target] if ":" in target else [],
                "latency_ms": 0.0,
                "records": {}
            },
            "error": None
        }

    resolution = resolve_host_addresses(target)
    if not resolution["success"]:
        return {
            "module": "dns_diagnostics",
            "status": "FAIL",
            "data": {
                "target": target,
                "is_ip": False,
                "ipv4": [],
                "ipv6": [],
                "latency_ms": resolution["latency_ms"],
                "records": {}
            },
            "error": resolution["error"]
        }

    records = query_dns_records(target)

    return {
        "module": "dns_diagnostics",
        "status": "PASS",
        "data": {
            "target": target,
            "is_ip": False,
            "ipv4": resolution["ipv4"],
            "ipv6": resolution["ipv6"],
            "latency_ms": resolution["latency_ms"],
            "records": records
        },
        "error": None
    }