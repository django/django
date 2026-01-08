@REM This file is UTF-8 encoded, so we need to update the current code page while executing it
@for /f "tokens=2 delims=:." %%a in ('"%SystemRoot%\System32\chcp.com"') do @set _OLD_CODEPAGE=%%a

@if defined _OLD_CODEPAGE (
    "%SystemRoot%\System32\chcp.com" 65001 > nul
)

@set "VIRTUAL_ENV=__VIRTUAL_ENV__"

@set "VIRTUAL_ENV_PROMPT=__VIRTUAL_PROMPT__"
@if NOT DEFINED VIRTUAL_ENV_PROMPT (
    @for %%d in ("%VIRTUAL_ENV%") do @set "VIRTUAL_ENV_PROMPT=%%~nxd"
)

@if defined _OLD_VIRTUAL_PROMPT (
    @set "PROMPT=%_OLD_VIRTUAL_PROMPT%"
) else (
    @if not defined PROMPT (
        @set "PROMPT=$P$G"
    )
    @if not defined VIRTUAL_ENV_DISABLE_PROMPT (
        @set "_OLD_VIRTUAL_PROMPT=%PROMPT%"
    )
)
@if not defined VIRTUAL_ENV_DISABLE_PROMPT (
    @set "PROMPT=(%VIRTUAL_ENV_PROMPT%) %PROMPT%"
)

@REM Don't use () to avoid problems with them in %PATH%
@if defined _OLD_VIRTUAL_PYTHONHOME @goto ENDIFVHOME
    @set "_OLD_VIRTUAL_PYTHONHOME=%PYTHONHOME%"
:ENDIFVHOME

@set PYTHONHOME=

@if defined TCL_LIBRARY @set "_OLD_VIRTUAL_TCL_LIBRARY=%TCL_LIBRARY%"
@if NOT "__TCL_LIBRARY__"=="" @set "TCL_LIBRARY=__TCL_LIBRARY__"

@if defined TK_LIBRARY @set "_OLD_VIRTUAL_TK_LIBRARY=%TK_LIBRARY%"
@if NOT "__TK_LIBRARY__"=="" @set "TK_LIBRARY=__TK_LIBRARY__"

@REM if defined _OLD_VIRTUAL_PATH (
@if not defined _OLD_VIRTUAL_PATH @goto ENDIFVPATH1
    @set "PATH=%_OLD_VIRTUAL_PATH%"
:ENDIFVPATH1
@REM ) else (
@if defined _OLD_VIRTUAL_PATH @goto ENDIFVPATH2
    @set "_OLD_VIRTUAL_PATH=%PATH%"
:ENDIFVPATH2

@set "PATH=%VIRTUAL_ENV%\__BIN_NAME__;%PATH%"

@if defined _OLD_CODEPAGE (
    "%SystemRoot%\System32\chcp.com" %_OLD_CODEPAGE% > nul
    @set _OLD_CODEPAGE=
)
