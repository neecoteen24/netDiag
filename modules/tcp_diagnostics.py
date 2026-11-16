import socket
import time
from utils.config import DEFAULT_PORTS, DEFAULT_TIMEOUT

def test_tcp_port(ip: str, port: int, timeout: float = DEFAULT_TIMEOUT) -> dict:
    # Choose IPv6 or IPv4 address family dynamically based on IP format
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    start_time = time.perf_counter()

    try:
        # socket.create_connection is high-level; using raw socket() gives explicit control
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((ip, port))
            handshake_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return {
                "port": port,
                "protocol": "TCP",
                "state": "OPEN",
                "handshake_ms": handshake_ms,
                "error": None
            }

    except ConnectionRefusedError:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "port": port,
            "protocol": "TCP",
            "state": "CLOSED",
            "handshake_ms": elapsed_ms,
            "error": "Connection refused (Server actively returned TCP RST; service not listening)."
        }

    except socket.timeout:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "port": port,
            "protocol": "TCP",
            "state": "FILTERED_OR_TIMEOUT",
            "handshake_ms": elapsed_ms,
            "error": f"Connection timed out after {timeout}s (Packets dropped by firewall or host unreachable)."
        }

    except OSError as e:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "port": port,
            "protocol": "TCP",
            "state": "UNREACHABLE",
            "handshake_ms": elapsed_ms,
            "error": f"Network/Socket error ({e.errno}): {e.strerror}"
        }

def test_udp_probe(ip: str, port: int = 53, timeout: float = 2.0) -> dict:
    """
    Sends a minimal UDP datagram to observe connectionless behavior.
    Note: Absence of a reply in UDP does NOT prove the port is closed.
    """
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    start_time = time.perf_counter()

    try:
        with socket.socket(family, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            # Minimal valid-looking DNS header query payload for port 53, or generic ping bytes
            payload = b"\x00\x00\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x01" if port == 53 else b"NETDIAG_PROBE"
            sock.sendto(payload, (ip, port))
            data, _ = sock.recvfrom(512)
            rtt_ms = round((time.perf_counter() - start_time) * 1000, 2)

            return {
                "port": port,
                "protocol": "UDP",
                "state": "OPEN_RESPONDED",
                "rtt_ms": rtt_ms,
                "bytes_received": len(data),
                "error": None
            }

    except ConnectionRefusedError:
        # Triggered when target host returns ICMP Port Unreachable (Type 3, Code 3)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "port": port,
            "protocol": "UDP",
            "state": "CLOSED",
            "rtt_ms": elapsed_ms,
            "bytes_received": 0,
            "error": "ICMP Port Unreachable received (UDP port is closed)."
        }

    except socket.timeout:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "port": port,
            "protocol": "UDP",
            "state": "OPEN_OR_FILTERED",
            "rtt_ms": elapsed_ms,
            "bytes_received": 0,
            "error": f"No UDP response within {timeout}s (Port may be open without reply, or silently filtered)."
        }

    except OSError as e:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "port": port,
            "protocol": "UDP",
            "state": "ERROR",
            "rtt_ms": elapsed_ms,
            "bytes_received": 0,
            "error": f"UDP socket error: {e.strerror}"
        }

def run_tcp_diagnostics(resolved_ips: list[str], ports: list[int] | None = None, include_udp_dns_check: bool = False) -> dict:
    if not resolved_ips:
        return {
            "module": "tcp_diagnostics",
            "status": "SKIPPED",
            "data": {},
            "error": "No target IP addresses available from DNS stage."
        }

    target_ip = resolved_ips[0]  # Test primary resolved IP
    ports_to_test = ports if ports else DEFAULT_PORTS

    tcp_results = [test_tcp_port(target_ip, p) for p in ports_to_test]
    udp_result = test_udp_probe(target_ip, 53) if include_udp_dns_check else None

    any_open = any(r["state"] == "OPEN" for r in tcp_results)
    status = "PASS" if any_open else "FAIL"
    error = None if any_open else f"None of the tested TCP ports {ports_to_test} are open on {target_ip}."

    return {
        "module": "tcp_diagnostics",
        "status": status,
        "data": {
            "tested_ip": target_ip,
            "tcp_ports": tcp_results,
            "udp_probe": udp_result
        },
        "error": error
    }