# This file must be used with "source bin/activate" *from bash*
# you cannot run it directly


if [ "${BASH_SOURCE-}" = "$0" ]; then
    echo "You must source this script: \$ source $0" >&2
    exit 33
fi

deactivate () {
    unset -f pydoc >/dev/null 2>&1 || true

    # reset old environment variables
    # ! [ -z ${VAR+_} ] returns true if VAR is declared at all
    if ! [ -z "${_OLD_VIRTUAL_PATH:+_}" ] ; then
        PATH="$_OLD_VIRTUAL_PATH"
        export PATH
        unset _OLD_VIRTUAL_PATH
    fi
    if ! [ -z "${_OLD_VIRTUAL_PYTHONHOME+_}" ] ; then
        PYTHONHOME="$_OLD_VIRTUAL_PYTHONHOME"
        export PYTHONHOME
        unset _OLD_VIRTUAL_PYTHONHOME
    fi

    if ! [ -z "${_OLD_VIRTUAL_TCL_LIBRARY+_}" ]; then
        TCL_LIBRARY="$_OLD_VIRTUAL_TCL_LIBRARY"
        export TCL_LIBRARY
        unset _OLD_VIRTUAL_TCL_LIBRARY
    fi
    if ! [ -z "${_OLD_VIRTUAL_TK_LIBRARY+_}" ]; then
        TK_LIBRARY="$_OLD_VIRTUAL_TK_LIBRARY"
        export TK_LIBRARY
        unset _OLD_VIRTUAL_TK_LIBRARY
    fi

    # The hash command must be called to get it to forget past
    # commands. Without forgetting past commands the $PATH changes
    # we made may not be respected
    hash -r 2>/dev/null

    if ! [ -z "${_OLD_VIRTUAL_PS1+_}" ] ; then
        PS1="$_OLD_VIRTUAL_PS1"
        export PS1
        unset _OLD_VIRTUAL_PS1
    fi

    unset VIRTUAL_ENV
    unset VIRTUAL_ENV_PROMPT
    if [ ! "${1-}" = "nondestructive" ] ; then
    # Self destruct!
        unset -f deactivate
    fi
}

# unset irrelevant variables
deactivate nondestructive

VIRTUAL_ENV=__VIRTUAL_ENV__
if ([ "$OSTYPE" = "cygwin" ] || [ "$OSTYPE" = "msys" ]) && $(command -v cygpath &> /dev/null) ; then
    VIRTUAL_ENV=$(cygpath -u "$VIRTUAL_ENV")
fi
export VIRTUAL_ENV

_OLD_VIRTUAL_PATH="$PATH"
PATH="$VIRTUAL_ENV/"__BIN_NAME__":$PATH"
export PATH

if [ "x"__VIRTUAL_PROMPT__ != x ] ; then
    VIRTUAL_ENV_PROMPT=__VIRTUAL_PROMPT__
else
    VIRTUAL_ENV_PROMPT=$(basename "$VIRTUAL_ENV")
fi
export VIRTUAL_ENV_PROMPT

# unset PYTHONHOME if set
if ! [ -z "${PYTHONHOME+_}" ] ; then
    _OLD_VIRTUAL_PYTHONHOME="$PYTHONHOME"
    unset PYTHONHOME
fi

if [ __TCL_LIBRARY__ != "" ]; then
    if ! [ -z "${TCL_LIBRARY+_}" ] ; then
        _OLD_VIRTUAL_TCL_LIBRARY="$TCL_LIBRARY"
    fi
    TCL_LIBRARY=__TCL_LIBRARY__
    export TCL_LIBRARY
fi

if [ __TK_LIBRARY__ != "" ]; then
    if ! [ -z "${TK_LIBRARY+_}" ] ; then
        _OLD_VIRTUAL_TK_LIBRARY="$TK_LIBRARY"
    fi
    TK_LIBRARY=__TK_LIBRARY__
    export TK_LIBRARY
fi

if [ -z "${VIRTUAL_ENV_DISABLE_PROMPT-}" ] ; then
    _OLD_VIRTUAL_PS1="${PS1-}"
    PS1="(${VIRTUAL_ENV_PROMPT}) ${PS1-}"
    export PS1
fi

# Make sure to unalias pydoc if it's already there
alias pydoc 2>/dev/null >/dev/null && unalias pydoc || true

pydoc () {
    python -m pydoc "$@"
}

# The hash command must be called to get it to forget past
# commands. Without forgetting past commands the $PATH changes
# we made may not be respected
hash -r 2>/dev/null || true
