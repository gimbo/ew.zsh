# Emacs for the win!

# Assumes 'server-use-tcp' is nil, so we use a socket.

EMACSTMP=$TMPDIR/emacs$(id -u)

autoload -Uz ec esk esl ess ew

# I prefer to edit ~/.emacs in its own server space, which
# automatically gets a different colour thanks to my ~/.emacs
#
alias ewdot="ew -s .emacs ~/.emacs-dir/amg-init.el"
