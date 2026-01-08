$script:THIS_PATH = $myinvocation.mycommand.path
$script:BASE_DIR = Split-Path (Resolve-Path "$THIS_PATH/..") -Parent

function global:deactivate([switch] $NonDestructive) {
    if (Test-Path variable:_OLD_VIRTUAL_PATH) {
        $env:PATH = $variable:_OLD_VIRTUAL_PATH
        Remove-Variable "_OLD_VIRTUAL_PATH" -Scope global
    }

    if (Test-Path variable:_OLD_VIRTUAL_TCL_LIBRARY) {
        $env:TCL_LIBRARY = $variable:_OLD_VIRTUAL_TCL_LIBRARY
        Remove-Variable "_OLD_VIRTUAL_TCL_LIBRARY" -Scope global
    } else {
        if (Test-Path env:TCL_LIBRARY) {
            Remove-Item env:TCL_LIBRARY -ErrorAction SilentlyContinue
        }
    }

    if (Test-Path variable:_OLD_VIRTUAL_TK_LIBRARY) {
        $env:TK_LIBRARY = $variable:_OLD_VIRTUAL_TK_LIBRARY
        Remove-Variable "_OLD_VIRTUAL_TK_LIBRARY" -Scope global
    } else {
        if (Test-Path env:TK_LIBRARY) {
            Remove-Item env:TK_LIBRARY -ErrorAction SilentlyContinue
        }
    }

    if (Test-Path function:_old_virtual_prompt) {
        $function:prompt = $function:_old_virtual_prompt
        Remove-Item function:\_old_virtual_prompt
    }

    if ($env:VIRTUAL_ENV) {
        Remove-Item env:VIRTUAL_ENV -ErrorAction SilentlyContinue
    }

    if ($env:VIRTUAL_ENV_PROMPT) {
        Remove-Item env:VIRTUAL_ENV_PROMPT -ErrorAction SilentlyContinue
    }

    if (!$NonDestructive) {
        # Self destruct!
        Remove-Item function:deactivate
        Remove-Item function:pydoc
    }
}

function global:pydoc {
    python -m pydoc $args
}

# unset irrelevant variables
deactivate -nondestructive

$VIRTUAL_ENV = $BASE_DIR
$env:VIRTUAL_ENV = $VIRTUAL_ENV

if (__VIRTUAL_PROMPT__ -ne "") {
    $env:VIRTUAL_ENV_PROMPT = __VIRTUAL_PROMPT__
}
else {
    $env:VIRTUAL_ENV_PROMPT = $( Split-Path $env:VIRTUAL_ENV -Leaf )
}

if (__TCL_LIBRARY__ -ne "") {
    if (Test-Path env:TCL_LIBRARY) {
        New-Variable -Scope global -Name _OLD_VIRTUAL_TCL_LIBRARY -Value $env:TCL_LIBRARY
    }
    $env:TCL_LIBRARY = __TCL_LIBRARY__
}

if (__TK_LIBRARY__ -ne "") {
    if (Test-Path env:TK_LIBRARY) {
        New-Variable -Scope global -Name _OLD_VIRTUAL_TK_LIBRARY -Value $env:TK_LIBRARY
    }
    $env:TK_LIBRARY = __TK_LIBRARY__
}

New-Variable -Scope global -Name _OLD_VIRTUAL_PATH -Value $env:PATH

$env:PATH = "$env:VIRTUAL_ENV/" + __BIN_NAME__ + __PATH_SEP__ + $env:PATH
if (!$env:VIRTUAL_ENV_DISABLE_PROMPT) {
    function global:_old_virtual_prompt {
        ""
    }
    $function:_old_virtual_prompt = $function:prompt

    function global:prompt {
        # Add the custom prefix to the existing prompt
        $previous_prompt_value = & $function:_old_virtual_prompt
        ("(" + $env:VIRTUAL_ENV_PROMPT + ") " + $previous_prompt_value)
    }
}
