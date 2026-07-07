import re
import shlex

def patch_utils():
    with open('utils.py', 'r') as f:
        content = f.read()

    # Fix _EMAIL_RE
    content = content.replace(
        r"_EMAIL_RE = _re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')",
        r"_EMAIL_RE = _re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')"
    )

    # Fix _is_command_allowed
    old_func = """def _is_command_allowed(cmd: str) -> tuple[bool, str]:
    \"\"\"
    Validate command against strict allowlist templates.
    Returns (allowed, reason_if_blocked).
    \"\"\"
    cmd_stripped = cmd.strip()
    if not cmd_stripped:
        return False, "Empty command"

    # Check blocklist first (safety net)
    cmd_lower = cmd_stripped.lower()
    for blocked in BLOCKED_PATTERNS:
        if blocked in cmd_lower:
            return False, f"Blocked pattern: {blocked}"

    # Parse command to get base command and args
    import shlex
    try:
        parts = shlex.split(cmd_stripped)
    except ValueError as e:
        return False, f"Invalid command syntax: {e}"

    if not parts:
        return False, "Empty command"

    base_cmd = parts[0].lower()"""

    new_func = """def _is_command_allowed(cmd: str) -> tuple[bool, str]:
    \"\"\"
    Validate command against strict allowlist templates.
    Returns (allowed, reason_if_blocked).
    \"\"\"
    cmd_stripped = cmd.strip()
    if not cmd_stripped:
        return False, "Empty command"

    import shlex
    import re
    try:
        parts = shlex.split(cmd_stripped)
    except ValueError as e:
        return False, f"Invalid command syntax: {e}"

    if not parts:
        return False, "Empty command"

    base_cmd = parts[0].lower()
    
    # Blocked binaries (exact match for safety, prevents blocking 'grep subprocess')
    blocked_bins = {
        'sudo', 'su', 'doas', 'passwd', 'chown', 'chmod', 'mount', 'umount',
        'fdisk', 'parted', 'mkfs', 'iptables', 'ufw', 'firewall-cmd', 'service',
        'reboot', 'poweroff', 'halt', 'shutdown', 'crontab', 'at', 'batch',
        'ssh', 'scp', 'rsync', 'sftp', 'docker', 'podman', 'kubectl', 'helm',
        'chroot', 'pivot_root', 'python', 'python3', 'bash', 'sh', 'zsh', 'tmux'
    }
    if base_cmd in blocked_bins or base_cmd.startswith('/etc/init.d/'):
        return False, f"Blocked binary: {base_cmd}"

    cmd_lower = cmd_stripped.lower()
    dangerous_patterns = [
        r'rm\s+-rf\s+/', r'dd\s+if=', r':\(\)\{', r'fork bomb',
        r'>\s*/dev/', r'>\s*/proc/', r'>\s*/sys/', r'chmod\s+-r\s+777\s+/',
        r'curl.*\|.*bash', r'wget.*\|.*sh',
        r'systemctl\s+(start|stop|restart|enable|disable)',
        r'tar\s+--checkpoint', r'__import__', r'importlib',
        r'exec\(', r'eval\(', r'os\.system', r'subprocess\.'
    ]
    for pat in dangerous_patterns:
        if re.search(pat, cmd_lower):
            return False, f"Blocked pattern: {pat}"
"""

    content = content.replace(old_func, new_func)

    with open('utils.py', 'w') as f:
        f.write(content)

patch_utils()
print("Fixed utils.py")
