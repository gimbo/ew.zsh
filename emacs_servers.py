#!/usr/bin/env python

"""Look for named emacs servers/daemons and launch them if needed.

This is intended to be run as a MacOS launch agent, e.g. with a config as follows:

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>com.barefootcode.emacs-servers</string>
    <key>ProgramArguments</key>
    <array>
      <string>/opt/homebrew/bin/python3</string>
      <string>/Users/andy.gimblett/prog/gimbo/zsh-plugins/ew.zsh/emacs_servers.py</string>
      <string>server</string>
      <string>git</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StartInterval</key>
    <integer>10</integer>
    <key>Nice</key>
    <integer>10</integer>
    <key>ProcessType</key>
    <string>Background</string>
    <key>WorkingDirectory</key>
    <string>/Users/andy.gimblett</string>
    <!--
    <key>StandardOutPath</key>
    <string>/Users/andy.gimblett/com.barefootcode.emacs-servers.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/andy.gimblett/com.barefootcode.emacs-servers.stderr.log</string>
    -->
    <key>StandardOutPath</key>
    <string>/dev/null</string>
    <key>StandardErrorPath</key>
    <string>/dev/null</string>
  </dict>
</plist>

(If you want to log output, then comment out/uncomment the appropriate
`StandardOutPath`/`StandardErrorPath` entries as desired — and don't forget to
also set `DEBUG` to `True` in the script itself if you want to see actual
output.)
"""

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DEBUG = False
EMACS_TMP_FOLDER_NAME = "emacs{0}".format(os.getuid())
EMACS_BINARY_PATH = "/Applications/Emacs.app/Contents/MacOS/Emacs"


def main():
    debug()
    debug("emacs_servers.py starting")
    requested_servers = tuple(
        sorted(sys.argv[1:], key=lambda x: x if x != "server" else "0")
    )
    requested_servers = set(sys.argv[1:])
    if not requested_servers:
        debug("No emacs servers requested; nothing to do")
        return
    debug("Requested emacs servers:", ", ".join(requested_servers))
    running_servers = list_running_servers()
    debug("Running emacs servers:", ", ".join(running_servers))
    missing_servers = requested_servers - running_servers
    if not missing_servers:
        debug("All requested emacs servers running; nothing to do")
        return
    debug("Missing emacs servers:", ", ".join(missing_servers))
    for server in missing_servers:
        attempt_to_start_server(server)
    debug("emacs_server.py finished")


def list_running_servers():
    emacs_servers = set(get_apparent_emacs_server_processes().values())
    debug("Apparently running emacs servers:", emacs_servers)
    try:
        server_sockets = set(path.name for path in emacs_servers_path().iterdir())
    except FileNotFoundError:
        server_sockets = {}
    debug("Server_sockets:", server_sockets)
    for server_socket in server_sockets:
        if server_socket not in emacs_servers:
            debug("Removing dangling server socket:", server_socket)
            os.unlink(emacs_servers_path() / server_socket)
    return emacs_servers


def get_apparent_emacs_server_processes():
    debug("Listing apparent emacs server processes")
    emacs_pids = list(
        sorted(
            int(line.split()[0])
            for line in run_command(
                ["ps", "-x", "-o", "pid,command"],
                filter_fn=lambda line: "emacs" in line.lower(),
            )
        )
    )
    debug(
        "PIDs of emacs-like processes: {0}".format(
            ", ".join(str(pid) for pid in emacs_pids)
        )
    )
    return {
        pid: server_name
        for pid, server_name in [
            (pid, check_if_process_is_emacs_server(pid)) for pid in emacs_pids
        ]
        if server_name is not None
    }


def check_if_process_is_emacs_server(pid: int):
    debug("Checking process with pid:", pid)
    servers_path = str(emacs_servers_path())
    output = "\n".join(run_command(["lsof", "+p", str(pid)], debug_output=False))
    regex = "{0}".format(emacs_servers_path()) + r"/(\S+)$"
    match = re.search(regex, output, re.MULTILINE)
    if match:
        server_name = match.group(1)
        debug(
            "Process with pid {0} seems to be running emacs server: {1}".format(
                pid, server_name
            )
        )
        return server_name


def emacs_servers_path():
    return Path(os.environ["TMPDIR"]) / EMACS_TMP_FOLDER_NAME


def attempt_to_start_server(server: str):
    debug("Attempting to start server:", server)
    run_command([EMACS_BINARY_PATH, "--daemon={0}".format(server)], filter_fn=bool)
    debug("Started emacs server successfully: {0}".format(server))


def run_command(args, filter_fn=None, debug_output=True):
    cmd_line = " ".join(args)
    debug("  Running command: {0}".format(cmd_line))
    output = subprocess.check_output(
        args, encoding="utf-8", errors="replace", stderr=subprocess.STDOUT
    ).split("\n")
    if filter_fn is not None:
        output = [line for line in output if filter_fn(line)]
    if debug_output:
        for line in output:
            debug("    {0}".format(line))
    debug("  Finished running command: {0}".format(cmd_line))
    return output


def debug(*args):
    if not DEBUG:
        return
    print(datetime.utcnow().isoformat(timespec="seconds"), *args, flush=True)


if __name__ == "__main__":
    main()
