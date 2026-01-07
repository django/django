# This file must be used with "source bin/activate.csh" *from csh*.
# You cannot run it directly.
# Created by Davide Di Blasi <davidedb@gmail.com>.

set newline='\
'

alias deactivate 'test $?_OLD_VIRTUAL_PATH != 0 && setenv PATH "$_OLD_VIRTUAL_PATH:q" && unset _OLD_VIRTUAL_PATH; rehash; test $?_OLD_VIRTUAL_TCL_LIBRARY != 0 && setenv TCL_LIBRARY "$_OLD_VIRTUAL_TCL_LIBRARY:q" && unset _OLD_VIRTUAL_TCL_LIBRARY || unsetenv TCL_LIBRARY; test $?_OLD_VIRTUAL_TK_LIBRARY != 0 && setenv TK_LIBRARY "$_OLD_VIRTUAL_TK_LIBRARY:q" && unset _OLD_VIRTUAL_TK_LIBRARY || unsetenv TK_LIBRARY; test $?_OLD_VIRTUAL_PROMPT != 0 && set prompt="$_OLD_VIRTUAL_PROMPT:q" && unset _OLD_VIRTUAL_PROMPT; unsetenv VIRTUAL_ENV; unsetenv VIRTUAL_ENV_PROMPT; test "\!:*" != "nondestructive" && unalias deactivate && unalias pydoc'

# Unset irrelevant variables.
deactivate nondestructive

setenv VIRTUAL_ENV __VIRTUAL_ENV__

set _OLD_VIRTUAL_PATH="$PATH:q"
setenv PATH "$VIRTUAL_ENV:q/"__BIN_NAME__":$PATH:q"

if (__TCL_LIBRARY__ != "") then
    if ($?TCL_LIBRARY) then
        set _OLD_VIRTUAL_TCL_LIBRARY="$TCL_LIBRARY"
    endif
    setenv TCL_LIBRARY __TCL_LIBRARY__
endif

if (__TK_LIBRARY__ != "") then
    if ($?TK_LIBRARY) then
        set _OLD_VIRTUAL_TK_LIBRARY="$TK_LIBRARY"
    endif
    setenv TK_LIBRARY __TK_LIBRARY__
endif

if (__VIRTUAL_PROMPT__ != "") then
    setenv VIRTUAL_ENV_PROMPT __VIRTUAL_PROMPT__
else
    setenv VIRTUAL_ENV_PROMPT "$VIRTUAL_ENV:t:q"
endif

if ( $?VIRTUAL_ENV_DISABLE_PROMPT ) then
    if ( $VIRTUAL_ENV_DISABLE_PROMPT == "" ) then
        set do_prompt = "1"
    else
        set do_prompt = "0"
    endif
else
    set do_prompt = "1"
endif

if ( $do_prompt == "1" ) then
    # Could be in a non-interactive environment,
    # in which case, $prompt is undefined and we wouldn't
    # care about the prompt anyway.
    if ( $?prompt ) then
        set _OLD_VIRTUAL_PROMPT="$prompt:q"
        if ( "$prompt:q" =~ *"$newline:q"* ) then
            :
        else
            set prompt = '('"$VIRTUAL_ENV_PROMPT:q"') '"$prompt:q"
        endif
    endif
endif

unset env_name
unset do_prompt

alias pydoc python -m pydoc

rehash
