import ipaddress
import subprocess
from urllib.parse import urlparse

def run_command(cmd: list[str], timeout: int = 5) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout
        )
        return True, result.stdout.strip()
    except FileNotFoundError:
        return False, f"Command not found: {cmd[0]}"
    except subprocess.CalledProcessError as e:
        err_output = e.stdout.strip() if e.stdout.strip() else e.stderr.strip()
        return False, err_output if err_output else f"Command failed with exit code {e.returncode}"
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s: {' '.join(cmd)}"

def is_ip_address(target: str) -> bool:
    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        return False

def extract_hostname(target: str) -> str:
    target = target.strip()
    if "://" not in target:
        target = f"http://{target}"
    parsed = urlparse(target)
    return parsed.hostname or target