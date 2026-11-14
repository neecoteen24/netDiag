import json

from utils.helpers import run_command


def get_interfaces() -> list[dict]:
    """
    Retrieve network interfaces and their IP addresses.
    """
    success, output = run_command(["ip", "-j", "addr", "show"])

    if not success:
        return []

    try:
        raw_interfaces = json.loads(output)
    except json.JSONDecodeError:
        return []

    interfaces = []

    for interface in raw_interfaces:
        name = interface.get("ifname")

        if not name:
            continue

        interface_info = {
            "name": name,
            "state": interface.get("operstate", "UNKNOWN"),
            "mac": None if name == "lo" else interface.get("address"),
            "ipv4": [],
            "ipv6": []
        }

        for address_info in interface.get("addr_info", []):
            family = address_info.get("family")
            ip_address = address_info.get("local")
            prefix_length = address_info.get("prefixlen")

            if not ip_address or prefix_length is None:
                continue

            address = f"{ip_address}/{prefix_length}"

            if family == "inet":
                interface_info["ipv4"].append(address)

            elif family == "inet6":
                interface_info["ipv6"].append(address)

        interfaces.append(interface_info)

    return interfaces


def get_default_gateway() -> dict:
    """
    Retrieve the default gateway and its outgoing interface.
    """
    default_gateway = {
        "gateway": None,
        "interface": None
    }

    success, output = run_command(
        ["ip", "-j", "route", "show", "default"]
    )

    if not success:
        return default_gateway

    try:
        routes = json.loads(output)
    except json.JSONDecodeError:
        return default_gateway

    for route in routes:
        if route.get("dst") == "default":
            default_gateway["gateway"] = route.get("gateway")
            default_gateway["interface"] = route.get("dev")
            break

    return default_gateway


def get_dns_resolvers() -> list[str]:
    """
    Read configured DNS nameservers from /etc/resolv.conf.
    """
    resolvers = []

    try:
        with open("/etc/resolv.conf", "r", encoding="utf-8") as file:
            for line in file:
                line = line.split("#", 1)[0].strip()

                if not line:
                    continue

                parts = line.split()

                if len(parts) >= 2 and parts[0] == "nameserver":
                    resolvers.append(parts[1])

    except OSError:
        return []

    return resolvers


def collect_network_info() -> dict:
    """
    Collect network interface, gateway, and DNS information.
    """
    interfaces = get_interfaces()
    gateway = get_default_gateway()
    dns_resolvers = get_dns_resolvers()

    active_interfaces = [
        interface
        for interface in interfaces
        if interface["name"] != "lo"
        and interface["state"].upper() == "UP"
    ]

    errors = []

    if not interfaces:
        errors.append("Could not retrieve network interfaces")

    elif not active_interfaces:
        errors.append("No active non-loopback network interface found")

    if gateway["gateway"] is None:
        errors.append("Default gateway not found")

    return {
        "module": "network_info",
        "status": "PASS" if not errors else "FAIL",
        "data": {
            "interfaces": interfaces,
            "default_gateway": gateway,
            "dns_resolvers": dns_resolvers
        },
        "error": "; ".join(errors) if errors else None
    }