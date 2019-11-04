# #########################################################################
# This bash script adds tab-completion feature to django-admin.py and
# manage.py.
#
# Testing it out without installing
# =================================
#
# To test out the completion without "installing" this, just run this file
# directly, like so:
#
#     . ~/path/to/django_bash_completion
#
# Note: There's a dot ('.') at the beginning of that command.
#
# After you do that, tab completion will immediately be made available in your
# current Bash shell. But it won't be available next time you log in.
#
# Installing
# ==========
#
# To install this, point to this file from your .bash_profile, like so:
#
#     . ~/path/to/django_bash_completion
#
# Do the same in your .bashrc if .bashrc doesn't invoke .bash_profile.
#
# Settings will take effect the next time you log in.
#
# Uninstalling
# ============
#
# To uninstall, just remove the line from your .bash_profile and .bashrc.

_django_completion()
{
    COMPREPLY=( $( COMP_WORDS="${COMP_WORDS[*]}" \
                   COMP_CWORD=$COMP_CWORD \
                   DJANGO_AUTO_COMPLETE=1 $1 ) )
}
complete -F _django_completion -o default django-admin.py manage.py django-admin

_python_django_completion()
{
    if [[ ${COMP_CWORD} -ge 2 ]]; then
        local PYTHON_EXE=${COMP_WORDS[0]##*/}
        echo $PYTHON_EXE | egrep "python([3-9]\.[0-9])?" >/dev/null 2>&1
        if [[ $? == 0 ]]; then
            local PYTHON_SCRIPT=${COMP_WORDS[1]##*/}
            echo $PYTHON_SCRIPT | egrep "manage\.py|django-admin(\.py)?" >/dev/null 2>&1
            if [[ $? == 0 ]]; then
                COMPREPLY=( $( COMP_WORDS="${COMP_WORDS[*]:1}" \
                               COMP_CWORD=$(( COMP_CWORD-1 )) \
                               DJANGO_AUTO_COMPLETE=1 ${COMP_WORDS[*]} ) )
            fi
        fi
    fi
}

# Support for multiple interpreters.
unset pythons
if command -v whereis &>/dev/null; then
    python_interpreters=$(whereis python | cut -d " " -f 2-)
    for python in $python_interpreters; do
        [[ $python != *-config ]] && pythons="${pythons} ${python##*/}"
    done
    unset python_interpreters
    pythons=$(echo $pythons | tr " " "\n" | sort -u | tr "\n" " ")
else
    pythons=python
fi

complete -F _python_django_completion -o default $pythons
unset pythons
