import ipaddress
import subprocess

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
        return False, f"Command failed ({e.returncode}): {e.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s: {' '.join(cmd)}"

def is_ip_address(target: str) -> bool:
    try:
        ipaddress.ip_address(target)
        return True
    except ValueError:
        return False