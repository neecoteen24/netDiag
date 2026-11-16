import argparse
import json
from modules.network_info import collect_network_info
from modules.dns_diagnostics import run_dns_diagnostics
from modules.tcp_diagnostics import run_tcp_diagnostics
from utils.config import DEFAULT_PORTS

def parse_ports(port_str: str) -> list[int]:
    return [int(p.strip()) for p in port_str.split(",") if p.strip().isdigit()]

def main():
    parser = argparse.ArgumentParser(description="NetDiag - Network Diagnostics Toolkit")
    parser.add_argument("--target", default="google.com", help="Target domain or IP address")
    parser.add_argument("--ports", default="80,443", help="Comma-separated TCP ports (e.g., 80,443,22)")
    parser.add_argument("--udp-probe", action="store_true", help="Also run UDP port 53 probe")
    args = parser.parse_args()

    ports = parse_ports(args.ports) or DEFAULT_PORTS

    net_result = collect_network_info()
    dns_result = run_dns_diagnostics(args.target)

    # Prefer IPv4 if available, fallback to IPv6
    candidate_ips = dns_result["data"].get("ipv4") or dns_result["data"].get("ipv6") or []
    tcp_result = run_tcp_diagnostics(candidate_ips, ports=ports, include_udp_dns_check=args.udp_probe)

    report = {
        "target": args.target,
        "diagnostics": [
            net_result,
            dns_result,
            tcp_result
        ]
    }

    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()