#!/bin/bash
########################################################################################################################
# Convert Physical CSS → Logical CSS for Django
########################################################################################################################

# https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_logical_properties_and_values/Basic_concepts_of_logical_properties_and_values
# https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_logical_properties_and_values/Floating_and_positioning
# https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_logical_properties_and_values/Margins_borders_padding
# https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_logical_properties_and_values/Sizing

# https://caniuse.com/css-logical-props
# https://elad.medium.com/new-css-logical-properties-bc6945311ce7

set -o errexit -o nounset -o pipefail

declare -a css_all=($(echo django/contrib/admin/static/admin/css/*.css))
declare -a css_rtl=($(echo django/contrib/admin/static/admin/css/*rtl*.css))
declare -a scripts=()

trap '[[ ${#scripts[@]} -gt 0 ]] && rm --force "${scripts[@]}"' EXIT

function try_replace {
    local -r paths="${1}[@]"
    sed --in-place --regexp-extended "${2}" "${!paths}"
}

function try_simplify_shorthand {
    local -r s="${2:+-${2}}"
    # 4(t,r,b,l) → 1(trbl) | 4(t,r,b,l) → 2(tb,rl) | 4(t,r,b,l) → 3(t,rl,b)
    try_replace css_all "s/^( *${1}${s}: *([^ ]+)) +\\2 +\\2 +\\2( *;)/\\1\\3/g"
    try_replace css_all "s/^( *${1}${s}: *([^ ]+) +([^ ]+)) +\\2 +\\3( *;)/\\1\\4/g"
    try_replace css_all "s/^( *${1}${s}: *[^ ]+ +([^ ]+) +[^ ]+) +\\2( *;)/\\1\\3/g"
    try_commit "Simplified shorthand physical ${1}${s} properties (4-value shorthand)."
    # 3(t,rl,b) → 1(trbl) | 3(t,rl,b) → 2(tb,rl)
    try_replace css_all "s/^( *${1}${s}: *([^ ]+)) +\\2 +\\2( *;)/\\1\\3/g"
    try_replace css_all "s/^( *${1}${s}: *([^ ]+) +[^ ]+) +\\2( *;)/\\1\\3/g"
    try_commit "Simplified shorthand physical ${1}${s} properties (3-value shorthand)."
    # 2(tb,rl) → 1(trbl)
    try_replace css_all "s/^( *${1}${s}: *([^ ]+)) +\\2( *;)/\\1\\3/g"
    try_commit "Simplified shorthand physical ${1}${s} properties (2-value shorthand)."
}

function try_convert_complex {
    local -r s="${2:+-${2}}"
    try_replace css_rtl "/^ *${1}${s}: *[^ ]+ +[^ ]+ +[^ ]+ +[^ ]+ *;/d"
    try_replace css_all "s/^( *${1})${s}: *([^ ]+) +([^ ]+) +([^ ]+) +([^ ]+) *(;.*)/\\1-block${s}: \\2 \\4\\6\\n\\1-inline${s}: \\5 \\3\\6/g"
    try_replace css_all "s/^( *${1}-(block|inline)${s}: *([^ ]+)) +\\3( *;)/\\1\\4/g"  # [1]
    try_commit "Changed from physical to logical ${1}${s} properties (4-value shorthand)."
    try_replace css_rtl "/^ *${1}${s}: *[^ ]+ +[^ ]+ +[^ ]+ *;/d"
    try_replace css_all "s/^( *${1})${s}: *([^ ]+) +([^ ]+) +([^ ]+) *(;.*)/\\1-block${s}: \\2 \\4\\5\\n\\1-inline${s}: \\3\\5/g"
    try_commit "Changed from physical to logical ${1}${s} properties (3-value shorthand)."
    try_replace css_rtl "/^ *${1}${s}: *[^ ]+ +[^ ]+ *;/d"
    try_replace css_all "s/^( *${1})${s}: *([^ ]+) +([^ ]+) *(;.*)/\\1-block${s}: \\2\\4\\n\\1-inline${s}: \\3\\4/g"
    try_commit "Changed from physical to logical ${1}${s} properties (2-value shorthand)."
    try_replace css_rtl "/^ *${1}-(top|bottom|left|right)${s}:/d"
    try_replace css_all "s/^( *${1}-)top${s}:/\\1block-start${s}:/g"
    try_replace css_all "s/^( *${1}-)bottom${s}:/\\1block-end${s}:/g"
    try_replace css_all "s/^( *${1}-)left${s}:/\\1inline-start${s}:/g"
    try_replace css_all "s/^( *${1}-)right${s}:/\\1inline-end${s}:/g"
    try_commit "Changed from physical to logical ${1}${s} properties (individual)."
    # [1]: Simplification after converting from 4-value shorthand with differing left and right values.
}

function try_convert_page {
    try_replace css_all 's/(@page *[^{]+):left\>/\1:verso/g'
    try_replace css_all 's/(@page *[^{]+):right\>/\1:recto/g'
    try_commit "Changed from physical to logical values for @page psuedo-classes."
}

function try_convert_value {
    local -r p="${1}"
    shift 1
    try_replace css_rtl "/^ *${p}:/d"
    for mapping in "${@}"
    do
        local old="${mapping%%:*}"
        local new="${mapping##*:}"
        try_replace css_all "s/^( *${p}: *)${old}/\\1${new}/g"
    done
    try_commit "Changed from physical to logical values for ${p} property."
}

function try_script {
    local -r paths="${1}[@]"
    local -r script="$(mktemp --tmpdir=/tmp 'XXXXX.sed')"
    scripts+=("${script}")
    cat /dev/stdin > "${script}"
    for path in "${!paths}"
    do
        sed --in-place --quiet --regexp-extended --file="${script}" "${path}"
    done
}

function try_commit {
    if [[ -n $(git status --porcelain --untracked-files=no -- "${css_all[@]}") ]]
    then
        git add --update -- "${css_all[@]}"
        git commit --message="[RFC/WIP] Refs #????? -- ${1}" --quiet
        echo -e "\e[1;32m✔\e[39m ${1}\e[0m"
    else
        echo -e "\e[1;31m✘\e[39m ${1}\e[0m"
    fi
}

# https://www.w3.org/TR/css-logical-1/#dimension-properties
try_replace css_rtl '/^ *(max-|min-)?(height|width):/d'
try_replace css_all 's/^( *)(max-|min-)?height:/\1\2block-size:/'
try_replace css_all 's/^( *)(max-|min-)?width:/\1\2inline-size:/'
try_commit 'Changed from physical to logical dimension properties.'

# https://www.w3.org/TR/css-logical-1/#margin-properties
try_simplify_shorthand margin
try_convert_complex margin

# https://www.w3.org/TR/css-logical-1/#position-properties
try_replace css_rtl '/^ *(top|bottom|left|right):/d'
try_replace css_all 's/^( *)top:/\1inset-block-start:/g'
try_replace css_all 's/^( *)bottom:/\1inset-block-end:/g'
try_replace css_all 's/^( *)left:/\1inset-inline-start:/g'
try_replace css_all 's/^( *)right:/\1inset-inline-end:/g'
# TODO: Handle `inset`, `inset-block` and `inset-inline` where necessary.
try_commit 'Changed from physical to logical position properties.'

# https://www.w3.org/TR/css-logical-1/#padding-properties
try_simplify_shorthand padding
try_convert_complex padding

# https://www.w3.org/TR/css-logical-1/#border-width
try_simplify_shorthand border width
try_convert_complex border width

# https://www.w3.org/TR/css-logical-1/#border-style
try_simplify_shorthand border style
try_convert_complex border style

# https://www.w3.org/TR/css-logical-1/#border-color
try_simplify_shorthand border color
try_convert_complex border color

# https://www.w3.org/TR/css-logical-1/#border-shorthands
try_replace css_rtl '/^ *border-(top|bottom|left|right):/d'
try_replace css_all 's/^( *border-)top:/\1block-start:/g'
try_replace css_all 's/^( *border-)bottom:/\1block-end:/g'
try_replace css_all 's/^( *border-)left:/\1inline-start:/g'
try_replace css_all 's/^( *border-)right:/\1inline-end:/g'
# TODO: Handle `border` to `border-block` and `border-inline` where necessary.
try_commit 'Changed from physical to logical border shorthand properties.'

# https://www.w3.org/TR/css-logical-1/#border-radius-properties
try_replace css_rtl '/^ *border-(top|bottom)-(left|right)-radius:/d'
try_replace css_all 's/^( *border-)top-left-radius:/\1start-start-radius:/g'
try_replace css_all 's/^( *border-)bottom-left-radius:/\1start-end-radius:/g'
try_replace css_all 's/^( *border-)top-right-radius:/\1end-start-radius:/g'
try_replace css_all 's/^( *border-)bottom-right-radius:/\1end-end-radius:/g'
try_commit 'Changed from physical to logical border radius properties.'

# https://www.w3.org/TR/css-logical-1/#caption-side
# https://drafts.csswg.org/css-logical-1/#caption-side
# https://developer.mozilla.org/en-US/docs/Web/CSS/caption-side
# https://developer.mozilla.org/en-US/docs/Web/CSS/caption-side
# https://caniuse.com/mdn-css_properties_caption-side_writing-mode_relative_values
# https://caniuse.com/mdn-css_properties_caption-side_non_standard_values
# XXX: Not widely supported yet.
try_convert_value caption-side top:block-start bottom:block-end left:inline-start right:inline-end

# https://www.w3.org/TR/css-logical-1/#float-clear
# https://drafts.csswg.org/css-logical-1/#float-clear
# https://developer.mozilla.org/en-US/docs/Web/CSS/clear
# https://developer.mozilla.org/en-US/docs/Web/CSS/float
# https://caniuse.com/mdn-css_properties_clear_flow_relative_values
# https://caniuse.com/mdn-css_properties_float_flow_relative_values
# XXX: Unflagged in Chrome/Edge 118 & Opera 104, so expect support to increase rapidly.
try_convert_value clear left:inline-start right:inline-end
try_convert_value float left:inline-start right:inline-end

# https://www.w3.org/TR/css-logical-1/#text-align
# https://drafts.csswg.org/css-logical-1/#text-align
# https://developer.mozilla.org/en-US/docs/Web/CSS/text-align
# https://caniuse.com/mdn-css_properties_text-align_flow_relative_values_start_and_end
try_convert_value text-align left:start right:end

# https://www.w3.org/TR/css-logical-1/#resize
# https://drafts.csswg.org/css-logical-1/  (Removed?)
# https://developer.mozilla.org/en-US/docs/Web/CSS/resize
# https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_logical_properties_and_values/Sizing#logical_keywords_for_resize
# https://caniuse.com/mdn-css_properties_resize_flow_relative_support
# XXX: Unflagged in Chrome/Edge 118 & Opera 104, so expect support to increase rapidly.
try_convert_value resize horizontal:inline vertical:block

# https://www.w3.org/TR/css-logical-1/#page
# https://drafts.csswg.org/css-logical-1/#page
# https://caniuse.com/mdn-css_properties_break-after_paged_context_recto
# https://caniuse.com/mdn-css_properties_break-before_paged_context_recto
# XXX: No browser support. Also renamed to drop `page-` prefix.
try_convert_value page-break-after left:verso right:recto
try_convert_value page-break-before left:verso right:recto
try_convert_page

# https://www.w3.org/TR/css-break-3/
# https://drafts.csswg.org/css-break/#break-between
# https://caniuse.com/mdn-css_properties_break-after_paged_context_recto
# https://caniuse.com/mdn-css_properties_break-before_paged_context_recto
# XXX: No browser support.
try_convert_value break-after left:verso right:recto
try_convert_value break-before left:verso right:recto

# https://www.w3.org/TR/css-scroll-snap-1/#scroll-snap-type
# https://drafts.csswg.org/css-scroll-snap-1/#scroll-snap-type
# https://caniuse.com/mdn-css_properties_scroll-snap-type
try_convert_value scroll-snap-type x:inline y:block

# https://www.w3.org/TR/css-scroll-snap-1/#scroll-margin
# https://www.w3.org/TR/css-scroll-snap-1/#margin-longhands-logical
# https://drafts.csswg.org/css-scroll-snap-1/#scroll-margin
# https://drafts.csswg.org/css-scroll-snap-1/#margin-longhands-logical
# https://caniuse.com/mdn-css_properties_scroll-margin-block
# https://caniuse.com/mdn-css_properties_scroll-margin-block-start
# https://caniuse.com/mdn-css_properties_scroll-margin-block-end
# https://caniuse.com/mdn-css_properties_scroll-margin-inline
# https://caniuse.com/mdn-css_properties_scroll-margin-inline-start
# https://caniuse.com/mdn-css_properties_scroll-margin-inline-end
try_simplify_shorthand scroll-margin
try_convert_complex scroll-margin

# https://www.w3.org/TR/css-scroll-snap-1/#scroll-padding
# https://www.w3.org/TR/css-scroll-snap-1/#padding-longhands-logical
# https://drafts.csswg.org/css-scroll-snap-1/#scroll-padding
# https://drafts.csswg.org/css-scroll-snap-1/#padding-longhands-logical
# https://caniuse.com/mdn-css_properties_scroll-padding-block
# https://caniuse.com/mdn-css_properties_scroll-padding-block-start
# https://caniuse.com/mdn-css_properties_scroll-padding-block-end
# https://caniuse.com/mdn-css_properties_scroll-padding-inline
# https://caniuse.com/mdn-css_properties_scroll-padding-inline-start
# https://caniuse.com/mdn-css_properties_scroll-padding-inline-end
try_simplify_shorthand scroll-padding
try_convert_complex scroll-padding

# https://www.w3.org/TR/css-overflow-3/#overflow-control
# https://drafts.csswg.org/css-overflow-3/#overflow-control
# https://caniuse.com/mdn-css_properties_overflow-block
# https://caniuse.com/mdn-css_properties_overflow-inline
# XXX: Not widely supported yet.
try_replace css_rtl '/^ *overflow-[xy]:/d'
try_replace css_all 's/^( *overflow-)x:/\1inline:/g'
try_replace css_all 's/^( *overflow-)y:/\1block:/g'
try_commit 'Changed from physical to logical overflow properties.'

# https://www.w3.org/TR/css-overscroll-1/#overscroll-behavior-longhands-logical
# https://drafts.csswg.org/css-overscroll/#overscroll-behavior-longhands-logical
# https://caniuse.com/mdn-css_properties_overscroll-behavior-block
# https://caniuse.com/mdn-css_properties_overscroll-behavior-inline
try_replace css_rtl '/^ *overscroll-behavior-[xy]:/d'
try_replace css_all 's/^( *overscroll-behavior-)x:/\1inline:/g'
try_replace css_all 's/^( *overscroll-behavior-)y:/\1block:/g'
try_commit 'Changed from physical to logical overscroll behavior properties.'

# https://www.w3.org/TR/css-sizing-4/#intrinsic-size-override
# https://drafts.csswg.org/css-sizing-4/#intrinsic-size-override
# https://caniuse.com/mdn-css_properties_contain-intrinsic-block-size
# https://caniuse.com/mdn-css_properties_contain-intrinsic-inline-size
try_replace css_rtl '/^ *contain-intrinsic-(width|height):/d'
try_replace css_all 's/^( *contain-instrinsic-)width:/\1inline-size:/g'
try_replace css_all 's/^( *contain-instrinsic-)height:/\1block-size:/g'
try_commit 'Changed from physical to logical contain intrinsic properties.'

# Remove empty CSS rule sets from RTL stylesheets.
# Based on https://unix.stackexchange.com/a/520887
try_script css_rtl <<'EOF'
# Read the whole document into the pattern space.
1{h;d};H;${x
# Remove all empty rule sets.
:again
s/[][[:alnum:][:space:]()@>.:#"'=+-]+(,[][[:alnum:][:space:]()@>.:#"'=+-]+)*[[:space:]]*\{[[:space:]]*\}//g
t again
# Remove excess new lines, except after comment or rule set.
s/([}/]\n)?(\n)\2*/\1\2/g
# Output the result.
p}
EOF
try_script css_rtl <<'EOF'
# Read the whole document into the pattern space.
1{h;d};H;${x
# Remove all comments followed by another comment.
:again
s@/\*[^}]*\*/[[:space:]]*/\*@/*@g
t again
# Output the result.
p}
EOF
try_script css_rtl <<'EOF'
# Read the whole document into the pattern space.
1{h;d};H;${x
# Remove all comments at the end of the file.
s@}[[:space:]]*/*[^}]*\*/[[:space:]]*$@}@g
# Output the result.
p}
EOF
try_commit 'Removed empty CSS rule sets from RTL stylesheets.'

########################################################################################################################

# Fixed #????? -- Used logical properties in CSS for admin site.
#
# Use of logical properties allows for more simple handling of styles for
# different writing modes/directions than use of the traditional physical
# properties. It should also help avoid issues with bugs related to different
# writing directions that crop up whenever things are changed.
#
# 1. Migrate properties as follows, but remove from rtl stylesheets or
#    `[dir=rtl]` rules first
#
#   - `height` → `block-size`
#   - `max-height` → `max-block-size`
#   - `min-height` → `min-block-size`
#   - `width` → `inline-size`
#   - `max-width` → `max-inline-size`
#   - `min-width` → `min-inline-size`
#   - `margin-top` → `margin-block-start`
#   - `margin-bottom` → `margin-block-end`
#   - `margin-left` → `margin-inline-start`
#   - `margin-right` → `margin-inline-end`
#   - `top` → `inset-block-start`
#   - `bottom` → `inset-block-end`
#   - `left` → `inset-inline-start`
#   - `right` → `inset-inline-end`
#   - `padding-top` → `padding-block-start`
#   - `padding-bottom` → `padding-block-end`
#   - `padding-left` → `padding-inline-start`
#   - `padding-right` → `padding-inline-end`
#   - `border-top-width` → `border-block-start-width`
#   - `border-bottom-width` → `border-block-end-width`
#   - `border-left-width` → `border-inline-start-width`
#   - `border-right-width` → `border-inline-end-width`
#   - `border-top-style` → `border-block-start-style`
#   - `border-bottom-style` → `border-block-end-style`
#   - `border-left-style` → `border-inline-start-style`
#   - `border-right-style` → `border-inline-end-style`
#   - `border-top-color` → `border-block-start-color`
#   - `border-bottom-color` → `border-block-end-color`
#   - `border-left-color` → `border-inline-start-color`
#   - `border-right-color` → `border-inline-end-color`
#   - `border-top` → `border-block-start`
#   - `border-bottom` → `border-block-end`
#   - `border-left` → `border-inline-start`
#   - `border-right` → `border-inline-end`
#   - `border-top-left-radius` → `border-start-start-radius`
#   - `border-bottom-left-radius` → `border-start-end-radius`
#   - `border-top-right-radius` → `border-end-start-radius`
#   - `border-bottom-right-radius` → `border-end-end-radius`
#   - `overflow-x` → `overflow-inline`
#   - `overflow-y` → `overflow-block`
#   - `overscroll-behavior-x` → `overscroll-behavior-inline`
#   - `overscroll-behavior-y` → `overscroll-behavior-block`
#   - `scroll-margin-top` → `scroll-margin-block-start`
#   - `scroll-margin-bottom` → `scroll-margin-block-end`
#   - `scroll-margin-left` → `scroll-margin-inline-start`
#   - `scroll-margin-right` → `scroll-margin-inline-end`
#   - `scroll-padding-top` → `scroll-padding-block-start`
#   - `scroll-padding-bottom` → `scroll-padding-block-end`
#   - `scroll-padding-left` → `scroll-padding-inline-start`
#   - `scroll-padding-right` → `scroll-padding-inline-end`
#   - `contain-intrinsic-width` → `contain-intrinsic-inline-size`
#   - `contain-intrinsic-height` → `contain-intrinsic-block-size`
#
#   - `caption-side: top` → `caption-side: block-start`
#   - `caption-side: bottom` → `caption-side: block-end`
#   - `clear: left` → `clear: inline-start`
#   - `clear: right` → `clear: inline-end`
#   - `float: left` → `float: inline-start`
#   - `float: right` → `float: inline-end`
#   - `resize: horizontal` → `resize: inline`
#   - `resize: vertical` → `resize: block`
#   - `text-align: left` → `text-align: start`
#   - `text-align: right` → `text-align: end`
#   - `scroll-snap-type: x` → `scroll-snap-type: inline`
#   - `scroll-snap-type: y` → `scroll-snap-type: block`
#
# 2. Merge some properties together
#
#   - `margin-block-start` + `margin-block-end` → `margin-block`
#   - `margin-inline-start` + `margin-inline-end` → `margin-inline`
#   - `inset-block-start` + `inset-block-end` → `inset-block`
#   - `inset-inline-start` + `inset-inline-end` → `inset-inline`
#   - `padding-block-start` + `padding-block-end` → `padding-block`
#   - `padding-inline-start` + `padding-inline-end` → `padding-inline`
#
# 3. The following things have no logical form...
#
#   - The `perspective-origin` property: `<x-position>`, `<y-position>`
#   - The `translate` property.
#   - Values for `perspective-origin`: `top`, `right`, `left`, `bottom`
#   - Values for `transform-origin`: `top`, `right`, `left`, `bottom`
#   - Values for `transform`:
#     - `rotateX()`, `rotateY()`, `rotateZ()`
#     - `scaleX()`, `scaleY()`, `scaleZ()`
#     - `skewX()`, `skewY()`
#     - `translateX()`, `translateY()`, `translateZ()`
#   - The `background-position*` properties:
#     - See https://drafts.csswg.org/css-backgrounds-4/#the-background-position
