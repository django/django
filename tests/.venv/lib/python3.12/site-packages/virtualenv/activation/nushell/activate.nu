# virtualenv activation module:
# - Activate with `overlay use activate.nu`
# - Deactivate with `deactivate`, as usual
#
# To customize the overlay name, you can call `overlay use activate.nu as foo`, but then simply `deactivate` won't work
# because it is just an alias to hide the "activate" overlay. You'd need to call `overlay hide foo` manually.

module warning {
    export-env {
        const file = path self
        error make -u {
            msg: $"`($file | path basename)` is meant to be used with `overlay use`, not `source`"
        }
    }

}

use warning

export-env {

    let nu_ver = (version | get version | split row '.' | take 2 | each { into int })
        if $nu_ver.0 == 0 and $nu_ver.1 < 106 {
            error make {
                msg: 'virtualenv Nushell activation requires Nushell 0.106 or greater.'
            }
    }

    def is-string [x] {
        ($x | describe) == 'string'
    }

    def has-env [...names] {
        $names | each {|n| $n in $env } | all {|i| $i }
    }

    def is-env-true [name: string] {
        if (has-env $name) {
            let val = ($env | get --optional $name)
            if ($val | describe) == 'bool' {
                $val
            } else {
                not ($val | is-empty)
            }
        } else {
            false
        }
    }

    let virtual_env = __VIRTUAL_ENV__
    let bin = __BIN_NAME__
    let path_name = if (has-env 'Path') { 'Path' } else { 'PATH' }
    let venv_path = ([$virtual_env $bin] | path join)
    let new_path = ($env | get $path_name | prepend $venv_path)
    let virtual_env_prompt = if (__VIRTUAL_PROMPT__ | is-empty) {
        ($virtual_env | path basename)
    } else {
        __VIRTUAL_PROMPT__
    }
    let new_env = { $path_name: $new_path VIRTUAL_ENV: $virtual_env VIRTUAL_ENV_PROMPT: $virtual_env_prompt }
    if (has-env 'TCL_LIBRARY')  {
        let $new_env = $new_env | insert TCL_LIBRARY __TCL_LIBRARY__
    }
    if (has-env 'TK_LIBRARY')  {
        let $new_env = $new_env | insert TK_LIBRARY __TK_LIBRARY__
    }
    let old_prompt_command = if (has-env 'PROMPT_COMMAND') { $env.PROMPT_COMMAND } else { '' }
    let new_env = if (is-env-true 'VIRTUAL_ENV_DISABLE_PROMPT') {
        $new_env
    } else {
        let virtual_prefix = $'(char lparen)($virtual_env_prompt)(char rparen) '
        let new_prompt = if (has-env 'PROMPT_COMMAND') {
            if ('closure' in ($old_prompt_command | describe)) {
                {|| $'($virtual_prefix)(do $old_prompt_command)' }
            } else {
                {|| $'($virtual_prefix)($old_prompt_command)' }
            }
        } else {
            {|| $'($virtual_prefix)' }
        }
        $new_env | merge { PROMPT_COMMAND: $new_prompt VIRTUAL_PREFIX: $virtual_prefix }
    }
    load-env $new_env
}

export alias pydoc = python -m pydoc
export alias deactivate = overlay hide activate
