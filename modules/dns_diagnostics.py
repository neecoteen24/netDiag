
import socket
import time
import subprocess
import shutil
import re


# Supported DNS record types
SUPPORTED_RECORD_TYPES = {
    "A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA", "PTR"
}


def validate_hostname(hostname):
    """Validate basic hostname input."""

    if not isinstance(hostname, str) or not hostname.strip():
        return False

    return True


def resolve_hostname(hostname):
    """
    Resolve a hostname using the operating system's
    name resolution mechanism.

    Returns IPv4, IPv6 addresses and resolution time.
    """

    if not validate_hostname(hostname):
        return {
            "hostname": hostname,
            "success": False,
            "ipv4": [],
            "ipv6": [],
            "resolution_time_ms": 0.0,
            "error": "Hostname must be a non-empty string"
        }

    hostname = hostname.strip()
    start_time = time.perf_counter()

    try:
        results = socket.getaddrinfo(
            hostname,
            None,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM
        )

        ipv4_addresses = set()
        ipv6_addresses = set()

        for result in results:

            family = result[0]
            address = result[4][0]

            if family == socket.AF_INET:
                ipv4_addresses.add(address)

            elif family == socket.AF_INET6:
                ipv6_addresses.add(address)

        elapsed = (time.perf_counter() - start_time) * 1000

        return {
            "hostname": hostname,
            "success": True,
            "ipv4": sorted(ipv4_addresses),
            "ipv6": sorted(ipv6_addresses),
            "resolution_time_ms": round(elapsed, 2),
            "error": None
        }

    except socket.gaierror as error:

        elapsed = (time.perf_counter() - start_time) * 1000

        return {
            "hostname": hostname,
            "success": False,
            "ipv4": [],
            "ipv6": [],
            "resolution_time_ms": round(elapsed, 2),
            "error": str(error)
        }


def query_dns_record(hostname, record_type="A", nameserver=None):
    """
    Query a specific DNS record using the Linux dig utility.

    Optionally specify a DNS nameserver.
    """

    if not validate_hostname(hostname):
        return {
            "hostname": hostname,
            "record_type": record_type,
            "nameserver": nameserver,
            "success": False,
            "status": None,
            "answers": [],
            "query_time_ms": None,
            "error": "Hostname must be a non-empty string"
        }

    record_type = record_type.upper()

    if record_type not in SUPPORTED_RECORD_TYPES:
        return {
            "hostname": hostname,
            "record_type": record_type,
            "nameserver": nameserver,
            "success": False,
            "status": None,
            "answers": [],
            "query_time_ms": None,
            "error": "Unsupported DNS record type"
        }

    # Check whether dig is installed
    if shutil.which("dig") is None:
        return {
            "hostname": hostname,
            "record_type": record_type,
            "nameserver": nameserver,
            "success": False,
            "status": None,
            "answers": [],
            "query_time_ms": None,
            "error": "dig utility is not installed"
        }

    # Construct command safely using argument list
    command = ["dig"]

    if nameserver:
        command.append(f"@{nameserver}")

    command.extend([
        hostname.strip(),
        record_type,
        "+time=3",
        "+tries=1",
        "+noall",
        "+comments",
        "+answer",
        "+stats"
    ])

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False
        )

        output = result.stdout

        # Extract DNS response status
        status_match = re.search(
            r"status:\s*(\w+)",
            output
        )

        status = (
            status_match.group(1)
            if status_match
            else None
        )

        # Extract DNS query time
        time_match = re.search(
            r"Query time:\s*(\d+)\s*msec",
            output
        )

        query_time = (
            float(time_match.group(1))
            if time_match
            else None
        )

        # Extract answer records
        answers = []

        answer_section = False

        for line in output.splitlines():

            if line.startswith(";; ANSWER SECTION:"):
                answer_section = True
                continue

            if answer_section:

                if not line.strip() or line.startswith(";;"):
                    break

                answers.append(line.strip())

        # Determine whether a DNS answer was received
        success = status == "NOERROR" and len(answers) > 0

        if status == "NXDOMAIN":
            error = "Domain does not exist"

        elif status == "NOERROR" and not answers:
            error = "No records found for the requested record type"

        elif status != "NOERROR":
            error = f"DNS query returned status: {status}"

        else:
            error = None

        return {
            "hostname": hostname,
            "record_type": record_type,
            "nameserver": nameserver or "System default",
            "success": success,
            "status": status,
            "answers": answers,
            "query_time_ms": query_time,
            "error": error
        }

    except subprocess.TimeoutExpired:

        return {
            "hostname": hostname,
            "record_type": record_type,
            "nameserver": nameserver,
            "success": False,
            "status": None,
            "answers": [],
            "query_time_ms": None,
            "error": "DNS query timed out"
        }

    except OSError as error:

        return {
            "hostname": hostname,
            "record_type": record_type,
            "nameserver": nameserver,
            "success": False,
            "status": None,
            "answers": [],
            "query_time_ms": None,
            "error": str(error)
        }


def compare_dns_resolvers(hostname, record_type="A"):
    """
    Compare DNS responses from the system default resolver,
    Google DNS and Cloudflare DNS.
    """

    resolvers = [
        None,
        "8.8.8.8",
        "1.1.1.1"
    ]

    results = []

    for resolver in resolvers:

        result = query_dns_record(
            hostname,
            record_type,
            resolver
        )

        results.append(result)

    return results
