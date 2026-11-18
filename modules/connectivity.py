import re
import shutil
from utils.config import (
    DEFAULT_PING_COUNT,
    DEFAULT_PING_TIMEOUT,
    DEFAULT_TRACEROUTE_MAX_HOPS,
)
from utils.helpers import run_command


def run_ping(target_ip: str, count: int = DEFAULT_PING_COUNT, timeout_per_packet: int = DEFAULT_PING_TIMEOUT) -> dict:
    # Use -6 for IPv6 addresses, -4 for IPv4
    ip_flag = "-6" if ":" in target_ip else "-4"
    cmd = ["ping", ip_flag, "-c", str(count), "-W", str(timeout_per_packet), target_ip]

    # Note: ping exits with return code 1 when 100% packet loss occurs, so we handle both True/False
    total_timeout = (count * timeout_per_packet) + 3
    success, output = run_command(cmd, timeout=total_timeout)

    # Extract transmitted, received, and packet loss %
    # Example line: "4 packets transmitted, 4 received, 0% packet loss, time 3004ms"
    stats_match = re.search(
        r"(\d+)\s+packets transmitted,\s+(\d+)\s+received.*?(\d+(?:\.\d+)?)%\s+packet loss",
        output,
    )

    if not stats_match:
        return {
            "reachable": False,
            "packets_transmitted": count,
            "packets_received": 0,
            "packet_loss_percent": 100.0,
            "min_ms": None,
            "avg_ms": None,
            "max_ms": None,
            "jitter_ms": None,
            "error": output if not success else "Unable to parse ping output.",
        }

    transmitted = int(stats_match.group(1))
    received = int(stats_match.group(2))
    loss_pct = float(stats_match.group(3))

    # Extract rtt min/avg/max/mdev
    # Example line: "rtt min/avg/max/mdev = 14.123/16.456/19.789/2.110 ms"
    rtt_match = re.search(
        r"(?:rtt|round-trip)\s+min/avg/max/(?:mdev|stddev)\s+=\s+([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)\s*ms",
        output,
    )

    if rtt_match:
        min_ms = round(float(rtt_match.group(1)), 2)
        avg_ms = round(float(rtt_match.group(2)), 2)
        max_ms = round(float(rtt_match.group(3)), 2)
        jitter_ms = round(float(rtt_match.group(4)), 2)
    else:
        min_ms = avg_ms = max_ms = jitter_ms = None

    reachable = received > 0
    error = None if reachable else f"100% packet loss to {target_ip} (ICMP blocked or host down)."

    return {
        "reachable": reachable,
        "packets_transmitted": transmitted,
        "packets_received": received,
        "packet_loss_percent": loss_pct,
        "min_ms": min_ms,
        "avg_ms": avg_ms,
        "max_ms": max_ms,
        "jitter_ms": jitter_ms,
        "error": error,
    }


def run_traceroute(target_ip: str, max_hops: int = DEFAULT_TRACEROUTE_MAX_HOPS) -> dict:
    # Prefer traceroute -n (numeric IPs, skips slow reverse DNS); fallback to tracepath -n
    if shutil.which("traceroute"):
        ip_flag = "-6" if ":" in target_ip else "-4"
        cmd = ["traceroute", ip_flag, "-n", "-m", str(max_hops), "-w", "1", "-q", "1", target_ip]
        tool_used = "traceroute"
    elif shutil.which("tracepath"):
        ip_flag = "-6" if ":" in target_ip else "-4"
        cmd = ["tracepath", ip_flag, "-n", "-m", str(max_hops), target_ip]
        tool_used = "tracepath"
    else:
        return {
            "tool": None,
            "total_hops": 0,
            "hops": [],
            "error": "Neither 'traceroute' nor 'tracepath' is installed on this system.",
        }

    success, output = run_command(cmd, timeout=max_hops + 10)
    if not success and not output:
        return {
            "tool": tool_used,
            "total_hops": 0,
            "hops": [],
            "error": "Traceroute execution failed.",
        }

    hops = []
    for line in output.splitlines():
        line = line.strip()
        # Match hop number at the start of the line (e.g., "1  172.27.32.1  0.412 ms" or "3  * * *")
        hop_match = re.match(r"^(\d+):?\s+(.*)$", line)
        if not hop_match:
            continue

        hop_num = int(hop_match.group(1))
        rest = hop_match.group(2)

        if "*" in rest and not re.search(r"\d+\.\d+\.\d+\.\d+|[0-9a-fA-F:]{4,}", rest):
            hops.append({
                "hop": hop_num,
                "ip": "*",
                "rtt_ms": None,
                "status": "TIMEOUT",
            })
            continue

        # Extract IP (IPv4 or IPv6) and first RTT value in ms
        ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+|[0-9a-fA-F:]+:[0-9a-fA-F:]+)", rest)
        rtt_match = re.search(r"([\d.]+)\s*ms", rest)

        hops.append({
            "hop": hop_num,
            "ip": ip_match.group(1) if ip_match else "UNKNOWN",
            "rtt_ms": round(float(rtt_match.group(1)), 2) if rtt_match else None,
            "status": "OK",
        })

    return {
        "tool": tool_used,
        "total_hops": len(hops),
        "hops": hops,
        "error": None if hops else "No hops parsed from traceroute output.",
    }


def run_connectivity_diagnostics(resolved_ips: list[str], include_trace: bool = True) -> dict:
    if not resolved_ips:
        return {
            "module": "connectivity",
            "status": "SKIPPED",
            "data": {},
            "error": "No target IP addresses available from DNS stage.",
        }

    target_ip = resolved_ips[0]
    ping_data = run_ping(target_ip)
    trace_data = run_traceroute(target_ip) if include_trace else None

    # Determine overall module status
    if not ping_data["reachable"]:
        status = "FAIL"
        error = ping_data["error"]
    elif ping_data["packet_loss_percent"] > 0:
        status = "WARN"
        error = f"Intermittent packet loss detected ({ping_data['packet_loss_percent']}%)."
    else:
        status = "PASS"
        error = None

    return {
        "module": "connectivity",
        "status": status,
        "data": {
            "tested_ip": target_ip,
            "ping": ping_data,
            "traceroute": trace_data,
        },
        "error": error,
    }