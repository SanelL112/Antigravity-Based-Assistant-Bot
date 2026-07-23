import re

def fix_bot_commands():
    with open('bot/commands.py', 'r') as f:
        content = f.read()

    # _get_server_overview
    content = content.replace(
        'subprocess.check_output("uptime", shell=True, text=True)',
        'subprocess.check_output(["uptime"], text=True)'
    )

    # _get_mc_status
    mc_status_old = """    try:
        import subprocess
        res = subprocess.check_output("systemctl is-active minecraft || echo 'inactive'", shell=True, text=True).strip()
        return f"⛏️ **Minecraft Server**\\nStatus: `{res}`"
    except Exception as e: return str(e)"""
    mc_status_new = """    try:
        import subprocess
        try:
            res = subprocess.check_output(["systemctl", "is-active", "minecraft"], text=True).strip()
        except subprocess.CalledProcessError:
            res = "inactive"
        return f"⛏️ **Minecraft Server**\\nStatus: `{res}`"
    except Exception as e: return str(e)"""
    content = content.replace(mc_status_old, mc_status_new)

    # _get_embed_status
    embed_status_old = """    try:
        import subprocess
        res = subprocess.check_output("tail -n 10 /tmp/embed_build4.log || echo 'No log found'", shell=True, text=True).strip()
        return f"🧠 **Embedding Progress**\\n```\\n{res}\\n```"
    except Exception as e: return str(e)"""
    embed_status_new = """    try:
        import os
        log_path = "/tmp/embed_build4.log"
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                lines = f.readlines()
            res = "".join(lines[-10:]).strip()
        else:
            res = "No log found"
        return f"🧠 **Embedding Progress**\\n```\\n{res}\\n```"
    except Exception as e: return str(e)"""
    content = content.replace(embed_status_old, embed_status_new)

    # _get_bot_status
    bot_status_old = """    try:
        import subprocess
        res = subprocess.check_output("systemctl status antigravity-bot | head -n 5", shell=True, text=True).strip()
        return f"🤖 **Bot Service**\\n```\\n{res}\\n```"
    except Exception as e: return str(e)"""
    bot_status_new = """    try:
        import subprocess
        res = subprocess.check_output(["systemctl", "status", "antigravity-bot"], text=True)
        res = "\\n".join(res.splitlines()[:5]).strip()
        return f"🤖 **Bot Service**\\n```\\n{res}\\n```"
    except Exception as e: return str(e)"""
    content = content.replace(bot_status_old, bot_status_new)

    # _get_mc_log
    content = content.replace(
        'subprocess.check_output("journalctl -u minecraft -n 10 --no-pager", shell=True, text=True)',
        'subprocess.check_output(["journalctl", "-u", "minecraft", "-n", "10", "--no-pager"], text=True)'
    )

    # _get_ram_status
    content = content.replace(
        'subprocess.check_output("free -h", shell=True, text=True)',
        'subprocess.check_output(["free", "-h"], text=True)'
    )

    # _get_services_status
    services_old = """    try:
        import subprocess
        res = subprocess.check_output("systemctl list-units --type=service --state=running | head -n 10", shell=True, text=True).strip()
        return f"⚙️ **Services**\\n```\\n{res}\\n```"
    except Exception as e: return str(e)"""
    services_new = """    try:
        import subprocess
        res = subprocess.check_output(["systemctl", "list-units", "--type=service", "--state=running"], text=True)
        res = "\\n".join(res.splitlines()[:10]).strip()
        return f"⚙️ **Services**\\n```\\n{res}\\n```"
    except Exception as e: return str(e)"""
    content = content.replace(services_old, services_new)

    # _get_bot_log
    content = content.replace(
        'subprocess.check_output("journalctl -u antigravity-bot -n 10 --no-pager", shell=True, text=True)',
        'subprocess.check_output(["journalctl", "-u", "antigravity-bot", "-n", "10", "--no-pager"], text=True)'
    )

    # _mc_start
    content = content.replace(
        'subprocess.check_output("sudo systemctl start minecraft", shell=True)',
        'subprocess.check_output(["sudo", "systemctl", "start", "minecraft"])'
    )

    # _mc_stop
    content = content.replace(
        'subprocess.check_output("sudo systemctl stop minecraft", shell=True)',
        'subprocess.check_output(["sudo", "systemctl", "stop", "minecraft"])'
    )

    with open('bot/commands.py', 'w') as f:
        f.write(content)

if __name__ == "__main__":
    fix_bot_commands()
    print("Fixed bot/commands.py")
