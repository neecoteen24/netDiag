import subprocess


def run_command(cmd: list[str]) -> tuple[bool, str]:
    """
    Execute a Linux command safely.

    Returns:
        (True, stdout)  if the command succeeds.
        (False, error)  if execution fails.
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )

        return True, result.stdout.strip()

    except FileNotFoundError:
        return False, f"Command not found: {cmd[0]}"

    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or error.stdout.strip()
        return False, message or f"Command failed with exit code {error.returncode}"

    except subprocess.TimeoutExpired:
        return False, f"Command timed out: {' '.join(cmd)}"

    except OSError as error:
        return False, str(error)