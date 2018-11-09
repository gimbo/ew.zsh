#!/usr/bin/env python

"""
If emacs daemon isn't running, launch it and wait for it to finish.

This is a wrapper/helper for running the emacs daemon as a launch agent with
KeepAlive=true

If the LaunchAgent definition runs the emacs daemon directly, as follows, there
is a problem:

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE blah>
 <plist version="1.0">
  <dict>
    <key>Label</key>
    <string>gnu.emacs.daemon</string>
    <key>ProgramArguments</key>
    <array>
      <string>/Applications/Emacs.app/Contents/MacOS/Emacs</string>
      <string>--daemon</string>
    </array>
   <key>RunAtLoad</key>
   <true/>
   <key>KeepAlive</key>
   <true/>
  </dict>
</plist>

The problem is that the resultant running process's name doesn't match the
contents of the ProgramArguments entry, so launchd continually thinks it's not
running and tries to launch it again; that fails because it *is* running, so
then launchd fills the log with messages about the process exiting too early.

Instead, we use this wrapper, whose name as a running process is stable,
predictable, and can match what is seen in ProgramArguments:

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE blah>
 <plist version="1.0">
  <dict>
    <key>Label</key>
    <string>gnu.emacs.daemon</string>
    <key>ProgramArguments</key>
    <array>
      <string>/usr/local/bin/python3</string>
      <string>PATH TO THIS FILE</string>
    </array>
   <key>RunAtLoad</key>
   <true/>
   <key>KeepAlive</key>
   <true/>
  </dict>
</plist>

"""

import os
import subprocess
import time


SLEEP_TIME = 10


def main():
    # If emacs daemon isn't running, launch it and wait for it to finish;
    # otherwise return immediately.
    if not emacs_daemon_is_running():
        launch_emacs_daemon()
        wait_for_emacs_daemon_to_end()


def emacs_daemon_is_running():
    ps_output = (
        subprocess.check_output(['ps', 'ax']).decode('utf-8').split('\n')[1:]
    )
    for line in ps_output:
        if 'Emacs.app' in line and 'daemon' in line:
            return True
    return False


def launch_emacs_daemon():
    os.system('/Applications/Emacs.app/Contents/MacOS/Emacs --daemon')


def wait_for_emacs_daemon_to_end():
    while emacs_daemon_is_running():
        time.sleep(10)


if __name__ == '__main__':
    main()
