import time
import urllib.error
import urllib.request
from utils.config import DEFAULT_TIMEOUT

IMPORTANT_HEADERS = [
    "Server",
    "Content-Type",
    "Cache-Control",
    "Strict-Transport-Security",
    "X-Frame-Options",
    "Via",
    "CF-Ray"
]

def run_http_diagnostics(target: str, scheme: str = "https", timeout: float = DEFAULT_TIMEOUT) -> dict:
    url = target if target.startswith(("http://", "https://")) else f"{scheme}://{target}"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": "NetDiag-CLI/1.0"}
    )

    start_time = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            status_code = response.getcode()
            final_url = response.geturl()
            raw_headers = dict(response.headers.items())

            filtered_headers = {
                h: raw_headers[h] for h in IMPORTANT_HEADERS if h in raw_headers
            }

            return {
                "module": "http_diagnostics",
                "status": "PASS" if 200 <= status_code < 400 else "WARN",
                "data": {
                    "requested_url": url,
                    "final_url": final_url,
                    "redirected": url.rstrip("/") != final_url.rstrip("/"),
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "headers": filtered_headers
                },
                "error": None
            }

    except urllib.error.HTTPError as e:
        # Server responded, but with an HTTP error status (e.g., 403 Forbidden, 404, 502 Bad Gateway)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "module": "http_diagnostics",
            "status": "FAIL",
            "data": {
                "requested_url": url,
                "final_url": e.geturl(),
                "redirected": url.rstrip("/") != e.geturl().rstrip("/"),
                "status_code": e.code,
                "latency_ms": latency_ms,
                "headers": {}
            },
            "error": f"HTTP {e.code} {e.reason}"
        }

    except urllib.error.URLError as e:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "module": "http_diagnostics",
            "status": "FAIL",
            "data": {
                "requested_url": url,
                "final_url": None,
                "redirected": False,
                "status_code": None,
                "latency_ms": latency_ms,
                "headers": {}
            },
            "error": f"URL/Connection Error: {e.reason}"
        }