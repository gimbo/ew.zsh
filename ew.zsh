# Emacs for the win!

# Assumes 'server-use-tcp' is nil, so we use a socket.

EMACSTMP=$TMPDIR/emacs$(id -u)

# Start an emacs server.  Takes one optional argument, the server
# name, defaulting to "server".
#
ess() {
  if (( $# == 0)); then
    local server="server"
  else
    local server="$1"
  fi
  local socket="$EMACSTMP/$server"
  echo "Looking for emacs socket at $socket"
  if [ -e "$socket" ]; then
    echo "Server $server already running"
  else
    echo "Starting server $server"
    emacs --daemon=$server
  fi
}

# List the currently running emacs servers, and any emacs processes.
#
esl() {
  ls -a -1 $EMACSTMP | sort
  echo
  pgrep -il emacs
}

# Kill an emacs server.  Takes one optional argument, the server name,
# defaulting to "server".
#
esk() {
  if (( $# == 0)); then
    local server="server"
  else
    local server="$1"
  fi
  local socket="$EMACSTMP/$server"
  echo "Looking for emacs socket at $socket"
  if [ -e "$socket" ]; then
    echo "Sending (kill-emacs) to $server"
    emacsclient -s $server -e '(kill-emacs)'
  else
    echo "Socket not found for server $server, nothing to do"
  fi
  sleep 1
  esl
}

# Emacs clients for the command line and GUI.
#
e() {
  emacsclient --alternate-editor="" -t "$@"
}

ew() {
  if (( $# == 0 )); then
    # No filename, just open and focus.
    emacsclient --alternate-editor="" -c -n --eval '(x-focus-frame nil)' &
  else
    emacsclient --alternate-editor="" -c -n "$@" &
  fi
}

# I prefer to edit ~/.emacs in its own server space, which
# automatically gets a different colour thanks to my ~/.emacs
#
alias ewdot="ew -s .emacs ~/.emacs-dir/amg-init.el"
