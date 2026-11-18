import socket
import ssl
import time
from datetime import datetime, timezone
from utils.config import DEFAULT_TIMEOUT

def run_tls_diagnostics(hostname: str, ip: str, port: int = 443, timeout: float = DEFAULT_TIMEOUT) -> dict:
    # Create a default TLS context that enforces hostname & CA chain verification
    context = ssl.create_default_context()
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    start_time = time.perf_counter()

    try:
        with socket.socket(family, socket.SOCK_STREAM) as raw_sock:
            raw_sock.settimeout(timeout)
            raw_sock.connect((ip, port))

            # Wrap TCP socket in TLS; server_hostname sends the SNI extension
            with context.wrap_socket(raw_sock, server_hostname=hostname) as tls_sock:
                handshake_ms = round((time.perf_counter() - start_time) * 1000, 2)
                cert = tls_sock.getpeercert()
                cipher_name, tls_version, secret_bits = tls_sock.cipher()

                # Parse certificate validity dates (format: 'Nov 18 12:00:00 2026 GMT')
                not_after_str = cert.get("notAfter")
                not_before_str = cert.get("notBefore")
                expiry_dt = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                days_remaining = (expiry_dt - datetime.now(timezone.utc)).days

                # Flatten subject and issuer tuples into readable dicts
                subject = dict(item[0] for item in cert.get("subject", []))
                issuer = dict(item[0] for item in cert.get("issuer", []))

                status = "WARN" if days_remaining < 15 else "PASS"
                warning = f"Certificate expires soon ({days_remaining} days remaining)." if days_remaining < 15 else None

                return {
                    "module": "tls_diagnostics",
                    "status": status,
                    "data": {
                        "hostname": hostname,
                        "tested_ip": ip,
                        "port": port,
                        "tls_version": tls_version,
                        "cipher_suite": cipher_name,
                        "key_bits": secret_bits,
                        "handshake_ms": handshake_ms,
                        "subject_cn": subject.get("commonName"),
                        "issuer_org": issuer.get("organizationName"),
                        "issuer_cn": issuer.get("commonName"),
                        "valid_from": not_before_str,
                        "valid_until": not_after_str,
                        "days_remaining": days_remaining
                    },
                    "error": warning
                }

    except ssl.SSLCertVerificationError as e:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "module": "tls_diagnostics",
            "status": "FAIL",
            "data": {"hostname": hostname, "tested_ip": ip, "port": port, "handshake_ms": elapsed_ms},
            "error": f"TLS Certificate Verification Failed: {e.verify_message} (code {e.verify_code})"
        }
    except ssl.SSLError as e:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "module": "tls_diagnostics",
            "status": "FAIL",
            "data": {"hostname": hostname, "tested_ip": ip, "port": port, "handshake_ms": elapsed_ms},
            "error": f"TLS Handshake Protocol Error: {e.reason}"
        }
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "module": "tls_diagnostics",
            "status": "FAIL",
            "data": {"hostname": hostname, "tested_ip": ip, "port": port, "handshake_ms": elapsed_ms},
            "error": f"TCP/Socket failure before TLS handshake: {e}"
        }