#!/usr/bin/env python3

"""Helper script for managing emacs server processes."""

EXTRA_DOCS = """

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
      <string>ensure</string>
      <string>server</string>
      <string>git</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StartInterval</key>
    <integer>5</integer>
    <key>Nice</key>
    <integer>10</integer>
    <key>ProcessType</key>
    <string>Background</string>
    <key>WorkingDirectory</key>
    <string>/Users/andy.gimblett</string>
    <key>StandardOutPath</key>
    <string>/dev/null</string>
    <key>StandardErrorPath</key>
    <string>/dev/null</string>
  </dict>
</plist>

If you want to turn on debug output add

      <string>--debug</string>

before the "ensure" line above, and set StandardOutPath and StandardErrorPath as appropriate.
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple


EMACS_BINARY_PATH = "/Applications/Emacs.app/Contents/MacOS/Emacs"


def main():
    args = parse_args(sys.argv[1:])
    debug()
    debug("emacs_servers.py starting")
    debug("args:", args)
    if args.command == "list":
        list_running_servers()
    elif args.command == "clean":
        clean_dangling_server_sockets()
    elif args.command == "ensure":
        if not args.stopped:
            ensure_servers_running(args.servers)
        else:
            ensure_servers_stopped(args.servers)
    debug("emacs_server.py finished")


# Commands


def list_running_servers() -> Set[str]:
    debug("Listing running servers")
    emacs_server_processes: Dict[int, str] = enumerate_apparent_emacs_server_processes()
    debug("Apparently running emacs server processes:", emacs_server_processes)
    emacs_server_sockets: Set[str] = enumerate_apparent_server_sockets()
    debug("Apparent emacs server sockets:", emacs_server_sockets)
    max_server_name_length: int = max(
        [0] + [len(server_name) for server_name in emacs_server_processes.values()]
    )
    template = "Server: {{0:<{0}}}  |  PID: {{1:>6}}  |  Has socket: {{2:<5}}".format(
        max_server_name_length
    )
    if not emacs_server_processes:
        print("No emacs server processes seem to be running.")
    for pid, server_name in emacs_server_processes.items():
        has_socket = server_name in emacs_server_sockets
        print(template.format(server_name, pid, str(has_socket)))
    for socket_name in set(emacs_server_sockets) - set(emacs_server_processes.values()):
        print("Dangling socket (no associated process): {0}".format(socket_name))
    return set(emacs_server_processes.values()) & set(emacs_server_sockets)


def clean_dangling_server_sockets():
    debug("Cleaning up dangling server sockets")
    emacs_server_processes = enumerate_apparent_emacs_server_processes()
    debug("Apparently running emacs server processes:", emacs_server_processes)
    emacs_server_sockets = enumerate_apparent_server_sockets()
    debug("Apparent emacs server sockets:", emacs_server_sockets)
    dangling_socket_names = emacs_server_sockets - set(emacs_server_processes.values())
    if not dangling_socket_names:
        debug("No dangling sockets to clean up")
    for socket_name in dangling_socket_names:
        print("Cleaning dangling emacs server socket: {0}".format(socket_name))
        os.unlink(emacs_server_sockets_path() / socket_name)


def ensure_servers_running(requested_servers: List[str]):
    debug("Ensuring servers running: ", requested_servers)
    running_servers = list_running_servers()
    debug("Running emacs servers:", ", ".join(running_servers))
    missing_servers = set(requested_servers) - running_servers
    if not missing_servers:
        debug("All requested emacs servers running; nothing to do")
        return
    debug("Missing emacs servers:", ", ".join(missing_servers))
    for server in missing_servers:
        attempt_to_start_server(server)


def ensure_servers_stopped(servers: List[str]):
    debug("Ensuring servers stopped: ", servers)
    raise NotImplementedError()


# Machinery called by commands


def enumerate_apparent_emacs_server_processes() -> Dict[int, str]:
    def check_if_process_is_emacs_server(pid: int):
        debug("Checking process with pid:", pid)
        output = "\n".join(run_command(["lsof", "+p", str(pid)], debug_output=False))
        regex = "{0}".format(emacs_server_sockets_path()) + r"/(\S+)$"
        match = re.search(regex, output, re.MULTILINE)
        if match:
            server_name = match.group(1)
            debug(
                "Process with pid {0} seems to be running emacs server: {1}".format(
                    pid, server_name
                )
            )
            return server_name

    debug("Enumerating apparent emacs server processes")
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


def enumerate_apparent_server_sockets() -> Set[str]:
    debug("Enumerating apparent emacs server sockets")
    try:
        return set(
            path.name
            for path in emacs_server_sockets_path().iterdir()
            if path.is_socket()
        )
    except FileNotFoundError:
        return {}


def emacs_server_sockets_path():
    """Compute path to user-specific emacs server socket folder."""
    return Path(os.environ["TMPDIR"]) / "emacs{0}".format(os.getuid())


def attempt_to_start_server(server: str):
    debug("Attempting to start server:", server)
    run_command([EMACS_BINARY_PATH, "--daemon={0}".format(server)], filter_fn=bool)
    debug("Started emacs server successfully: {0}".format(server))


# I/O handling, running commands, and argument parsing


def debug(*args):
    if not DEBUG:
        return
    print(datetime.utcnow().isoformat(timespec="seconds"), *args, flush=True)


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


def parse_args(argsraw: List[str]):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("-d", "--debug", action="store_true", help="Write debug output")

    commands = parser.add_subparsers(title="commands", dest="command", required=True)
    commands.add_parser("list", description="List running servers")
    commands.add_parser(
        "clean",
        description="Clean up dangling server sockets (i.e. those without an associated running process)",
    )
    cmd_ensure = commands.add_parser(
        "ensure", description="Ensure named servers are running or stopped"
    )
    cmd_ensure.add_argument(
        "-S",
        "--stopped",
        action="store_true",
        help="Ensure named servers are stopped (default is to ensure running",
    )
    cmd_ensure.add_argument(
        "servers",
        help="Names of servers to ensure are running",
        metavar="SERVER_NAME",
        nargs="+",
    )

    args = parser.parse_args(argsraw)

    global DEBUG
    DEBUG = args.debug
    del args.debug

    return args


if __name__ == "__main__":
    main()
