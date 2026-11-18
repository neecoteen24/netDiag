import argparse
import json
from modules.network_info import collect_network_info
from modules.dns_diagnostics import run_dns_diagnostics
from modules.connectivity import run_connectivity_diagnostics
from modules.tcp_diagnostics import run_tcp_diagnostics
from modules.tls_diagnostics import run_tls_diagnostics
from modules.http_diagnostics import run_http_diagnostics
from utils.config import DEFAULT_PORTS
from utils.helpers import extract_hostname
from utils.logger import setup_logger


def parse_ports(port_str: str) -> list[int]:
    return [int(p.strip()) for p in port_str.split(",") if p.strip().isdigit()]


def main():
    logger = setup_logger()
    parser = argparse.ArgumentParser(description="NetDiag - Network Diagnostics Toolkit")
    parser.add_argument("--target", default="google.com", help="Target domain, URL, or IP address")
    parser.add_argument("--ports", default="80,443", help="Comma-separated TCP ports (e.g., 80,443,22)")
    parser.add_argument("--udp-probe", action="store_true", help="Also run UDP port 53 probe")
    parser.add_argument("--no-trace", action="store_true", help="Skip traceroute for faster execution")
    parser.add_argument("--scheme", default="https", choices=["http", "https"], help="HTTP scheme to test")
    args = parser.parse_args()

    hostname = extract_hostname(args.target)
    logger.info(f"Starting diagnostic run for target={args.target} (host={hostname}), ports={args.ports}")
    ports = parse_ports(args.ports) or DEFAULT_PORTS

    net_result = collect_network_info()
    dns_result = run_dns_diagnostics(hostname)

    candidate_ips = dns_result["data"].get("ipv4") or dns_result["data"].get("ipv6") or []
    conn_result = run_connectivity_diagnostics(candidate_ips, include_trace=not args.no_trace)
    tcp_result = run_tcp_diagnostics(candidate_ips, ports=ports, include_udp_dns_check=args.udp_probe)

    if candidate_ips and 443 in ports:
        tls_result = run_tls_diagnostics(hostname, candidate_ips[0], port=443)
    else:
        tls_result = {
            "module": "tls_diagnostics",
            "status": "SKIPPED",
            "data": {},
            "error": "Skipped (no resolved IP or port 443 not in target ports)."
        }

    if candidate_ips:
        http_result = run_http_diagnostics(args.target, scheme=args.scheme)
    else:
        http_result = {
            "module": "http_diagnostics",
            "status": "SKIPPED",
            "data": {},
            "error": "Skipped due to DNS resolution failure."
        }

    diagnostics = [net_result, dns_result, conn_result, tcp_result, tls_result, http_result]

    for mod in diagnostics:
        if mod["status"] == "FAIL":
            logger.error(f"[{mod['module']}] FAIL - {mod['error']}")
        elif mod["status"] == "WARN":
            logger.warning(f"[{mod['module']}] WARN - {mod['error']}")
        else:
            logger.info(f"[{mod['module']}] {mod['status']}")

    report = {
        "target": args.target,
        "resolved_hostname": hostname,
        "diagnostics": diagnostics
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()