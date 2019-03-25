#! /usr/bin/env python
# -*- coding: utf-8 -*-

#   math2html: convert LaTeX equations to HTML output.
#
#   Copyright (C) 2009-2011 Alex Fernández
#
#   Released under the terms of the `2-Clause BSD license'_, in short:
#   Copying and distribution of this file, with or without modification,
#   are permitted in any medium without royalty provided the copyright
#   notice and this notice are preserved.
#   This file is offered as-is, without any warranty.
#
# .. _2-Clause BSD license: http://www.spdx.org/licenses/BSD-2-Clause

#   Based on eLyXer: convert LyX source files to HTML output.
#   http://alexfernandez.github.io/elyxer/

# --end--
# Alex 20101110
# eLyXer standalone formula conversion to HTML.




import sys

class Trace(object):
  "A tracing class"

  debugmode = False
  quietmode = False
  showlinesmode = False

  prefix = None

  def debug(cls, message):
    "Show a debug message"
    if not Trace.debugmode or Trace.quietmode:
      return
    Trace.show(message, sys.stdout)

  def message(cls, message):
    "Show a trace message"
    if Trace.quietmode:
      return
    if Trace.prefix and Trace.showlinesmode:
      message = Trace.prefix + message
    Trace.show(message, sys.stdout)

  def error(cls, message):
    "Show an error message"
    message = '* ' + message
    if Trace.prefix and Trace.showlinesmode:
      message = Trace.prefix + message
    Trace.show(message, sys.stderr)

  def fatal(cls, message):
    "Show an error message and terminate"
    Trace.error('FATAL: ' + message)
    exit(-1)

  def show(cls, message, channel):
    "Show a message out of a channel"
    if sys.version_info < (3,0):
      message = message.encode('utf-8')
    channel.write(message + '\n')

  debug = classmethod(debug)
  message = classmethod(message)
  error = classmethod(error)
  fatal = classmethod(fatal)
  show = classmethod(show)




import os.path
import sys


class BibStylesConfig(object):
  "Configuration class from elyxer.config file"

  abbrvnat = {
      
      '@article':'$authors. $title. <i>$journal</i>,{ {$volume:}$pages,} $month $year.{ doi: $doi.}{ URL <a href="$url">$url</a>.}{ $note.}', 
      'cite':'$surname($year)', 
      'default':'$authors. <i>$title</i>. $publisher, $year.{ URL <a href="$url">$url</a>.}{ $note.}', 
      }

  alpha = {
      
      '@article':'$authors. $title.{ <i>$journal</i>{, {$volume}{($number)}}{: $pages}{, $year}.}{ <a href="$url">$url</a>.}{ <a href="$filename">$filename</a>.}{ $note.}', 
      'cite':'$Sur$YY', 
      'default':'$authors. $title.{ <i>$journal</i>,} $year.{ <a href="$url">$url</a>.}{ <a href="$filename">$filename</a>.}{ $note.}', 
      }

  authordate2 = {
      
      '@article':'$authors. $year. $title. <i>$journal</i>, <b>$volume</b>($number), $pages.{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@book':'$authors. $year. <i>$title</i>. $publisher.{ URL <a href="$url">$url</a>.}{ $note.}', 
      'cite':'$surname, $year', 
      'default':'$authors. $year. <i>$title</i>. $publisher.{ URL <a href="$url">$url</a>.}{ $note.}', 
      }

  default = {
      
      '@article':'$authors: “$title”, <i>$journal</i>,{ pp. $pages,} $year.{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@book':'{$authors: }<i>$title</i>{ ($editor, ed.)}.{{ $publisher,} $year.}{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@booklet':'$authors: <i>$title</i>.{{ $publisher,} $year.}{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@conference':'$authors: “$title”, <i>$journal</i>,{ pp. $pages,} $year.{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@inbook':'$authors: <i>$title</i>.{{ $publisher,} $year.}{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@incollection':'$authors: <i>$title</i>{ in <i>$booktitle</i>{ ($editor, ed.)}}.{{ $publisher,} $year.}{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@inproceedings':'$authors: “$title”, <i>$booktitle</i>,{ pp. $pages,} $year.{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@manual':'$authors: <i>$title</i>.{{ $publisher,} $year.}{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@mastersthesis':'$authors: <i>$title</i>.{{ $publisher,} $year.}{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@misc':'$authors: <i>$title</i>.{{ $publisher,}{ $howpublished,} $year.}{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@phdthesis':'$authors: <i>$title</i>.{{ $publisher,} $year.}{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@proceedings':'$authors: “$title”, <i>$journal</i>,{ pp. $pages,} $year.{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@techreport':'$authors: <i>$title</i>, $year.{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@unpublished':'$authors: “$title”, <i>$journal</i>, $year.{ URL <a href="$url">$url</a>.}{ $note.}', 
      'cite':'$index', 
      'default':'$authors: <i>$title</i>.{{ $publisher,} $year.}{ URL <a href="$url">$url</a>.}{ $note.}', 
      }

  defaulttags = {
      'YY':'??', 'authors':'', 'surname':'', 
      }

  ieeetr = {
      
      '@article':'$authors, “$title”, <i>$journal</i>, vol. $volume, no. $number, pp. $pages, $year.{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@book':'$authors, <i>$title</i>. $publisher, $year.{ URL <a href="$url">$url</a>.}{ $note.}', 
      'cite':'$index', 
      'default':'$authors, “$title”. $year.{ URL <a href="$url">$url</a>.}{ $note.}', 
      }

  plain = {
      
      '@article':'$authors. $title.{ <i>$journal</i>{, {$volume}{($number)}}{:$pages}{, $year}.}{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@book':'$authors. <i>$title</i>. $publisher,{ $month} $year.{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@incollection':'$authors. $title.{ In <i>$booktitle</i> {($editor, ed.)}.} $publisher,{ $month} $year.{ URL <a href="$url">$url</a>.}{ $note.}', 
      '@inproceedings':'$authors. $title. { <i>$booktitle</i>{, {$volume}{($number)}}{:$pages}{, $year}.}{ URL <a href="$url">$url</a>.}{ $note.}', 
      'cite':'$index', 
      'default':'{$authors. }$title.{{ $publisher,} $year.}{ URL <a href="$url">$url</a>.}{ $note.}', 
      }

  vancouver = {
      
      '@article':'$authors. $title. <i>$journal</i>, $year{;{<b>$volume</b>}{($number)}{:$pages}}.{ URL: <a href="$url">$url</a>.}{ $note.}', 
      '@book':'$authors. $title. {$publisher, }$year.{ URL: <a href="$url">$url</a>.}{ $note.}', 
      'cite':'$index', 
      'default':'$authors. $title; {$publisher, }$year.{ $howpublished.}{ URL: <a href="$url">$url</a>.}{ $note.}', 
      }

class BibTeXConfig(object):
  "Configuration class from elyxer.config file"

  replaced = {
      '--':'—', '..':'.', 
      }

class ContainerConfig(object):
  "Configuration class from elyxer.config file"

  endings = {
      'Align':'\\end_layout', 'BarredText':'\\bar', 
      'BoldText':'\\series', 'Cell':'</cell', 
      'ChangeDeleted':'\\change_unchanged', 
      'ChangeInserted':'\\change_unchanged', 'ColorText':'\\color', 
      'EmphaticText':'\\emph', 'Hfill':'\\hfill', 'Inset':'\\end_inset', 
      'Layout':'\\end_layout', 'LyXFooter':'\\end_document', 
      'LyXHeader':'\\end_header', 'Row':'</row', 'ShapedText':'\\shape', 
      'SizeText':'\\size', 'StrikeOut':'\\strikeout', 
      'TextFamily':'\\family', 'VersalitasText':'\\noun', 
      }

  extracttext = {
      'allowed':['StringContainer','Constant','FormulaConstant',], 
      'cloned':['',], 
      'extracted':['PlainLayout','TaggedText','Align','Caption','TextFamily','EmphaticText','VersalitasText','BarredText','SizeText','ColorText','LangLine','Formula','Bracket','RawText','BibTag','FormulaNumber','AlphaCommand','EmptyCommand','OneParamFunction','SymbolFunction','TextFunction','FontFunction','CombiningFunction','DecoratingFunction','FormulaSymbol','BracketCommand','TeXCode',], 
      }

  startendings = {
      '\\begin_deeper':'\\end_deeper', '\\begin_inset':'\\end_inset', 
      '\\begin_layout':'\\end_layout', 
      }

  starts = {
      '':'StringContainer', '#LyX':'BlackBox', '</lyxtabular':'BlackBox', 
      '<cell':'Cell', '<column':'Column', '<row':'Row', 
      '\\align':'Align', '\\bar':'BarredText', 
      '\\bar default':'BlackBox', '\\bar no':'BlackBox', 
      '\\begin_body':'BlackBox', '\\begin_deeper':'DeeperList', 
      '\\begin_document':'BlackBox', '\\begin_header':'LyXHeader', 
      '\\begin_inset Argument':'ShortTitle', 
      '\\begin_inset Box':'BoxInset', '\\begin_inset Branch':'Branch', 
      '\\begin_inset Caption':'Caption', 
      '\\begin_inset CommandInset bibitem':'BiblioEntry', 
      '\\begin_inset CommandInset bibtex':'BibTeX', 
      '\\begin_inset CommandInset citation':'BiblioCitation', 
      '\\begin_inset CommandInset href':'URL', 
      '\\begin_inset CommandInset include':'IncludeInset', 
      '\\begin_inset CommandInset index_print':'PrintIndex', 
      '\\begin_inset CommandInset label':'Label', 
      '\\begin_inset CommandInset line':'LineInset', 
      '\\begin_inset CommandInset nomencl_print':'PrintNomenclature', 
      '\\begin_inset CommandInset nomenclature':'NomenclatureEntry', 
      '\\begin_inset CommandInset ref':'Reference', 
      '\\begin_inset CommandInset toc':'TableOfContents', 
      '\\begin_inset ERT':'ERT', '\\begin_inset Flex':'FlexInset', 
      '\\begin_inset Flex Chunkref':'NewfangledChunkRef', 
      '\\begin_inset Flex Marginnote':'SideNote', 
      '\\begin_inset Flex Sidenote':'SideNote', 
      '\\begin_inset Flex URL':'FlexURL', '\\begin_inset Float':'Float', 
      '\\begin_inset FloatList':'ListOf', '\\begin_inset Foot':'Footnote', 
      '\\begin_inset Formula':'Formula', 
      '\\begin_inset FormulaMacro':'FormulaMacro', 
      '\\begin_inset Graphics':'Image', 
      '\\begin_inset Index':'IndexReference', 
      '\\begin_inset Info':'InfoInset', 
      '\\begin_inset LatexCommand bibitem':'BiblioEntry', 
      '\\begin_inset LatexCommand bibtex':'BibTeX', 
      '\\begin_inset LatexCommand cite':'BiblioCitation', 
      '\\begin_inset LatexCommand citealt':'BiblioCitation', 
      '\\begin_inset LatexCommand citep':'BiblioCitation', 
      '\\begin_inset LatexCommand citet':'BiblioCitation', 
      '\\begin_inset LatexCommand htmlurl':'URL', 
      '\\begin_inset LatexCommand index':'IndexReference', 
      '\\begin_inset LatexCommand label':'Label', 
      '\\begin_inset LatexCommand nomenclature':'NomenclatureEntry', 
      '\\begin_inset LatexCommand prettyref':'Reference', 
      '\\begin_inset LatexCommand printindex':'PrintIndex', 
      '\\begin_inset LatexCommand printnomenclature':'PrintNomenclature', 
      '\\begin_inset LatexCommand ref':'Reference', 
      '\\begin_inset LatexCommand tableofcontents':'TableOfContents', 
      '\\begin_inset LatexCommand url':'URL', 
      '\\begin_inset LatexCommand vref':'Reference', 
      '\\begin_inset Marginal':'SideNote', 
      '\\begin_inset Newline':'NewlineInset', 
      '\\begin_inset Newpage':'NewPageInset', '\\begin_inset Note':'Note', 
      '\\begin_inset OptArg':'ShortTitle', 
      '\\begin_inset Phantom':'PhantomText', 
      '\\begin_inset Quotes':'QuoteContainer', 
      '\\begin_inset Tabular':'Table', '\\begin_inset Text':'InsetText', 
      '\\begin_inset VSpace':'VerticalSpace', '\\begin_inset Wrap':'Wrap', 
      '\\begin_inset listings':'Listing', 
      '\\begin_inset script':'ScriptInset', '\\begin_inset space':'Space', 
      '\\begin_layout':'Layout', '\\begin_layout Abstract':'Abstract', 
      '\\begin_layout Author':'Author', 
      '\\begin_layout Bibliography':'Bibliography', 
      '\\begin_layout Chunk':'NewfangledChunk', 
      '\\begin_layout Description':'Description', 
      '\\begin_layout Enumerate':'ListItem', 
      '\\begin_layout Itemize':'ListItem', '\\begin_layout List':'List', 
      '\\begin_layout LyX-Code':'LyXCode', 
      '\\begin_layout Plain':'PlainLayout', 
      '\\begin_layout Standard':'StandardLayout', 
      '\\begin_layout Title':'Title', '\\begin_preamble':'LyXPreamble', 
      '\\change_deleted':'ChangeDeleted', 
      '\\change_inserted':'ChangeInserted', 
      '\\change_unchanged':'BlackBox', '\\color':'ColorText', 
      '\\color inherit':'BlackBox', '\\color none':'BlackBox', 
      '\\emph default':'BlackBox', '\\emph off':'BlackBox', 
      '\\emph on':'EmphaticText', '\\emph toggle':'EmphaticText', 
      '\\end_body':'LyXFooter', '\\family':'TextFamily', 
      '\\family default':'BlackBox', '\\family roman':'BlackBox', 
      '\\hfill':'Hfill', '\\labelwidthstring':'BlackBox', 
      '\\lang':'LangLine', '\\length':'InsetLength', 
      '\\lyxformat':'LyXFormat', '\\lyxline':'LyXLine', 
      '\\newline':'Newline', '\\newpage':'NewPage', 
      '\\noindent':'BlackBox', '\\noun default':'BlackBox', 
      '\\noun off':'BlackBox', '\\noun on':'VersalitasText', 
      '\\paragraph_spacing':'BlackBox', '\\series bold':'BoldText', 
      '\\series default':'BlackBox', '\\series medium':'BlackBox', 
      '\\shape':'ShapedText', '\\shape default':'BlackBox', 
      '\\shape up':'BlackBox', '\\size':'SizeText', 
      '\\size normal':'BlackBox', '\\start_of_appendix':'StartAppendix', 
      '\\strikeout default':'BlackBox', '\\strikeout on':'StrikeOut', 
      }

  string = {
      'startcommand':'\\', 
      }

  table = {
      'headers':['<lyxtabular','<features',], 
      }

class EscapeConfig(object):
  "Configuration class from elyxer.config file"

  chars = {
      '\n':'', ' -- ':' — ', ' --- ':' — ', '\'':'’', '`':'‘', 
      }

  commands = {
      '\\InsetSpace \\space{}':' ', '\\InsetSpace \\thinspace{}':' ', 
      '\\InsetSpace ~':' ', '\\SpecialChar \\-':'', 
      '\\SpecialChar \\@.':'.', '\\SpecialChar \\ldots{}':'…', 
      '\\SpecialChar \\menuseparator':' ▷ ', 
      '\\SpecialChar \\nobreakdash-':'-', '\\SpecialChar \\slash{}':'/', 
      '\\SpecialChar \\textcompwordmark{}':'', '\\backslash':'\\', 
      }

  entities = {
      '&':'&amp;', '<':'&lt;', '>':'&gt;', 
      }

  html = {
      '/>':'>', 
      }

  iso885915 = {
      ' ':'&nbsp;', ' ':'&emsp;', ' ':'&#8197;', 
      }

  nonunicode = {
      ' ':' ', 
      }

class FormulaConfig(object):
  "Configuration class from elyxer.config file"

  alphacommands = {
      '\\AA':'Å', '\\AE':'Æ', 
      '\\AmS':'<span class="versalitas">AmS</span>', '\\Angstroem':'Å', 
      '\\DH':'Ð', '\\Koppa':'Ϟ', '\\L':'Ł', '\\Micro':'µ', '\\O':'Ø', 
      '\\OE':'Œ', '\\Sampi':'Ϡ', '\\Stigma':'Ϛ', '\\TH':'Þ', 
      '\\aa':'å', '\\ae':'æ', '\\alpha':'α', '\\beta':'β', 
      '\\delta':'δ', '\\dh':'ð', '\\digamma':'ϝ', '\\epsilon':'ϵ', 
      '\\eta':'η', '\\eth':'ð', '\\gamma':'γ', '\\i':'ı', 
      '\\imath':'ı', '\\iota':'ι', '\\j':'ȷ', '\\jmath':'ȷ', 
      '\\kappa':'κ', '\\koppa':'ϟ', '\\l':'ł', '\\lambda':'λ', 
      '\\mu':'μ', '\\nu':'ν', '\\o':'ø', '\\oe':'œ', '\\omega':'ω', 
      '\\phi':'φ', '\\pi':'π', '\\psi':'ψ', '\\rho':'ρ', 
      '\\sampi':'ϡ', '\\sigma':'σ', '\\ss':'ß', '\\stigma':'ϛ', 
      '\\tau':'τ', '\\tcohm':'Ω', '\\textcrh':'ħ', '\\th':'þ', 
      '\\theta':'θ', '\\upsilon':'υ', '\\varDelta':'∆', 
      '\\varGamma':'Γ', '\\varLambda':'Λ', '\\varOmega':'Ω', 
      '\\varPhi':'Φ', '\\varPi':'Π', '\\varPsi':'Ψ', '\\varSigma':'Σ', 
      '\\varTheta':'Θ', '\\varUpsilon':'Υ', '\\varXi':'Ξ', 
      '\\varbeta':'ϐ', '\\varepsilon':'ε', '\\varkappa':'ϰ', 
      '\\varphi':'φ', '\\varpi':'ϖ', '\\varrho':'ϱ', '\\varsigma':'ς', 
      '\\vartheta':'ϑ', '\\xi':'ξ', '\\zeta':'ζ', 
      }

  array = {
      'begin':'\\begin', 'cellseparator':'&', 'end':'\\end', 
      'rowseparator':'\\\\', 
      }

  bigbrackets = {
      '(':['⎛','⎜','⎝',], ')':['⎞','⎟','⎠',], '[':['⎡','⎢','⎣',], 
      ']':['⎤','⎥','⎦',], '{':['⎧','⎪','⎨','⎩',], '|':['|',], 
      '}':['⎫','⎪','⎬','⎭',], '∥':['∥',], 
      }

  bigsymbols = {
      '∑':['⎲','⎳',], '∫':['⌠','⌡',], 
      }

  bracketcommands = {
      '\\left':'span class="symbol"', 
      '\\left.':'<span class="leftdot"></span>', 
      '\\middle':'span class="symbol"', '\\right':'span class="symbol"', 
      '\\right.':'<span class="rightdot"></span>', 
      }

  combiningfunctions = {
      '\\"':'̈', '\\\'':'́', '\\^':'̂', '\\`':'̀', '\\acute':'́', 
      '\\bar':'̄', '\\breve':'̆', '\\c':'̧', '\\check':'̌', 
      '\\dddot':'⃛', '\\ddot':'̈', '\\dot':'̇', '\\grave':'̀', 
      '\\hat':'̂', '\\mathring':'̊', '\\overleftarrow':'⃖', 
      '\\overrightarrow':'⃗', '\\r':'̊', '\\s':'̩', 
      '\\textcircled':'⃝', '\\textsubring':'̥', '\\tilde':'̃', 
      '\\v':'̌', '\\vec':'⃗', '\\~':'̃', 
      }

  commands = {
      '\\ ':' ', '\\!':'', '\\#':'#', '\\$':'$', '\\%':'%', 
      '\\&':'&', '\\,':' ', '\\:':' ', '\\;':' ', '\\AC':'∿', 
      '\\APLcomment':'⍝', '\\APLdownarrowbox':'⍗', '\\APLinput':'⍞', 
      '\\APLinv':'⌹', '\\APLleftarrowbox':'⍇', '\\APLlog':'⍟', 
      '\\APLrightarrowbox':'⍈', '\\APLuparrowbox':'⍐', '\\Box':'□', 
      '\\Bumpeq':'≎', '\\CIRCLE':'●', '\\Cap':'⋒', 
      '\\CapitalDifferentialD':'ⅅ', '\\CheckedBox':'☑', '\\Circle':'○', 
      '\\Coloneqq':'⩴', '\\ComplexI':'ⅈ', '\\ComplexJ':'ⅉ', 
      '\\Corresponds':'≙', '\\Cup':'⋓', '\\Delta':'Δ', '\\Diamond':'◇', 
      '\\Diamondblack':'◆', '\\Diamonddot':'⟐', '\\DifferentialD':'ⅆ', 
      '\\Downarrow':'⇓', '\\EUR':'€', '\\Euler':'ℇ', 
      '\\ExponetialE':'ⅇ', '\\Finv':'Ⅎ', '\\Game':'⅁', '\\Gamma':'Γ', 
      '\\Im':'ℑ', '\\Join':'⨝', '\\LEFTCIRCLE':'◖', '\\LEFTcircle':'◐', 
      '\\LHD':'◀', '\\Lambda':'Λ', '\\Lbag':'⟅', '\\Leftarrow':'⇐', 
      '\\Lleftarrow':'⇚', '\\Longleftarrow':'⟸', 
      '\\Longleftrightarrow':'⟺', '\\Longrightarrow':'⟹', '\\Lparen':'⦅', 
      '\\Lsh':'↰', '\\Mapsfrom':'⇐|', '\\Mapsto':'|⇒', '\\Omega':'Ω', 
      '\\P':'¶', '\\Phi':'Φ', '\\Pi':'Π', '\\Pr':'Pr', '\\Psi':'Ψ', 
      '\\Qoppa':'Ϙ', '\\RHD':'▶', '\\RIGHTCIRCLE':'◗', 
      '\\RIGHTcircle':'◑', '\\Rbag':'⟆', '\\Re':'ℜ', '\\Rparen':'⦆', 
      '\\Rrightarrow':'⇛', '\\Rsh':'↱', '\\S':'§', '\\Sigma':'Σ', 
      '\\Square':'☐', '\\Subset':'⋐', '\\Sun':'☉', '\\Supset':'⋑', 
      '\\Theta':'Θ', '\\Uparrow':'⇑', '\\Updownarrow':'⇕', 
      '\\Upsilon':'Υ', '\\Vdash':'⊩', '\\Vert':'∥', '\\Vvdash':'⊪', 
      '\\XBox':'☒', '\\Xi':'Ξ', '\\Yup':'⅄', '\\\\':'<br/>', 
      '\\_':'_', '\\aleph':'ℵ', '\\amalg':'∐', '\\anchor':'⚓', 
      '\\angle':'∠', '\\aquarius':'♒', '\\arccos':'arccos', 
      '\\arcsin':'arcsin', '\\arctan':'arctan', '\\arg':'arg', 
      '\\aries':'♈', '\\arrowbullet':'➢', '\\ast':'∗', '\\asymp':'≍', 
      '\\backepsilon':'∍', '\\backprime':'‵', '\\backsimeq':'⋍', 
      '\\backslash':'\\', '\\ballotx':'✗', '\\barwedge':'⊼', 
      '\\because':'∵', '\\beth':'ℶ', '\\between':'≬', '\\bigcap':'∩', 
      '\\bigcirc':'○', '\\bigcup':'∪', '\\bigodot':'⊙', 
      '\\bigoplus':'⊕', '\\bigotimes':'⊗', '\\bigsqcup':'⊔', 
      '\\bigstar':'★', '\\bigtriangledown':'▽', '\\bigtriangleup':'△', 
      '\\biguplus':'⊎', '\\bigvee':'∨', '\\bigwedge':'∧', 
      '\\biohazard':'☣', '\\blacklozenge':'⧫', '\\blacksmiley':'☻', 
      '\\blacksquare':'■', '\\blacktriangle':'▲', 
      '\\blacktriangledown':'▼', '\\blacktriangleleft':'◂', 
      '\\blacktriangleright':'▶', '\\blacktriangleup':'▴', '\\bot':'⊥', 
      '\\bowtie':'⋈', '\\box':'▫', '\\boxast':'⧆', '\\boxbar':'◫', 
      '\\boxbox':'⧈', '\\boxbslash':'⧅', '\\boxcircle':'⧇', 
      '\\boxdot':'⊡', '\\boxminus':'⊟', '\\boxplus':'⊞', 
      '\\boxslash':'⧄', '\\boxtimes':'⊠', '\\bullet':'•', 
      '\\bumpeq':'≏', '\\cancer':'♋', '\\cap':'∩', '\\capricornus':'♑', 
      '\\cat':'⁀', '\\cdot':'⋅', '\\cdots':'⋯', '\\cent':'¢', 
      '\\centerdot':'∙', '\\checkmark':'✓', '\\chi':'χ', '\\circ':'∘', 
      '\\circeq':'≗', '\\circlearrowleft':'↺', '\\circlearrowright':'↻', 
      '\\circledR':'®', '\\circledast':'⊛', '\\circledbslash':'⦸', 
      '\\circledcirc':'⊚', '\\circleddash':'⊝', '\\circledgtr':'⧁', 
      '\\circledless':'⧀', '\\clubsuit':'♣', '\\colon':': ', '\\coloneqq':'≔', 
      '\\complement':'∁', '\\cong':'≅', '\\coprod':'∐', 
      '\\copyright':'©', '\\cos':'cos', '\\cosh':'cosh', '\\cot':'cot', 
      '\\coth':'coth', '\\csc':'csc', '\\cup':'∪', '\\curlyvee':'⋎', 
      '\\curlywedge':'⋏', '\\curvearrowleft':'↶', 
      '\\curvearrowright':'↷', '\\dag':'†', '\\dagger':'†', 
      '\\daleth':'ℸ', '\\dashleftarrow':'⇠', '\\dashv':'⊣', 
      '\\ddag':'‡', '\\ddagger':'‡', '\\ddots':'⋱', '\\deg':'deg', 
      '\\det':'det', '\\diagdown':'╲', '\\diagup':'╱', 
      '\\diameter':'⌀', '\\diamond':'◇', '\\diamondsuit':'♦', 
      '\\dim':'dim', '\\div':'÷', '\\divideontimes':'⋇', 
      '\\dotdiv':'∸', '\\doteq':'≐', '\\doteqdot':'≑', '\\dotplus':'∔', 
      '\\dots':'…', '\\doublebarwedge':'⌆', '\\downarrow':'↓', 
      '\\downdownarrows':'⇊', '\\downharpoonleft':'⇃', 
      '\\downharpoonright':'⇂', '\\dsub':'⩤', '\\earth':'♁', 
      '\\eighthnote':'♪', '\\ell':'ℓ', '\\emptyset':'∅', 
      '\\eqcirc':'≖', '\\eqcolon':'≕', '\\eqsim':'≂', '\\euro':'€', 
      '\\exists':'∃', '\\exp':'exp', '\\fallingdotseq':'≒', 
      '\\fcmp':'⨾', '\\female':'♀', '\\flat':'♭', '\\forall':'∀', 
      '\\fourth':'⁗', '\\frown':'⌢', '\\frownie':'☹', '\\gcd':'gcd', 
      '\\gemini':'♊', '\\geq)':'≥', '\\geqq':'≧', '\\geqslant':'≥', 
      '\\gets':'←', '\\gg':'≫', '\\ggg':'⋙', '\\gimel':'ℷ', 
      '\\gneqq':'≩', '\\gnsim':'⋧', '\\gtrdot':'⋗', '\\gtreqless':'⋚', 
      '\\gtreqqless':'⪌', '\\gtrless':'≷', '\\gtrsim':'≳', 
      '\\guillemotleft':'«', '\\guillemotright':'»', '\\hbar':'ℏ', 
      '\\heartsuit':'♥', '\\hfill':'<span class="hfill"> </span>', 
      '\\hom':'hom', '\\hookleftarrow':'↩', '\\hookrightarrow':'↪', 
      '\\hslash':'ℏ', '\\idotsint':'<span class="bigsymbol">∫⋯∫</span>', 
      '\\iiint':'<span class="bigsymbol">∭</span>', 
      '\\iint':'<span class="bigsymbol">∬</span>', '\\imath':'ı', 
      '\\inf':'inf', '\\infty':'∞', '\\intercal':'⊺', 
      '\\interleave':'⫴', '\\invamp':'⅋', '\\invneg':'⌐', 
      '\\jmath':'ȷ', '\\jupiter':'♃', '\\ker':'ker', '\\land':'∧', 
      '\\landupint':'<span class="bigsymbol">∱</span>', '\\lang':'⟪', 
      '\\langle':'⟨', '\\lblot':'⦉', '\\lbrace':'{', '\\lbrace)':'{', 
      '\\lbrack':'[', '\\lceil':'⌈', '\\ldots':'…', '\\leadsto':'⇝', 
      '\\leftarrow)':'←', '\\leftarrowtail':'↢', '\\leftarrowtobar':'⇤', 
      '\\leftharpoondown':'↽', '\\leftharpoonup':'↼', 
      '\\leftleftarrows':'⇇', '\\leftleftharpoons':'⥢', '\\leftmoon':'☾', 
      '\\leftrightarrow':'↔', '\\leftrightarrows':'⇆', 
      '\\leftrightharpoons':'⇋', '\\leftthreetimes':'⋋', '\\leo':'♌', 
      '\\leq)':'≤', '\\leqq':'≦', '\\leqslant':'≤', '\\lessdot':'⋖', 
      '\\lesseqgtr':'⋛', '\\lesseqqgtr':'⪋', '\\lessgtr':'≶', 
      '\\lesssim':'≲', '\\lfloor':'⌊', '\\lg':'lg', '\\lgroup':'⟮', 
      '\\lhd':'⊲', '\\libra':'♎', '\\lightning':'↯', '\\limg':'⦇', 
      '\\liminf':'liminf', '\\limsup':'limsup', '\\ll':'≪', 
      '\\llbracket':'⟦', '\\llcorner':'⌞', '\\lll':'⋘', '\\ln':'ln', 
      '\\lneqq':'≨', '\\lnot':'¬', '\\lnsim':'⋦', '\\log':'log', 
      '\\longleftarrow':'⟵', '\\longleftrightarrow':'⟷', 
      '\\longmapsto':'⟼', '\\longrightarrow':'⟶', '\\looparrowleft':'↫', 
      '\\looparrowright':'↬', '\\lor':'∨', '\\lozenge':'◊', 
      '\\lrcorner':'⌟', '\\ltimes':'⋉', '\\lyxlock':'', '\\male':'♂', 
      '\\maltese':'✠', '\\mapsfrom':'↤', '\\mapsto':'↦', 
      '\\mathcircumflex':'^', '\\max':'max', '\\measuredangle':'∡', 
      '\\medbullet':'⚫', '\\medcirc':'⚪', '\\mercury':'☿', '\\mho':'℧', 
      '\\mid':'∣', '\\min':'min', '\\models':'⊨', '\\mp':'∓', 
      '\\multimap':'⊸', '\\nLeftarrow':'⇍', '\\nLeftrightarrow':'⇎', 
      '\\nRightarrow':'⇏', '\\nVDash':'⊯', '\\nabla':'∇', 
      '\\napprox':'≉', '\\natural':'♮', '\\ncong':'≇', '\\nearrow':'↗', 
      '\\neg':'¬', '\\neg)':'¬', '\\neptune':'♆', '\\nequiv':'≢', 
      '\\newline':'<br/>', '\\nexists':'∄', '\\ngeqslant':'≱', 
      '\\ngtr':'≯', '\\ngtrless':'≹', '\\ni':'∋', '\\ni)':'∋', 
      '\\nleftarrow':'↚', '\\nleftrightarrow':'↮', '\\nleqslant':'≰', 
      '\\nless':'≮', '\\nlessgtr':'≸', '\\nmid':'∤', '\\nolimits':'', 
      '\\nonumber':'', '\\not':'¬', '\\not<':'≮', '\\not=':'≠', 
      '\\not>':'≯', '\\notbackslash':'⍀', '\\notin':'∉', '\\notni':'∌', 
      '\\notslash':'⌿', '\\nparallel':'∦', '\\nprec':'⊀', 
      '\\nrightarrow':'↛', '\\nsim':'≁', '\\nsimeq':'≄', 
      '\\nsqsubset':'⊏̸', '\\nsubseteq':'⊈', '\\nsucc':'⊁', 
      '\\nsucccurlyeq':'⋡', '\\nsupset':'⊅', '\\nsupseteq':'⊉', 
      '\\ntriangleleft':'⋪', '\\ntrianglelefteq':'⋬', 
      '\\ntriangleright':'⋫', '\\ntrianglerighteq':'⋭', '\\nvDash':'⊭', 
      '\\nvdash':'⊬', '\\nwarrow':'↖', '\\odot':'⊙', 
      '\\officialeuro':'€', '\\oiiint':'<span class="bigsymbol">∰</span>', 
      '\\oiint':'<span class="bigsymbol">∯</span>', 
      '\\oint':'<span class="bigsymbol">∮</span>', 
      '\\ointclockwise':'<span class="bigsymbol">∲</span>', 
      '\\ointctrclockwise':'<span class="bigsymbol">∳</span>', 
      '\\ominus':'⊖', '\\oplus':'⊕', '\\oslash':'⊘', '\\otimes':'⊗', 
      '\\owns':'∋', '\\parallel':'∥', '\\partial':'∂', '\\pencil':'✎', 
      '\\perp':'⊥', '\\pisces':'♓', '\\pitchfork':'⋔', '\\pluto':'♇', 
      '\\pm':'±', '\\pointer':'➪', '\\pointright':'☞', '\\pounds':'£', 
      '\\prec':'≺', '\\preccurlyeq':'≼', '\\preceq':'≼', 
      '\\precsim':'≾', '\\prime':'′', '\\prompto':'∝', '\\qoppa':'ϙ', 
      '\\qquad':'  ', '\\quad':' ', '\\quarternote':'♩', 
      '\\radiation':'☢', '\\rang':'⟫', '\\rangle':'⟩', '\\rblot':'⦊', 
      '\\rbrace':'}', '\\rbrace)':'}', '\\rbrack':']', '\\rceil':'⌉', 
      '\\recycle':'♻', '\\rfloor':'⌋', '\\rgroup':'⟯', '\\rhd':'⊳', 
      '\\rightangle':'∟', '\\rightarrow)':'→', '\\rightarrowtail':'↣', 
      '\\rightarrowtobar':'⇥', '\\rightharpoondown':'⇁', 
      '\\rightharpoonup':'⇀', '\\rightharpooondown':'⇁', 
      '\\rightharpooonup':'⇀', '\\rightleftarrows':'⇄', 
      '\\rightleftharpoons':'⇌', '\\rightmoon':'☽', 
      '\\rightrightarrows':'⇉', '\\rightrightharpoons':'⥤', 
      '\\rightthreetimes':'⋌', '\\rimg':'⦈', '\\risingdotseq':'≓', 
      '\\rrbracket':'⟧', '\\rsub':'⩥', '\\rtimes':'⋊', 
      '\\sagittarius':'♐', '\\saturn':'♄', '\\scorpio':'♏', 
      '\\searrow':'↘', '\\sec':'sec', '\\second':'″', '\\setminus':'∖', 
      '\\sharp':'♯', '\\simeq':'≃', '\\sin':'sin', '\\sinh':'sinh', 
      '\\sixteenthnote':'♬', '\\skull':'☠', '\\slash':'∕', 
      '\\smallsetminus':'∖', '\\smalltriangledown':'▿', 
      '\\smalltriangleleft':'◃', '\\smalltriangleright':'▹', 
      '\\smalltriangleup':'▵', '\\smile':'⌣', '\\smiley':'☺', 
      '\\spadesuit':'♠', '\\spddot':'¨', '\\sphat':'', 
      '\\sphericalangle':'∢', '\\spot':'⦁', '\\sptilde':'~', 
      '\\sqcap':'⊓', '\\sqcup':'⊔', '\\sqsubset':'⊏', 
      '\\sqsubseteq':'⊑', '\\sqsupset':'⊐', '\\sqsupseteq':'⊒', 
      '\\square':'□', '\\sslash':'⫽', '\\star':'⋆', '\\steaming':'☕', 
      '\\subseteqq':'⫅', '\\subsetneqq':'⫋', '\\succ':'≻', 
      '\\succcurlyeq':'≽', '\\succeq':'≽', '\\succnsim':'⋩', 
      '\\succsim':'≿', '\\sun':'☼', '\\sup':'sup', '\\supseteqq':'⫆', 
      '\\supsetneqq':'⫌', '\\surd':'√', '\\swarrow':'↙', 
      '\\swords':'⚔', '\\talloblong':'⫾', '\\tan':'tan', 
      '\\tanh':'tanh', '\\taurus':'♉', '\\textasciicircum':'^', 
      '\\textasciitilde':'~', '\\textbackslash':'\\', 
      '\\textcopyright':'©\'', '\\textdegree':'°', '\\textellipsis':'…', 
      '\\textemdash':'—', '\\textendash':'—', '\\texteuro':'€', 
      '\\textgreater':'>', '\\textless':'<', '\\textordfeminine':'ª', 
      '\\textordmasculine':'º', '\\textquotedblleft':'“', 
      '\\textquotedblright':'”', '\\textquoteright':'’', 
      '\\textregistered':'®', '\\textrightarrow':'→', 
      '\\textsection':'§', '\\texttrademark':'™', 
      '\\texttwosuperior':'²', '\\textvisiblespace':' ', 
      '\\therefore':'∴', '\\third':'‴', '\\top':'⊤', '\\triangle':'△', 
      '\\triangleleft':'⊲', '\\trianglelefteq':'⊴', '\\triangleq':'≜', 
      '\\triangleright':'▷', '\\trianglerighteq':'⊵', 
      '\\twoheadleftarrow':'↞', '\\twoheadrightarrow':'↠', 
      '\\twonotes':'♫', '\\udot':'⊍', '\\ulcorner':'⌜', '\\unlhd':'⊴', 
      '\\unrhd':'⊵', '\\unrhl':'⊵', '\\uparrow':'↑', 
      '\\updownarrow':'↕', '\\upharpoonleft':'↿', '\\upharpoonright':'↾', 
      '\\uplus':'⊎', '\\upuparrows':'⇈', '\\uranus':'♅', 
      '\\urcorner':'⌝', '\\vDash':'⊨', '\\varclubsuit':'♧', 
      '\\vardiamondsuit':'♦', '\\varheartsuit':'♥', '\\varnothing':'∅', 
      '\\varspadesuit':'♤', '\\vdash':'⊢', '\\vdots':'⋮', '\\vee':'∨', 
      '\\vee)':'∨', '\\veebar':'⊻', '\\vert':'∣', '\\virgo':'♍', 
      '\\warning':'⚠', '\\wasylozenge':'⌑', '\\wedge':'∧', 
      '\\wedge)':'∧', '\\wp':'℘', '\\wr':'≀', '\\yen':'¥', 
      '\\yinyang':'☯', '\\{':'{', '\\|':'∥', '\\}':'}', 
      }

  decoratedcommand = {
      
      }

  decoratingfunctions = {
      '\\overleftarrow':'⟵', '\\overrightarrow':'⟶', '\\widehat':'^', 
      }

  endings = {
      'bracket':'}', 'complex':'\\]', 'endafter':'}', 
      'endbefore':'\\end{', 'squarebracket':']', 
      }

  environments = {
      'align':['r','l',], 'eqnarray':['r','c','l',], 
      'gathered':['l','l',], 
      }

  fontfunctions = {
      '\\boldsymbol':'b', '\\mathbb':'span class="blackboard"', 
      '\\mathbb{A}':'𝔸', '\\mathbb{B}':'𝔹', '\\mathbb{C}':'ℂ', 
      '\\mathbb{D}':'𝔻', '\\mathbb{E}':'𝔼', '\\mathbb{F}':'𝔽', 
      '\\mathbb{G}':'𝔾', '\\mathbb{H}':'ℍ', '\\mathbb{J}':'𝕁', 
      '\\mathbb{K}':'𝕂', '\\mathbb{L}':'𝕃', '\\mathbb{N}':'ℕ', 
      '\\mathbb{O}':'𝕆', '\\mathbb{P}':'ℙ', '\\mathbb{Q}':'ℚ', 
      '\\mathbb{R}':'ℝ', '\\mathbb{S}':'𝕊', '\\mathbb{T}':'𝕋', 
      '\\mathbb{W}':'𝕎', '\\mathbb{Z}':'ℤ', '\\mathbf':'b', 
      '\\mathcal':'span class="scriptfont"', '\\mathcal{B}':'ℬ', 
      '\\mathcal{E}':'ℰ', '\\mathcal{F}':'ℱ', '\\mathcal{H}':'ℋ', 
      '\\mathcal{I}':'ℐ', '\\mathcal{L}':'ℒ', '\\mathcal{M}':'ℳ', 
      '\\mathcal{R}':'ℛ', '\\mathfrak':'span class="fraktur"', 
      '\\mathfrak{C}':'ℭ', '\\mathfrak{F}':'𝔉', '\\mathfrak{H}':'ℌ', 
      '\\mathfrak{I}':'ℑ', '\\mathfrak{R}':'ℜ', '\\mathfrak{Z}':'ℨ', 
      '\\mathit':'i', '\\mathring{A}':'Å', '\\mathring{U}':'Ů', 
      '\\mathring{a}':'å', '\\mathring{u}':'ů', '\\mathring{w}':'ẘ', 
      '\\mathring{y}':'ẙ', '\\mathrm':'span class="mathrm"', 
      '\\mathscr':'span class="scriptfont"', '\\mathscr{B}':'ℬ', 
      '\\mathscr{E}':'ℰ', '\\mathscr{F}':'ℱ', '\\mathscr{H}':'ℋ', 
      '\\mathscr{I}':'ℐ', '\\mathscr{L}':'ℒ', '\\mathscr{M}':'ℳ', 
      '\\mathscr{R}':'ℛ', '\\mathsf':'span class="mathsf"', 
      '\\mathtt':'tt', 
      }

  hybridfunctions = {
      '\\addcontentsline':['{$p!}{$q!}{$r!}','f0{}','ignored',], 
      '\\addtocontents':['{$p!}{$q!}','f0{}','ignored',], 
      '\\backmatter':['','f0{}','ignored',], 
      '\\binom':['{$1}{$2}','f2{(}f0{f1{$1}f1{$2}}f2{)}','span class="binom"','span class="binomstack"','span class="bigsymbol"',], 
      '\\boxed':['{$1}','f0{$1}','span class="boxed"',], 
      '\\cfrac':['[$p!]{$1}{$2}','f0{f3{(}f1{$1}f3{)/(}f2{$2}f3{)}}','span class="fullfraction"','span class="numerator align-$p"','span class="denominator"','span class="ignored"',], 
      '\\color':['{$p!}{$1}','f0{$1}','span style="color: $p;"',], 
      '\\colorbox':['{$p!}{$1}','f0{$1}','span class="colorbox" style="background: $p;"',], 
      '\\dbinom':['{$1}{$2}','(f0{f1{f2{$1}}f1{f2{ }}f1{f2{$2}}})','span class="binomial"','span class="binomrow"','span class="binomcell"',], 
      '\\dfrac':['{$1}{$2}','f0{f3{(}f1{$1}f3{)/(}f2{$2}f3{)}}','span class="fullfraction"','span class="numerator"','span class="denominator"','span class="ignored"',], 
      '\\displaystyle':['{$1}','f0{$1}','span class="displaystyle"',], 
      '\\fancyfoot':['[$p!]{$q!}','f0{}','ignored',], 
      '\\fancyhead':['[$p!]{$q!}','f0{}','ignored',], 
      '\\fbox':['{$1}','f0{$1}','span class="fbox"',], 
      '\\fboxrule':['{$p!}','f0{}','ignored',], 
      '\\fboxsep':['{$p!}','f0{}','ignored',], 
      '\\fcolorbox':['{$p!}{$q!}{$1}','f0{$1}','span class="boxed" style="border-color: $p; background: $q;"',], 
      '\\frac':['{$1}{$2}','f0{f3{(}f1{$1}f3{)/(}f2{$2}f3{)}}','span class="fraction"','span class="numerator"','span class="denominator"','span class="ignored"',], 
      '\\framebox':['[$p!][$q!]{$1}','f0{$1}','span class="framebox align-$q" style="width: $p;"',], 
      '\\frontmatter':['','f0{}','ignored',], 
      '\\href':['[$o]{$u!}{$t!}','f0{$t}','a href="$u"',], 
      '\\hspace':['{$p!}','f0{ }','span class="hspace" style="width: $p;"',], 
      '\\leftroot':['{$p!}','f0{ }','span class="leftroot" style="width: $p;px"',], 
      '\\mainmatter':['','f0{}','ignored',], 
      '\\markboth':['{$p!}{$q!}','f0{}','ignored',], 
      '\\markright':['{$p!}','f0{}','ignored',], 
      '\\nicefrac':['{$1}{$2}','f0{f1{$1}⁄f2{$2}}','span class="fraction"','sup class="numerator"','sub class="denominator"','span class="ignored"',], 
      '\\parbox':['[$p!]{$w!}{$1}','f0{1}','div class="Boxed" style="width: $w;"',], 
      '\\raisebox':['{$p!}{$1}','f0{$1.font}','span class="raisebox" style="vertical-align: $p;"',], 
      '\\renewenvironment':['{$1!}{$2!}{$3!}','',], 
      '\\rule':['[$v!]{$w!}{$h!}','f0/','hr class="line" style="width: $w; height: $h;"',], 
      '\\scriptscriptstyle':['{$1}','f0{$1}','span class="scriptscriptstyle"',], 
      '\\scriptstyle':['{$1}','f0{$1}','span class="scriptstyle"',], 
      '\\sqrt':['[$0]{$1}','f0{f1{$0}f2{√}f4{(}f3{$1}f4{)}}','span class="sqrt"','sup class="root"','span class="radical"','span class="root"','span class="ignored"',], 
      '\\stackrel':['{$1}{$2}','f0{f1{$1}f2{$2}}','span class="stackrel"','span class="upstackrel"','span class="downstackrel"',], 
      '\\tbinom':['{$1}{$2}','(f0{f1{f2{$1}}f1{f2{ }}f1{f2{$2}}})','span class="binomial"','span class="binomrow"','span class="binomcell"',], 
      '\\textcolor':['{$p!}{$1}','f0{$1}','span style="color: $p;"',], 
      '\\textstyle':['{$1}','f0{$1}','span class="textstyle"',], 
      '\\thispagestyle':['{$p!}','f0{}','ignored',], 
      '\\unit':['[$0]{$1}','$0f0{$1.font}','span class="unit"',], 
      '\\unitfrac':['[$0]{$1}{$2}','$0f0{f1{$1.font}⁄f2{$2.font}}','span class="fraction"','sup class="unit"','sub class="unit"',], 
      '\\uproot':['{$p!}','f0{ }','span class="uproot" style="width: $p;px"',], 
      '\\url':['{$u!}','f0{$u}','a href="$u"',], 
      '\\vspace':['{$p!}','f0{ }','span class="vspace" style="height: $p;"',], 
      }

  hybridsizes = {
      '\\binom':'$1+$2', '\\cfrac':'$1+$2', '\\dbinom':'$1+$2+1', 
      '\\dfrac':'$1+$2', '\\frac':'$1+$2', '\\tbinom':'$1+$2+1', 
      }

  labelfunctions = {
      '\\label':'a name="#"', 
      }

  limitcommands = {
      '\\biginterleave':'⫼', '\\bigsqcap':'⨅', '\\fint':'⨏', 
      '\\iiiint':'⨌', '\\int':'∫', '\\intop':'∫', '\\lim':'lim', 
      '\\prod':'∏', '\\smallint':'∫', '\\sqint':'⨖', '\\sum':'∑', 
      '\\varointclockwise':'∲', '\\varprod':'⨉', '\\zcmp':'⨟', 
      '\\zhide':'⧹', '\\zpipe':'⨠', '\\zproject':'⨡', 
      }

  misccommands = {
      '\\limits':'LimitPreviousCommand', '\\newcommand':'MacroDefinition', 
      '\\renewcommand':'MacroDefinition', 
      '\\setcounter':'SetCounterFunction', '\\tag':'FormulaTag', 
      '\\tag*':'FormulaTag', '\\today':'TodayCommand', 
      }

  modified = {
      '\n':'', ' ':'', '$':'', '&':'	', '\'':'’', '+':' + ', 
      ',':', ', '-':' − ', '/':' ⁄ ', ':':' : ', '<':' &lt; ', 
      '=':' = ', '>':' &gt; ', '@':'', '~':'', 
      }

  onefunctions = {
      '\\Big':'span class="bigsymbol"', '\\Bigg':'span class="hugesymbol"', 
      '\\bar':'span class="bar"', '\\begin{array}':'span class="arraydef"', 
      '\\big':'span class="symbol"', '\\bigg':'span class="largesymbol"', 
      '\\bigl':'span class="bigsymbol"', '\\bigr':'span class="bigsymbol"', 
      '\\centering':'span class="align-center"', 
      '\\ensuremath':'span class="ensuremath"', 
      '\\hphantom':'span class="phantom"', 
      '\\noindent':'span class="noindent"', 
      '\\overbrace':'span class="overbrace"', 
      '\\overline':'span class="overline"', 
      '\\phantom':'span class="phantom"', 
      '\\underbrace':'span class="underbrace"', '\\underline':'u', 
      '\\vphantom':'span class="phantom"', 
      }

  spacedcommands = {
      '\\Bot':'⫫', '\\Doteq':'≑', '\\DownArrowBar':'⤓', 
      '\\DownLeftTeeVector':'⥞', '\\DownLeftVectorBar':'⥖', 
      '\\DownRightTeeVector':'⥟', '\\DownRightVectorBar':'⥗', 
      '\\Equal':'⩵', '\\LeftArrowBar':'⇤', '\\LeftDownTeeVector':'⥡', 
      '\\LeftDownVectorBar':'⥙', '\\LeftTeeVector':'⥚', 
      '\\LeftTriangleBar':'⧏', '\\LeftUpTeeVector':'⥠', 
      '\\LeftUpVectorBar':'⥘', '\\LeftVectorBar':'⥒', 
      '\\Leftrightarrow':'⇔', '\\Longmapsfrom':'⟽', '\\Longmapsto':'⟾', 
      '\\MapsDown':'↧', '\\MapsUp':'↥', '\\Nearrow':'⇗', 
      '\\NestedGreaterGreater':'⪢', '\\NestedLessLess':'⪡', 
      '\\NotGreaterLess':'≹', '\\NotGreaterTilde':'≵', 
      '\\NotLessTilde':'≴', '\\Nwarrow':'⇖', '\\Proportion':'∷', 
      '\\RightArrowBar':'⇥', '\\RightDownTeeVector':'⥝', 
      '\\RightDownVectorBar':'⥕', '\\RightTeeVector':'⥛', 
      '\\RightTriangleBar':'⧐', '\\RightUpTeeVector':'⥜', 
      '\\RightUpVectorBar':'⥔', '\\RightVectorBar':'⥓', 
      '\\Rightarrow':'⇒', '\\Same':'⩶', '\\Searrow':'⇘', 
      '\\Swarrow':'⇙', '\\Top':'⫪', '\\UpArrowBar':'⤒', '\\VDash':'⊫', 
      '\\approx':'≈', '\\approxeq':'≊', '\\backsim':'∽', '\\barin':'⋶', 
      '\\barleftharpoon':'⥫', '\\barrightharpoon':'⥭', '\\bij':'⤖', 
      '\\coloneq':'≔', '\\corresponds':'≙', '\\curlyeqprec':'⋞', 
      '\\curlyeqsucc':'⋟', '\\dashrightarrow':'⇢', '\\dlsh':'↲', 
      '\\downdownharpoons':'⥥', '\\downuparrows':'⇵', 
      '\\downupharpoons':'⥯', '\\drsh':'↳', '\\eqslantgtr':'⪖', 
      '\\eqslantless':'⪕', '\\equiv':'≡', '\\ffun':'⇻', '\\finj':'⤕', 
      '\\ge':'≥', '\\geq':'≥', '\\ggcurly':'⪼', '\\gnapprox':'⪊', 
      '\\gneq':'⪈', '\\gtrapprox':'⪆', '\\hash':'⋕', '\\iddots':'⋰', 
      '\\implies':' ⇒ ', '\\in':'∈', '\\le':'≤', '\\leftarrow':'←', 
      '\\leftarrowtriangle':'⇽', '\\leftbarharpoon':'⥪', 
      '\\leftrightarrowtriangle':'⇿', '\\leftrightharpoon':'⥊', 
      '\\leftrightharpoondown':'⥐', '\\leftrightharpoonup':'⥎', 
      '\\leftrightsquigarrow':'↭', '\\leftslice':'⪦', 
      '\\leftsquigarrow':'⇜', '\\leftupdownharpoon':'⥑', '\\leq':'≤', 
      '\\lessapprox':'⪅', '\\llcurly':'⪻', '\\lnapprox':'⪉', 
      '\\lneq':'⪇', '\\longmapsfrom':'⟻', '\\multimapboth':'⧟', 
      '\\multimapdotbothA':'⊶', '\\multimapdotbothB':'⊷', 
      '\\multimapinv':'⟜', '\\nVdash':'⊮', '\\ne':'≠', '\\neq':'≠', 
      '\\ngeq':'≱', '\\nleq':'≰', '\\nni':'∌', '\\not\\in':'∉', 
      '\\notasymp':'≭', '\\npreceq':'⋠', '\\nsqsubseteq':'⋢', 
      '\\nsqsupseteq':'⋣', '\\nsubset':'⊄', '\\nsucceq':'⋡', 
      '\\pfun':'⇸', '\\pinj':'⤔', '\\precapprox':'⪷', '\\preceqq':'⪳', 
      '\\precnapprox':'⪹', '\\precnsim':'⋨', '\\propto':'∝', 
      '\\psur':'⤀', '\\rightarrow':'→', '\\rightarrowtriangle':'⇾', 
      '\\rightbarharpoon':'⥬', '\\rightleftharpoon':'⥋', 
      '\\rightslice':'⪧', '\\rightsquigarrow':'⇝', 
      '\\rightupdownharpoon':'⥏', '\\sim':'~', '\\strictfi':'⥼', 
      '\\strictif':'⥽', '\\subset':'⊂', '\\subseteq':'⊆', 
      '\\subsetneq':'⊊', '\\succapprox':'⪸', '\\succeqq':'⪴', 
      '\\succnapprox':'⪺', '\\supset':'⊃', '\\supseteq':'⊇', 
      '\\supsetneq':'⊋', '\\times':'×', '\\to':'→', 
      '\\updownarrows':'⇅', '\\updownharpoons':'⥮', '\\upupharpoons':'⥣', 
      '\\vartriangleleft':'⊲', '\\vartriangleright':'⊳', 
      }

  starts = {
      'beginafter':'}', 'beginbefore':'\\begin{', 'bracket':'{', 
      'command':'\\', 'comment':'%', 'complex':'\\[', 'simple':'$', 
      'squarebracket':'[', 'unnumbered':'*', 
      }

  symbolfunctions = {
      '^':'sup', '_':'sub', 
      }

  textfunctions = {
      '\\mbox':'span class="mbox"', '\\text':'span class="text"', 
      '\\textbf':'b', '\\textipa':'span class="textipa"', '\\textit':'i', 
      '\\textnormal':'span class="textnormal"', 
      '\\textrm':'span class="textrm"', 
      '\\textsc':'span class="versalitas"', 
      '\\textsf':'span class="textsf"', '\\textsl':'i', '\\texttt':'tt', 
      '\\textup':'span class="normal"', 
      }

  unmodified = {
      
      'characters':['.','*','€','(',')','[',']','·','!',';','|','§','"',], 
      }

  urls = {
      'googlecharts':'http://chart.googleapis.com/chart?cht=tx&chl=', 
      }

class GeneralConfig(object):
  "Configuration class from elyxer.config file"

  version = {
      'date':'2015-02-26', 'lyxformat':'413', 'number':'1.2.5', 
      }

class HeaderConfig(object):
  "Configuration class from elyxer.config file"

  parameters = {
      'beginpreamble':'\\begin_preamble', 'branch':'\\branch', 
      'documentclass':'\\textclass', 'endbranch':'\\end_branch', 
      'endpreamble':'\\end_preamble', 'language':'\\language', 
      'lstset':'\\lstset', 'outputchanges':'\\output_changes', 
      'paragraphseparation':'\\paragraph_separation', 
      'pdftitle':'\\pdf_title', 'secnumdepth':'\\secnumdepth', 
      'tocdepth':'\\tocdepth', 
      }

  styles = {
      
      'article':['article','aastex','aapaper','acmsiggraph','sigplanconf','achemso','amsart','apa','arab-article','armenian-article','article-beamer','chess','dtk','elsarticle','heb-article','IEEEtran','iopart','kluwer','scrarticle-beamer','scrartcl','extarticle','paper','mwart','revtex4','spie','svglobal3','ltugboat','agu-dtd','jgrga','agums','entcs','egs','ijmpc','ijmpd','singlecol-new','doublecol-new','isprs','tarticle','jsarticle','jarticle','jss','literate-article','siamltex','cl2emult','llncs','svglobal','svjog','svprobth',], 
      'book':['book','amsbook','scrbook','extbook','tufte-book','report','extreport','scrreprt','memoir','tbook','jsbook','jbook','mwbk','svmono','svmult','treport','jreport','mwrep',], 
      }

class ImageConfig(object):
  "Configuration class from elyxer.config file"

  converters = {
      
      'imagemagick':'convert[ -density $scale][ -define $format:use-cropbox=true] "$input" "$output"', 
      'inkscape':'inkscape "$input" --export-png="$output"', 
      'lyx':'lyx -C "$input" "$output"', 
      }

  cropboxformats = {
      '.eps':'ps', '.pdf':'pdf', '.ps':'ps', 
      }

  formats = {
      'default':'.png', 'vector':['.svg','.eps',], 
      }

class LayoutConfig(object):
  "Configuration class from elyxer.config file"

  groupable = {
      
      'allowed':['StringContainer','Constant','TaggedText','Align','TextFamily','EmphaticText','VersalitasText','BarredText','SizeText','ColorText','LangLine','Formula',], 
      }

class NewfangleConfig(object):
  "Configuration class from elyxer.config file"

  constants = {
      'chunkref':'chunkref{', 'endcommand':'}', 'endmark':'&gt;', 
      'startcommand':'\\', 'startmark':'=&lt;', 
      }

class NumberingConfig(object):
  "Configuration class from elyxer.config file"

  layouts = {
      
      'ordered':['Chapter','Section','Subsection','Subsubsection','Paragraph',], 
      'roman':['Part','Book',], 
      }

  sequence = {
      'symbols':['*','**','†','‡','§','§§','¶','¶¶','#','##',], 
      }

class StyleConfig(object):
  "Configuration class from elyxer.config file"

  hspaces = {
      '\\enskip{}':' ', '\\hfill{}':'<span class="hfill"> </span>', 
      '\\hspace*{\\fill}':' ', '\\hspace*{}':'', '\\hspace{}':' ', 
      '\\negthinspace{}':'', '\\qquad{}':'  ', '\\quad{}':' ', 
      '\\space{}':' ', '\\thinspace{}':' ', '~':' ', 
      }

  quotes = {
      'ald':'»', 'als':'›', 'ard':'«', 'ars':'‹', 'eld':'&ldquo;', 
      'els':'&lsquo;', 'erd':'&rdquo;', 'ers':'&rsquo;', 'fld':'«', 
      'fls':'‹', 'frd':'»', 'frs':'›', 'gld':'„', 'gls':'‚', 
      'grd':'“', 'grs':'‘', 'pld':'„', 'pls':'‚', 'prd':'”', 
      'prs':'’', 'sld':'”', 'srd':'”', 
      }

  referenceformats = {
      'eqref':'(@↕)', 'formatted':'¶↕', 'nameref':'$↕', 'pageref':'#↕', 
      'ref':'@↕', 'vpageref':'on-page#↕', 'vref':'@on-page#↕', 
      }

  size = {
      'ignoredtexts':['col','text','line','page','theight','pheight',], 
      }

  vspaces = {
      'bigskip':'<div class="bigskip"> </div>', 
      'defskip':'<div class="defskip"> </div>', 
      'medskip':'<div class="medskip"> </div>', 
      'smallskip':'<div class="smallskip"> </div>', 
      'vfill':'<div class="vfill"> </div>', 
      }

class TOCConfig(object):
  "Configuration class from elyxer.config file"

  extractplain = {
      
      'allowed':['StringContainer','Constant','TaggedText','Align','TextFamily','EmphaticText','VersalitasText','BarredText','SizeText','ColorText','LangLine','Formula',], 
      'cloned':['',], 'extracted':['',], 
      }

  extracttitle = {
      'allowed':['StringContainer','Constant','Space',], 
      'cloned':['TextFamily','EmphaticText','VersalitasText','BarredText','SizeText','ColorText','LangLine','Formula',], 
      'extracted':['PlainLayout','TaggedText','Align','Caption','StandardLayout','FlexInset',], 
      }

class TagConfig(object):
  "Configuration class from elyxer.config file"

  barred = {
      'under':'u', 
      }

  family = {
      'sans':'span class="sans"', 'typewriter':'tt', 
      }

  flex = {
      'CharStyle:Code':'span class="code"', 
      'CharStyle:MenuItem':'span class="menuitem"', 
      'Code':'span class="code"', 'MenuItem':'span class="menuitem"', 
      'Noun':'span class="noun"', 'Strong':'span class="strong"', 
      }

  group = {
      'layouts':['Quotation','Quote',], 
      }

  layouts = {
      'Center':'div', 'Chapter':'h?', 'Date':'h2', 'Paragraph':'div', 
      'Part':'h1', 'Quotation':'blockquote', 'Quote':'blockquote', 
      'Section':'h?', 'Subsection':'h?', 'Subsubsection':'h?', 
      }

  listitems = {
      'Enumerate':'ol', 'Itemize':'ul', 
      }

  notes = {
      'Comment':'', 'Greyedout':'span class="greyedout"', 'Note':'', 
      }

  script = {
      'subscript':'sub', 'superscript':'sup', 
      }

  shaped = {
      'italic':'i', 'slanted':'i', 'smallcaps':'span class="versalitas"', 
      }

class TranslationConfig(object):
  "Configuration class from elyxer.config file"

  constants = {
      'Appendix':'Appendix', 'Book':'Book', 'Chapter':'Chapter', 
      'Paragraph':'Paragraph', 'Part':'Part', 'Section':'Section', 
      'Subsection':'Subsection', 'Subsubsection':'Subsubsection', 
      'abstract':'Abstract', 'bibliography':'Bibliography', 
      'figure':'figure', 'float-algorithm':'Algorithm ', 
      'float-figure':'Figure ', 'float-listing':'Listing ', 
      'float-table':'Table ', 'float-tableau':'Tableau ', 
      'footnotes':'Footnotes', 'generated-by':'Document generated by ', 
      'generated-on':' on ', 'index':'Index', 
      'jsmath-enable':'Please enable JavaScript on your browser.', 
      'jsmath-requires':' requires JavaScript to correctly process the mathematics on this page. ', 
      'jsmath-warning':'Warning: ', 'list-algorithm':'List of Algorithms', 
      'list-figure':'List of Figures', 'list-table':'List of Tables', 
      'list-tableau':'List of Tableaux', 'main-page':'Main page', 
      'next':'Next', 'nomenclature':'Nomenclature', 
      'on-page':' on page ', 'prev':'Prev', 'references':'References', 
      'toc':'Table of Contents', 'toc-for':'Contents for ', 'up':'Up', 
      }

  languages = {
      'american':'en', 'british':'en', 'deutsch':'de', 'dutch':'nl', 
      'english':'en', 'french':'fr', 'ngerman':'de', 'russian':'ru', 
      'spanish':'es', 
      }






class CommandLineParser(object):
  "A parser for runtime options"

  def __init__(self, options):
    self.options = options

  def parseoptions(self, args):
    "Parse command line options"
    if len(args) == 0:
      return None
    while len(args) > 0 and args[0].startswith('--'):
      key, value = self.readoption(args)
      if not key:
        return 'Option ' + value + ' not recognized'
      if not value:
        return 'Option ' + key + ' needs a value'
      setattr(self.options, key, value)
    return None

  def readoption(self, args):
    "Read the key and value for an option"
    arg = args[0][2:]
    del args[0]
    if '=' in arg:
      key = self.readequalskey(arg, args)
    else:
      key = arg.replace('-', '')
    if not hasattr(self.options, key):
      return None, key
    current = getattr(self.options, key)
    if isinstance(current, bool):
      return key, True
    # read value
    if len(args) == 0:
      return key, None
    if args[0].startswith('"'):
      initial = args[0]
      del args[0]
      return key, self.readquoted(args, initial)
    value = args[0].decode('utf-8')
    del args[0]
    if isinstance(current, list):
      current.append(value)
      return key, current
    return key, value

  def readquoted(self, args, initial):
    "Read a value between quotes"
    Trace.error('Oops')
    value = initial[1:]
    while len(args) > 0 and not args[0].endswith('"') and not args[0].startswith('--'):
      Trace.error('Appending ' + args[0])
      value += ' ' + args[0]
      del args[0]
    if len(args) == 0 or args[0].startswith('--'):
      return None
    value += ' ' + args[0:-1]
    return value

  def readequalskey(self, arg, args):
    "Read a key using equals"
    split = arg.split('=', 1)
    key = split[0]
    value = split[1]
    args.insert(0, value)
    return key



class Options(object):
  "A set of runtime options"

  instance = None

  location = None
  nocopy = False
  copyright = False
  debug = False
  quiet = False
  version = False
  hardversion = False
  versiondate = False
  html = False
  help = False
  showlines = True
  str = False
  iso885915 = False
  css = []
  favicon = ''
  title = None
  directory = None
  destdirectory = None
  toc = False
  toctarget = ''
  tocfor = None
  forceformat = None
  lyxformat = False
  target = None
  splitpart = None
  memory = True
  lowmem = False
  nobib = False
  converter = 'imagemagick'
  raw = False
  jsmath = None
  mathjax = None
  nofooter = False
  simplemath = False
  template = None
  noconvert = False
  notoclabels = False
  letterfoot = True
  numberfoot = False
  symbolfoot = False
  hoverfoot = True
  marginfoot = False
  endfoot = False
  supfoot = True
  alignfoot = False
  footnotes = None
  imageformat = None
  copyimages = False
  googlecharts = False
  embedcss = []

  branches = dict()

  def parseoptions(self, args):
    "Parse command line options"
    Options.location = args[0]
    del args[0]
    parser = CommandLineParser(Options)
    result = parser.parseoptions(args)
    if result:
      Trace.error(result)
      self.usage()
    self.processoptions()

  def processoptions(self):
    "Process all options parsed."
    if Options.help:
      self.usage()
    if Options.version:
      self.showversion()
    if Options.hardversion:
      self.showhardversion()
    if Options.versiondate:
      self.showversiondate()
    if Options.lyxformat:
      self.showlyxformat()
    if Options.splitpart:
      try:
        Options.splitpart = int(Options.splitpart)
        if Options.splitpart <= 0:
          Trace.error('--splitpart requires a number bigger than zero')
          self.usage()
      except:
        Trace.error('--splitpart needs a numeric argument, not ' + Options.splitpart)
        self.usage()
    if Options.lowmem or Options.toc or Options.tocfor:
      Options.memory = False
    self.parsefootnotes()
    if Options.forceformat and not Options.imageformat:
      Options.imageformat = Options.forceformat
    if Options.imageformat == 'copy':
      Options.copyimages = True
    if Options.css == []:
      Options.css = ['http://elyxer.nongnu.org/lyx.css']
    if Options.favicon == '':
      pass # no default favicon
    if Options.html:
      Options.simplemath = True
    if Options.toc and not Options.tocfor:
      Trace.error('Option --toc is deprecated; use --tocfor "page" instead')
      Options.tocfor = Options.toctarget
    if Options.nocopy:
      Trace.error('Option --nocopy is deprecated; it is no longer needed')
    if Options.jsmath:
      Trace.error('Option --jsmath is deprecated; use --mathjax instead')
    # set in Trace if necessary
    for param in dir(Trace):
      if param.endswith('mode'):
        setattr(Trace, param, getattr(self, param[:-4]))

  def usage(self):
    "Show correct usage"
    Trace.error('Usage: ' + os.path.basename(Options.location) + ' [options] [filein] [fileout]')
    Trace.error('Convert LyX input file "filein" to HTML file "fileout".')
    Trace.error('If filein (or fileout) is not given use standard input (or output).')
    Trace.error('Main program of the eLyXer package (http://elyxer.nongnu.org/).')
    self.showoptions()

  def parsefootnotes(self):
    "Parse footnotes options."
    if not Options.footnotes:
      return
    Options.marginfoot = False
    Options.letterfoot = False
    Options.hoverfoot = False
    options = Options.footnotes.split(',')
    for option in options:
      footoption = option + 'foot'
      if hasattr(Options, footoption):
        setattr(Options, footoption, True)
      else:
        Trace.error('Unknown footnotes option: ' + option)
    if not Options.endfoot and not Options.marginfoot and not Options.hoverfoot:
      Options.hoverfoot = True
    if not Options.numberfoot and not Options.symbolfoot:
      Options.letterfoot = True

  def showoptions(self):
    "Show all possible options"
    Trace.error('  Common options:')
    Trace.error('    --help:                 show this online help')
    Trace.error('    --quiet:                disables all runtime messages')
    Trace.error('')
    Trace.error('  Advanced options:')
    Trace.error('    --debug:                enable debugging messages (for developers)')
    Trace.error('    --version:              show version number and release date')
    Trace.error('    --lyxformat:            return the highest LyX version supported')
    Trace.error('  Options for HTML output:')
    Trace.error('    --title "title":        set the generated page title')
    Trace.error('    --css "file.css":       use a custom CSS file')
    Trace.error('    --embedcss "file.css":  embed styles from a CSS file into the output')
    Trace.error('    --favicon "icon.ico":   insert the specified favicon in the header.')
    Trace.error('    --html:                 output HTML 4.0 instead of the default XHTML')
    Trace.error('    --unicode:              full Unicode output')
    Trace.error('    --iso885915:            output a document with ISO-8859-15 encoding')
    Trace.error('    --nofooter:             remove the footer "generated by eLyXer"')
    Trace.error('    --simplemath:           do not generate fancy math constructions')
    Trace.error('  Options for image output:')
    Trace.error('    --directory "img_dir":  look for images in the specified directory')
    Trace.error('    --destdirectory "dest": put converted images into this directory')
    Trace.error('    --imageformat ".ext":   image output format, or "copy" to copy images')
    Trace.error('    --noconvert:            do not convert images, use in original locations')
    Trace.error('    --converter "inkscape": use an alternative program to convert images')
    Trace.error('  Options for footnote display:')
    Trace.error('    --numberfoot:           mark footnotes with numbers instead of letters')
    Trace.error('    --symbolfoot:           mark footnotes with symbols (*, **...)')
    Trace.error('    --hoverfoot:            show footnotes as hovering text (default)')
    Trace.error('    --marginfoot:           show footnotes on the page margin')
    Trace.error('    --endfoot:              show footnotes at the end of the page')
    Trace.error('    --supfoot:              use superscript for footnote markers (default)')
    Trace.error('    --alignfoot:            use aligned text for footnote markers')
    Trace.error('    --footnotes "options":  specify several comma-separated footnotes options')
    Trace.error('      Available options are: "number", "symbol", "hover", "margin", "end",')
    Trace.error('        "sup", "align"')
    Trace.error('  Advanced output options:')
    Trace.error('    --splitpart "depth":    split the resulting webpage at the given depth')
    Trace.error('    --tocfor "page":        generate a TOC that points to the given page')
    Trace.error('    --target "frame":       make all links point to the given frame')
    Trace.error('    --notoclabels:          omit the part labels in the TOC, such as Chapter')
    Trace.error('    --lowmem:               do the conversion on the fly (conserve memory)')
    Trace.error('    --raw:                  generate HTML without header or footer.')
    Trace.error('    --mathjax remote:       use MathJax remotely to display equations')
    Trace.error('    --mathjax "URL":        use MathJax from the given URL to display equations')
    Trace.error('    --googlecharts:         use Google Charts to generate formula images')
    Trace.error('    --template "file":      use a template, put everything in <!--$content-->')
    Trace.error('    --copyright:            add a copyright notice at the bottom')
    Trace.error('  Deprecated options:')
    Trace.error('    --toc:                  (deprecated) create a table of contents')
    Trace.error('    --toctarget "page":     (deprecated) generate a TOC for the given page')
    Trace.error('    --nocopy:               (deprecated) maintained for backwards compatibility')
    Trace.error('    --jsmath "URL":         use jsMath from the given URL to display equations')
    sys.exit()

  def showversion(self):
    "Return the current eLyXer version string"
    string = 'eLyXer version ' + GeneralConfig.version['number']
    string += ' (' + GeneralConfig.version['date'] + ')'
    Trace.error(string)
    sys.exit()

  def showhardversion(self):
    "Return just the version string"
    Trace.message(GeneralConfig.version['number'])
    sys.exit()

  def showversiondate(self):
    "Return just the version dte"
    Trace.message(GeneralConfig.version['date'])
    sys.exit()

  def showlyxformat(self):
    "Return just the lyxformat parameter"
    Trace.message(GeneralConfig.version['lyxformat'])
    sys.exit()

class BranchOptions(object):
  "A set of options for a branch"

  def __init__(self, name):
    self.name = name
    self.options = {'color':'#ffffff'}

  def set(self, key, value):
    "Set a branch option"
    if not key.startswith(ContainerConfig.string['startcommand']):
      Trace.error('Invalid branch option ' + key)
      return
    key = key.replace(ContainerConfig.string['startcommand'], '')
    self.options[key] = value

  def isselected(self):
    "Return if the branch is selected"
    if not 'selected' in self.options:
      return False
    return self.options['selected'] == '1'

  def __unicode__(self):
    "String representation"
    return 'options for ' + self.name + ': ' + str(self.options)




import urllib.request, urllib.parse, urllib.error








class Cloner(object):
  "An object used to clone other objects."

  def clone(cls, original):
    "Return an exact copy of an object."
    "The original object must have an empty constructor."
    return cls.create(original.__class__)

  def create(cls, type):
    "Create an object of a given class."
    clone = type.__new__(type)
    clone.__init__()
    return clone

  clone = classmethod(clone)
  create = classmethod(create)

class ContainerExtractor(object):
  "A class to extract certain containers."

  def __init__(self, config):
    "The config parameter is a map containing three lists: allowed, copied and extracted."
    "Each of the three is a list of class names for containers."
    "Allowed containers are included as is into the result."
    "Cloned containers are cloned and placed into the result."
    "Extracted containers are looked into."
    "All other containers are silently ignored."
    self.allowed = config['allowed']
    self.cloned = config['cloned']
    self.extracted = config['extracted']

  def extract(self, container):
    "Extract a group of selected containers from elyxer.a container."
    list = []
    locate = lambda c: c.__class__.__name__ in self.allowed + self.cloned
    recursive = lambda c: c.__class__.__name__ in self.extracted
    process = lambda c: self.process(c, list)
    container.recursivesearch(locate, recursive, process)
    return list

  def process(self, container, list):
    "Add allowed containers, clone cloned containers and add the clone."
    name = container.__class__.__name__
    if name in self.allowed:
      list.append(container)
    elif name in self.cloned:
      list.append(self.safeclone(container))
    else:
      Trace.error('Unknown container class ' + name)

  def safeclone(self, container):
    "Return a new container with contents only in a safe list, recursively."
    clone = Cloner.clone(container)
    clone.output = container.output
    clone.contents = self.extract(container)
    return clone






class Parser(object):
  "A generic parser"

  def __init__(self):
    self.begin = 0
    self.parameters = dict()

  def parseheader(self, reader):
    "Parse the header"
    header = reader.currentline().split()
    reader.nextline()
    self.begin = reader.linenumber
    return header

  def parseparameter(self, reader):
    "Parse a parameter"
    if reader.currentline().strip().startswith('<'):
      key, value = self.parsexml(reader)
      self.parameters[key] = value
      return
    split = reader.currentline().strip().split(' ', 1)
    reader.nextline()
    if len(split) == 0:
      return
    key = split[0]
    if len(split) == 1:
      self.parameters[key] = True
      return
    if not '"' in split[1]:
      self.parameters[key] = split[1].strip()
      return
    doublesplit = split[1].split('"')
    self.parameters[key] = doublesplit[1]

  def parsexml(self, reader):
    "Parse a parameter in xml form: <param attr1=value...>"
    strip = reader.currentline().strip()
    reader.nextline()
    if not strip.endswith('>'):
      Trace.error('XML parameter ' + strip + ' should be <...>')
    split = strip[1:-1].split()
    if len(split) == 0:
      Trace.error('Empty XML parameter <>')
      return None, None
    key = split[0]
    del split[0]
    if len(split) == 0:
      return key, dict()
    attrs = dict()
    for attr in split:
      if not '=' in attr:
        Trace.error('Erroneous attribute for ' + key + ': ' + attr)
        attr += '="0"'
      parts = attr.split('=')
      attrkey = parts[0]
      value = parts[1].split('"')[1]
      attrs[attrkey] = value
    return key, attrs

  def parseending(self, reader, process):
    "Parse until the current ending is found"
    if not self.ending:
      Trace.error('No ending for ' + str(self))
      return
    while not reader.currentline().startswith(self.ending):
      process()

  def parsecontainer(self, reader, contents):
    container = self.factory.createcontainer(reader)
    if container:
      container.parent = self.parent
      contents.append(container)

  def __unicode__(self):
    "Return a description"
    return self.__class__.__name__ + ' (' + str(self.begin) + ')'

class LoneCommand(Parser):
  "A parser for just one command line"

  def parse(self,reader):
    "Read nothing"
    return []

class TextParser(Parser):
  "A parser for a command and a bit of text"

  stack = []

  def __init__(self, container):
    Parser.__init__(self)
    self.ending = None
    if container.__class__.__name__ in ContainerConfig.endings:
      self.ending = ContainerConfig.endings[container.__class__.__name__]
    self.endings = []

  def parse(self, reader):
    "Parse lines as long as they are text"
    TextParser.stack.append(self.ending)
    self.endings = TextParser.stack + [ContainerConfig.endings['Layout'],
        ContainerConfig.endings['Inset'], self.ending]
    contents = []
    while not self.isending(reader):
      self.parsecontainer(reader, contents)
    return contents

  def isending(self, reader):
    "Check if text is ending"
    current = reader.currentline().split()
    if len(current) == 0:
      return False
    if current[0] in self.endings:
      if current[0] in TextParser.stack:
        TextParser.stack.remove(current[0])
      else:
        TextParser.stack = []
      return True
    return False

class ExcludingParser(Parser):
  "A parser that excludes the final line"

  def parse(self, reader):
    "Parse everything up to (and excluding) the final line"
    contents = []
    self.parseending(reader, lambda: self.parsecontainer(reader, contents))
    return contents

class BoundedParser(ExcludingParser):
  "A parser bound by a final line"

  def parse(self, reader):
    "Parse everything, including the final line"
    contents = ExcludingParser.parse(self, reader)
    # skip last line
    reader.nextline()
    return contents

class BoundedDummy(Parser):
  "A bound parser that ignores everything"

  def parse(self, reader):
    "Parse the contents of the container"
    self.parseending(reader, lambda: reader.nextline())
    # skip last line
    reader.nextline()
    return []

class StringParser(Parser):
  "Parses just a string"

  def parseheader(self, reader):
    "Do nothing, just take note"
    self.begin = reader.linenumber + 1
    return []

  def parse(self, reader):
    "Parse a single line"
    contents = reader.currentline()
    reader.nextline()
    return contents

class InsetParser(BoundedParser):
  "Parses a LyX inset"

  def parse(self, reader):
    "Parse inset parameters into a dictionary"
    startcommand = ContainerConfig.string['startcommand']
    while reader.currentline() != '' and not reader.currentline().startswith(startcommand):
      self.parseparameter(reader)
    return BoundedParser.parse(self, reader)






class ContainerOutput(object):
  "The generic HTML output for a container."

  def gethtml(self, container):
    "Show an error."
    Trace.error('gethtml() not implemented for ' + str(self))

  def isempty(self):
    "Decide if the output is empty: by default, not empty."
    return False

class EmptyOutput(ContainerOutput):

  def gethtml(self, container):
    "Return empty HTML code."
    return []

  def isempty(self):
    "This output is particularly empty."
    return True

class FixedOutput(ContainerOutput):
  "Fixed output"

  def gethtml(self, container):
    "Return constant HTML code"
    return container.html

class ContentsOutput(ContainerOutput):
  "Outputs the contents converted to HTML"

  def gethtml(self, container):
    "Return the HTML code"
    html = []
    if container.contents == None:
      return html
    for element in container.contents:
      if not hasattr(element, 'gethtml'):
        Trace.error('No html in ' + element.__class__.__name__ + ': ' + str(element))
        return html
      html += element.gethtml()
    return html

class TaggedOutput(ContentsOutput):
  "Outputs an HTML tag surrounding the contents."

  tag = None
  breaklines = False
  empty = False

  def settag(self, tag, breaklines=False, empty=False):
    "Set the value for the tag and other attributes."
    self.tag = tag
    if breaklines:
      self.breaklines = breaklines
    if empty:
      self.empty = empty
    return self

  def setbreaklines(self, breaklines):
    "Set the value for breaklines."
    self.breaklines = breaklines
    return self

  def gethtml(self, container):
    "Return the HTML code."
    if self.empty:
      return [self.selfclosing(container)]
    html = [self.open(container)]
    html += ContentsOutput.gethtml(self, container)
    html.append(self.close(container))
    return html

  def open(self, container):
    "Get opening line."
    if not self.checktag():
      return ''
    open = '<' + self.tag + '>'
    if self.breaklines:
      return open + '\n'
    return open

  def close(self, container):
    "Get closing line."
    if not self.checktag():
      return ''
    close = '</' + self.tag.split()[0] + '>'
    if self.breaklines:
      return '\n' + close + '\n'
    return close

  def selfclosing(self, container):
    "Get self-closing line."
    if not self.checktag():
      return ''
    selfclosing = '<' + self.tag + '/>'
    if self.breaklines:
      return selfclosing + '\n'
    return selfclosing

  def checktag(self):
    "Check that the tag is valid."
    if not self.tag:
      Trace.error('No tag in ' + str(container))
      return False
    if self.tag == '':
      return False
    return True

class FilteredOutput(ContentsOutput):
  "Returns the output in the contents, but filtered:"
  "some strings are replaced by others."

  def __init__(self):
    "Initialize the filters."
    self.filters = []

  def addfilter(self, original, replacement):
    "Add a new filter: replace the original by the replacement."
    self.filters.append((original, replacement))

  def gethtml(self, container):
    "Return the HTML code"
    result = []
    html = ContentsOutput.gethtml(self, container)
    for line in html:
      result.append(self.filter(line))
    return result

  def filter(self, line):
    "Filter a single line with all available filters."
    for original, replacement in self.filters:
      if original in line:
        line = line.replace(original, replacement)
    return line

class StringOutput(ContainerOutput):
  "Returns a bare string as output"

  def gethtml(self, container):
    "Return a bare string"
    return [container.string]







import sys
import codecs


class LineReader(object):
  "Reads a file line by line"

  def __init__(self, filename):
    if isinstance(filename, file):
      self.file = filename
    else:
      self.file = codecs.open(filename, 'rU', 'utf-8')
    self.linenumber = 1
    self.lastline = None
    self.current = None
    self.mustread = True
    self.depleted = False
    try:
      self.readline()
    except UnicodeDecodeError:
      # try compressed file
      import gzip
      self.file = gzip.open(filename, 'rb')
      self.readline()

  def setstart(self, firstline):
    "Set the first line to read."
    for i in range(firstline):
      self.file.readline()
    self.linenumber = firstline

  def setend(self, lastline):
    "Set the last line to read."
    self.lastline = lastline

  def currentline(self):
    "Get the current line"
    if self.mustread:
      self.readline()
    return self.current

  def nextline(self):
    "Go to next line"
    if self.depleted:
      Trace.fatal('Read beyond file end')
    self.mustread = True

  def readline(self):
    "Read a line from elyxer.file"
    self.current = self.file.readline()
    if not isinstance(self.file, codecs.StreamReaderWriter):
      self.current = self.current.decode('utf-8')
    if len(self.current) == 0:
      self.depleted = True
    self.current = self.current.rstrip('\n\r')
    self.linenumber += 1
    self.mustread = False
    Trace.prefix = 'Line ' + str(self.linenumber) + ': '
    if self.linenumber % 1000 == 0:
      Trace.message('Parsing')

  def finished(self):
    "Find out if the file is finished"
    if self.lastline and self.linenumber == self.lastline:
      return True
    if self.mustread:
      self.readline()
    return self.depleted

  def close(self):
    self.file.close()

class LineWriter(object):
  "Writes a file as a series of lists"

  file = False

  def __init__(self, filename):
    if isinstance(filename, file):
      self.file = filename
      self.filename = None
    else:
      self.filename = filename

  def write(self, strings):
    "Write a list of strings"
    for string in strings:
      if not isinstance(string, str):
        Trace.error('Not a string: ' + str(string) + ' in ' + str(strings))
        return
      self.writestring(string)

  def writestring(self, string):
    "Write a string"
    if not self.file:
      self.file = codecs.open(self.filename, 'w', "utf-8")
    if self.file == sys.stdout and sys.version_info < (3,0):
      string = string.encode('utf-8')
    self.file.write(string)

  def writeline(self, line):
    "Write a line to file"
    self.writestring(line + '\n')

  def close(self):
    self.file.close()






class Globable(object):
  """A bit of text which can be globbed (lumped together in bits).
  Methods current(), skipcurrent(), checkfor() and isout() have to be
  implemented by subclasses."""

  leavepending = False

  def __init__(self):
    self.endinglist = EndingList()

  def checkbytemark(self):
    "Check for a Unicode byte mark and skip it."
    if self.finished():
      return
    if ord(self.current()) == 0xfeff:
      self.skipcurrent()

  def isout(self):
    "Find out if we are out of the position yet."
    Trace.error('Unimplemented isout()')
    return True

  def current(self):
    "Return the current character."
    Trace.error('Unimplemented current()')
    return ''

  def checkfor(self, string):
    "Check for the given string in the current position."
    Trace.error('Unimplemented checkfor()')
    return False

  def finished(self):
    "Find out if the current text has finished."
    if self.isout():
      if not self.leavepending:
        self.endinglist.checkpending()
      return True
    return self.endinglist.checkin(self)

  def skipcurrent(self):
    "Return the current character and skip it."
    Trace.error('Unimplemented skipcurrent()')
    return ''

  def glob(self, currentcheck):
    "Glob a bit of text that satisfies a check on the current char."
    glob = ''
    while not self.finished() and currentcheck():
      glob += self.skipcurrent()
    return glob

  def globalpha(self):
    "Glob a bit of alpha text"
    return self.glob(lambda: self.current().isalpha())

  def globnumber(self):
    "Glob a row of digits."
    return self.glob(lambda: self.current().isdigit())

  def isidentifier(self):
    "Return if the current character is alphanumeric or _."
    if self.current().isalnum() or self.current() == '_':
      return True
    return False

  def globidentifier(self):
    "Glob alphanumeric and _ symbols."
    return self.glob(self.isidentifier)

  def isvalue(self):
    "Return if the current character is a value character:"
    "not a bracket or a space."
    if self.current().isspace():
      return False
    if self.current() in '{}()':
      return False
    return True

  def globvalue(self):
    "Glob a value: any symbols but brackets."
    return self.glob(self.isvalue)

  def skipspace(self):
    "Skip all whitespace at current position."
    return self.glob(lambda: self.current().isspace())

  def globincluding(self, magicchar):
    "Glob a bit of text up to (including) the magic char."
    glob = self.glob(lambda: self.current() != magicchar) + magicchar
    self.skip(magicchar)
    return glob

  def globexcluding(self, excluded):
    "Glob a bit of text up until (excluding) any excluded character."
    return self.glob(lambda: self.current() not in excluded)

  def pushending(self, ending, optional = False):
    "Push a new ending to the bottom"
    self.endinglist.add(ending, optional)

  def popending(self, expected = None):
    "Pop the ending found at the current position"
    if self.isout() and self.leavepending:
      return expected
    ending = self.endinglist.pop(self)
    if expected and expected != ending:
      Trace.error('Expected ending ' + expected + ', got ' + ending)
    self.skip(ending)
    return ending

  def nextending(self):
    "Return the next ending in the queue."
    nextending = self.endinglist.findending(self)
    if not nextending:
      return None
    return nextending.ending

class EndingList(object):
  "A list of position endings"

  def __init__(self):
    self.endings = []

  def add(self, ending, optional = False):
    "Add a new ending to the list"
    self.endings.append(PositionEnding(ending, optional))

  def pickpending(self, pos):
    "Pick any pending endings from a parse position."
    self.endings += pos.endinglist.endings

  def checkin(self, pos):
    "Search for an ending"
    if self.findending(pos):
      return True
    return False

  def pop(self, pos):
    "Remove the ending at the current position"
    if pos.isout():
      Trace.error('No ending out of bounds')
      return ''
    ending = self.findending(pos)
    if not ending:
      Trace.error('No ending at ' + pos.current())
      return ''
    for each in reversed(self.endings):
      self.endings.remove(each)
      if each == ending:
        return each.ending
      elif not each.optional:
        Trace.error('Removed non-optional ending ' + each)
    Trace.error('No endings left')
    return ''

  def findending(self, pos):
    "Find the ending at the current position"
    if len(self.endings) == 0:
      return None
    for index, ending in enumerate(reversed(self.endings)):
      if ending.checkin(pos):
        return ending
      if not ending.optional:
        return None
    return None

  def checkpending(self):
    "Check if there are any pending endings"
    if len(self.endings) != 0:
      Trace.error('Pending ' + str(self) + ' left open')

  def __unicode__(self):
    "Printable representation"
    string = 'endings ['
    for ending in self.endings:
      string += str(ending) + ','
    if len(self.endings) > 0:
      string = string[:-1]
    return string + ']'

class PositionEnding(object):
  "An ending for a parsing position"

  def __init__(self, ending, optional):
    self.ending = ending
    self.optional = optional

  def checkin(self, pos):
    "Check for the ending"
    return pos.checkfor(self.ending)

  def __unicode__(self):
    "Printable representation"
    string = 'Ending ' + self.ending
    if self.optional:
      string += ' (optional)'
    return string



class Position(Globable):
  """A position in a text to parse.
  Including those in Globable, functions to implement by subclasses are:
  skip(), identifier(), extract(), isout() and current()."""

  def __init__(self):
    Globable.__init__(self)

  def skip(self, string):
    "Skip a string"
    Trace.error('Unimplemented skip()')

  def identifier(self):
    "Return an identifier for the current position."
    Trace.error('Unimplemented identifier()')
    return 'Error'

  def extract(self, length):
    "Extract the next string of the given length, or None if not enough text,"
    "without advancing the parse position."
    Trace.error('Unimplemented extract()')
    return None

  def checkfor(self, string):
    "Check for a string at the given position."
    return string == self.extract(len(string))

  def checkforlower(self, string):
    "Check for a string in lower case."
    extracted = self.extract(len(string))
    if not extracted:
      return False
    return string.lower() == self.extract(len(string)).lower()

  def skipcurrent(self):
    "Return the current character and skip it."
    current = self.current()
    self.skip(current)
    return current

  def __next__(self):
    "Advance the position and return the next character."
    self.skipcurrent()
    return self.current()

  def checkskip(self, string):
    "Check for a string at the given position; if there, skip it"
    if not self.checkfor(string):
      return False
    self.skip(string)
    return True

  def error(self, message):
    "Show an error message and the position identifier."
    Trace.error(message + ': ' + self.identifier())

class TextPosition(Position):
  "A parse position based on a raw text."

  def __init__(self, text):
    "Create the position from elyxer.some text."
    Position.__init__(self)
    self.pos = 0
    self.text = text
    self.checkbytemark()

  def skip(self, string):
    "Skip a string of characters."
    self.pos += len(string)

  def identifier(self):
    "Return a sample of the remaining text."
    length = 30
    if self.pos + length > len(self.text):
      length = len(self.text) - self.pos
    return '*' + self.text[self.pos:self.pos + length] + '*'

  def isout(self):
    "Find out if we are out of the text yet."
    return self.pos >= len(self.text)

  def current(self):
    "Return the current character, assuming we are not out."
    return self.text[self.pos]

  def extract(self, length):
    "Extract the next string of the given length, or None if not enough text."
    if self.pos + length > len(self.text):
      return None
    return self.text[self.pos : self.pos + length]

class FilePosition(Position):
  "A parse position based on an underlying file."

  def __init__(self, filename):
    "Create the position from a file."
    Position.__init__(self)
    self.reader = LineReader(filename)
    self.pos = 0
    self.checkbytemark()

  def skip(self, string):
    "Skip a string of characters."
    length = len(string)
    while self.pos + length > len(self.reader.currentline()):
      length -= len(self.reader.currentline()) - self.pos + 1
      self.nextline()
    self.pos += length

  def currentline(self):
    "Get the current line of the underlying file."
    return self.reader.currentline()

  def nextline(self):
    "Go to the next line."
    self.reader.nextline()
    self.pos = 0

  def linenumber(self):
    "Return the line number of the file."
    return self.reader.linenumber + 1

  def identifier(self):
    "Return the current line and line number in the file."
    before = self.reader.currentline()[:self.pos - 1]
    after = self.reader.currentline()[self.pos:]
    return 'line ' + str(self.getlinenumber()) + ': ' + before + '*' + after

  def isout(self):
    "Find out if we are out of the text yet."
    if self.pos > len(self.reader.currentline()):
      if self.pos > len(self.reader.currentline()) + 1:
        Trace.error('Out of the line ' + self.reader.currentline() + ': ' + str(self.pos))
      self.nextline()
    return self.reader.finished()

  def current(self):
    "Return the current character, assuming we are not out."
    if self.pos == len(self.reader.currentline()):
      return '\n'
    if self.pos > len(self.reader.currentline()):
      Trace.error('Out of the line ' + self.reader.currentline() + ': ' + str(self.pos))
      return '*'
    return self.reader.currentline()[self.pos]

  def extract(self, length):
    "Extract the next string of the given length, or None if not enough text."
    if self.pos + length > len(self.reader.currentline()):
      return None
    return self.reader.currentline()[self.pos : self.pos + length]



class Container(object):
  "A container for text and objects in a lyx file"

  partkey = None
  parent = None
  begin = None

  def __init__(self):
    self.contents = list()

  def process(self):
    "Process contents"
    pass

  def gethtml(self):
    "Get the resulting HTML"
    html = self.output.gethtml(self)
    if isinstance(html, str):
      Trace.error('Raw string ' + html)
      html = [html]
    return self.escapeall(html)

  def escapeall(self, lines):
    "Escape all lines in an array according to the output options."
    result = []
    for line in lines:
      if Options.html:
        line = self.escape(line, EscapeConfig.html)
      if Options.iso885915:
        line = self.escape(line, EscapeConfig.iso885915)
        line = self.escapeentities(line)
      elif not Options.str:
        line = self.escape(line, EscapeConfig.nonunicode)
      result.append(line)
    return result

  def escape(self, line, replacements = EscapeConfig.entities):
    "Escape a line with replacements from elyxer.a map"
    pieces = list(replacements.keys())
    # do them in order
    pieces.sort()
    for piece in pieces:
      if piece in line:
        line = line.replace(piece, replacements[piece])
    return line

  def escapeentities(self, line):
    "Escape all Unicode characters to HTML entities."
    result = ''
    pos = TextPosition(line)
    while not pos.finished():
      if ord(pos.current()) > 128:
        codepoint = hex(ord(pos.current()))
        if codepoint == '0xd835':
          codepoint = hex(ord(next(pos)) + 0xf800)
        result += '&#' + codepoint[1:] + ';'
      else:
        result += pos.current()
      pos.skipcurrent()
    return result

  def searchall(self, type):
    "Search for all embedded containers of a given type"
    list = []
    self.searchprocess(type, lambda container: list.append(container))
    return list

  def searchremove(self, type):
    "Search for all containers of a type and remove them"
    list = self.searchall(type)
    for container in list:
      container.parent.contents.remove(container)
    return list

  def searchprocess(self, type, process):
    "Search for elements of a given type and process them"
    self.locateprocess(lambda container: isinstance(container, type), process)

  def locateprocess(self, locate, process):
    "Search for all embedded containers and process them"
    for container in self.contents:
      container.locateprocess(locate, process)
      if locate(container):
        process(container)

  def recursivesearch(self, locate, recursive, process):
    "Perform a recursive search in the container."
    for container in self.contents:
      if recursive(container):
        container.recursivesearch(locate, recursive, process)
      if locate(container):
        process(container)

  def extracttext(self):
    "Extract all text from elyxer.allowed containers."
    result = ''
    constants = ContainerExtractor(ContainerConfig.extracttext).extract(self)
    for constant in constants:
      result += constant.string
    return result

  def group(self, index, group, isingroup):
    "Group some adjoining elements into a group"
    if index >= len(self.contents):
      return
    if hasattr(self.contents[index], 'grouped'):
      return
    while index < len(self.contents) and isingroup(self.contents[index]):
      self.contents[index].grouped = True
      group.contents.append(self.contents[index])
      self.contents.pop(index)
    self.contents.insert(index, group)

  def remove(self, index):
    "Remove a container but leave its contents"
    container = self.contents[index]
    self.contents.pop(index)
    while len(container.contents) > 0:
      self.contents.insert(index, container.contents.pop())

  def tree(self, level = 0):
    "Show in a tree"
    Trace.debug("  " * level + str(self))
    for container in self.contents:
      container.tree(level + 1)

  def getparameter(self, name):
    "Get the value of a parameter, if present."
    if not name in self.parameters:
      return None
    return self.parameters[name]

  def getparameterlist(self, name):
    "Get the value of a comma-separated parameter as a list."
    paramtext = self.getparameter(name)
    if not paramtext:
      return []
    return paramtext.split(',')

  def hasemptyoutput(self):
    "Check if the parent's output is empty."
    current = self.parent
    while current:
      if current.output.isempty():
        return True
      current = current.parent
    return False

  def __unicode__(self):
    "Get a description"
    if not self.begin:
      return self.__class__.__name__
    return self.__class__.__name__ + '@' + str(self.begin)

class BlackBox(Container):
  "A container that does not output anything"

  def __init__(self):
    self.parser = LoneCommand()
    self.output = EmptyOutput()
    self.contents = []

class LyXFormat(BlackBox):
  "Read the lyxformat command"

  def process(self):
    "Show warning if version < 276"
    version = int(self.header[1])
    if version < 276:
      Trace.error('Warning: unsupported old format version ' + str(version))
    if version > int(GeneralConfig.version['lyxformat']):
      Trace.error('Warning: unsupported new format version ' + str(version))

class StringContainer(Container):
  "A container for a single string"

  parsed = None

  def __init__(self):
    self.parser = StringParser()
    self.output = StringOutput()
    self.string = ''

  def process(self):
    "Replace special chars from elyxer.the contents."
    if self.parsed:
      self.string = self.replacespecial(self.parsed)
      self.parsed = None

  def replacespecial(self, line):
    "Replace all special chars from elyxer.a line"
    replaced = self.escape(line, EscapeConfig.entities)
    replaced = self.changeline(replaced)
    if ContainerConfig.string['startcommand'] in replaced and len(replaced) > 1:
      # unprocessed commands
      if self.begin:
        message = 'Unknown command at ' + str(self.begin) + ': '
      else:
        message = 'Unknown command: '
      Trace.error(message + replaced.strip())
    return replaced

  def changeline(self, line):
    line = self.escape(line, EscapeConfig.chars)
    if not ContainerConfig.string['startcommand'] in line:
      return line
    line = self.escape(line, EscapeConfig.commands)
    return line

  def extracttext(self):
    "Return all text."
    return self.string
  
  def __unicode__(self):
    "Return a printable representation."
    result = 'StringContainer'
    if self.begin:
      result += '@' + str(self.begin)
    ellipsis = '...'
    if len(self.string.strip()) <= 15:
      ellipsis = ''
    return result + ' (' + self.string.strip()[:15] + ellipsis + ')'

class Constant(StringContainer):
  "A constant string"

  def __init__(self, text):
    self.contents = []
    self.string = text
    self.output = StringOutput()

  def __unicode__(self):
    return 'Constant: ' + self.string

class TaggedText(Container):
  "Text inside a tag"

  output = None

  def __init__(self):
    self.parser = TextParser(self)
    self.output = TaggedOutput()

  def complete(self, contents, tag, breaklines=False):
    "Complete the tagged text and return it"
    self.contents = contents
    self.output.tag = tag
    self.output.breaklines = breaklines
    return self

  def constant(self, text, tag, breaklines=False):
    "Complete the tagged text with a constant"
    constant = Constant(text)
    return self.complete([constant], tag, breaklines)

  def __unicode__(self):
    "Return a printable representation."
    if not hasattr(self.output, 'tag'):
      return 'Emtpy tagged text'
    if not self.output.tag:
      return 'Tagged <unknown tag>'
    return 'Tagged <' + self.output.tag + '>'






class DocumentParameters(object):
  "Global parameters for the document."

  pdftitle = None
  indentstandard = False
  tocdepth = 10
  startinglevel = 0
  maxdepth = 10
  language = None
  bibliography = None
  outputchanges = False
  displaymode = False






class FormulaParser(Parser):
  "Parses a formula"

  def parseheader(self, reader):
    "See if the formula is inlined"
    self.begin = reader.linenumber + 1
    type = self.parsetype(reader)
    if not type:
      reader.nextline()
      type = self.parsetype(reader)
      if not type:
        Trace.error('Unknown formula type in ' + reader.currentline().strip())
        return ['unknown']
    return [type]

  def parsetype(self, reader):
    "Get the formula type from the first line."
    if reader.currentline().find(FormulaConfig.starts['simple']) >= 0:
      return 'inline'
    if reader.currentline().find(FormulaConfig.starts['complex']) >= 0:
      return 'block'
    if reader.currentline().find(FormulaConfig.starts['unnumbered']) >= 0:
      return 'block'
    if reader.currentline().find(FormulaConfig.starts['beginbefore']) >= 0:
      return 'numbered'
    return None
  
  def parse(self, reader):
    "Parse the formula until the end"
    formula = self.parseformula(reader)
    while not reader.currentline().startswith(self.ending):
      stripped = reader.currentline().strip()
      if len(stripped) > 0:
        Trace.error('Unparsed formula line ' + stripped)
      reader.nextline()
    reader.nextline()
    return formula

  def parseformula(self, reader):
    "Parse the formula contents"
    simple = FormulaConfig.starts['simple']
    if simple in reader.currentline():
      rest = reader.currentline().split(simple, 1)[1]
      if simple in rest:
        # formula is $...$
        return self.parsesingleliner(reader, simple, simple)
      # formula is multiline $...$
      return self.parsemultiliner(reader, simple, simple)
    if FormulaConfig.starts['complex'] in reader.currentline():
      # formula of the form \[...\]
      return self.parsemultiliner(reader, FormulaConfig.starts['complex'],
          FormulaConfig.endings['complex'])
    beginbefore = FormulaConfig.starts['beginbefore']
    beginafter = FormulaConfig.starts['beginafter']
    if beginbefore in reader.currentline():
      if reader.currentline().strip().endswith(beginafter):
        current = reader.currentline().strip()
        endsplit = current.split(beginbefore)[1].split(beginafter)
        startpiece = beginbefore + endsplit[0] + beginafter
        endbefore = FormulaConfig.endings['endbefore']
        endafter = FormulaConfig.endings['endafter']
        endpiece = endbefore + endsplit[0] + endafter
        return startpiece + self.parsemultiliner(reader, startpiece, endpiece) + endpiece
      Trace.error('Missing ' + beginafter + ' in ' + reader.currentline())
      return ''
    begincommand = FormulaConfig.starts['command']
    beginbracket = FormulaConfig.starts['bracket']
    if begincommand in reader.currentline() and beginbracket in reader.currentline():
      endbracket = FormulaConfig.endings['bracket']
      return self.parsemultiliner(reader, beginbracket, endbracket)
    Trace.error('Formula beginning ' + reader.currentline() + ' is unknown')
    return ''

  def parsesingleliner(self, reader, start, ending):
    "Parse a formula in one line"
    line = reader.currentline().strip()
    if not start in line:
      Trace.error('Line ' + line + ' does not contain formula start ' + start)
      return ''
    if not line.endswith(ending):
      Trace.error('Formula ' + line + ' does not end with ' + ending)
      return ''
    index = line.index(start)
    rest = line[index + len(start):-len(ending)]
    reader.nextline()
    return rest

  def parsemultiliner(self, reader, start, ending):
    "Parse a formula in multiple lines"
    formula = ''
    line = reader.currentline()
    if not start in line:
      Trace.error('Line ' + line.strip() + ' does not contain formula start ' + start)
      return ''
    index = line.index(start)
    line = line[index + len(start):].strip()
    while not line.endswith(ending):
      formula += line + '\n'
      reader.nextline()
      line = reader.currentline()
    formula += line[:-len(ending)]
    reader.nextline()
    return formula

class MacroParser(FormulaParser):
  "A parser for a formula macro."

  def parseheader(self, reader):
    "See if the formula is inlined"
    self.begin = reader.linenumber + 1
    return ['inline']
  
  def parse(self, reader):
    "Parse the formula until the end"
    formula = self.parsemultiliner(reader, self.parent.start, self.ending)
    reader.nextline()
    return formula
  








class FormulaBit(Container):
  "A bit of a formula"

  type = None
  size = 1
  original = ''

  def __init__(self):
    "The formula bit type can be 'alpha', 'number', 'font'."
    self.contents = []
    self.output = ContentsOutput()

  def setfactory(self, factory):
    "Set the internal formula factory."
    self.factory = factory
    return self

  def add(self, bit):
    "Add any kind of formula bit already processed"
    self.contents.append(bit)
    self.original += bit.original
    bit.parent = self

  def skiporiginal(self, string, pos):
    "Skip a string and add it to the original formula"
    self.original += string
    if not pos.checkskip(string):
      Trace.error('String ' + string + ' not at ' + pos.identifier())

  def computesize(self):
    "Compute the size of the bit as the max of the sizes of all contents."
    if len(self.contents) == 0:
      return 1
    self.size = max([element.size for element in self.contents])
    return self.size

  def clone(self):
    "Return a copy of itself."
    return self.factory.parseformula(self.original)

  def __unicode__(self):
    "Get a string representation"
    return self.__class__.__name__ + ' read in ' + self.original

class TaggedBit(FormulaBit):
  "A tagged string in a formula"

  def constant(self, constant, tag):
    "Set the constant and the tag"
    self.output = TaggedOutput().settag(tag)
    self.add(FormulaConstant(constant))
    return self

  def complete(self, contents, tag, breaklines = False):
    "Set the constant and the tag"
    self.contents = contents
    self.output = TaggedOutput().settag(tag, breaklines)
    return self

  def selfcomplete(self, tag):
    "Set the self-closing tag, no contents (as in <hr/>)."
    self.output = TaggedOutput().settag(tag, empty = True)
    return self

class FormulaConstant(Constant):
  "A constant string in a formula"

  def __init__(self, string):
    "Set the constant string"
    Constant.__init__(self, string)
    self.original = string
    self.size = 1
    self.type = None

  def computesize(self):
    "Compute the size of the constant: always 1."
    return self.size

  def clone(self):
    "Return a copy of itself."
    return FormulaConstant(self.original)

  def __unicode__(self):
    "Return a printable representation."
    return 'Formula constant: ' + self.string

class RawText(FormulaBit):
  "A bit of text inside a formula"

  def detect(self, pos):
    "Detect a bit of raw text"
    return pos.current().isalpha()

  def parsebit(self, pos):
    "Parse alphabetic text"
    alpha = pos.globalpha()
    self.add(FormulaConstant(alpha))
    self.type = 'alpha'

class FormulaSymbol(FormulaBit):
  "A symbol inside a formula"

  modified = FormulaConfig.modified
  unmodified = FormulaConfig.unmodified['characters']

  def detect(self, pos):
    "Detect a symbol"
    if pos.current() in FormulaSymbol.unmodified:
      return True
    if pos.current() in FormulaSymbol.modified:
      return True
    return False

  def parsebit(self, pos):
    "Parse the symbol"
    if pos.current() in FormulaSymbol.unmodified:
      self.addsymbol(pos.current(), pos)
      return
    if pos.current() in FormulaSymbol.modified:
      self.addsymbol(FormulaSymbol.modified[pos.current()], pos)
      return
    Trace.error('Symbol ' + pos.current() + ' not found')

  def addsymbol(self, symbol, pos):
    "Add a symbol"
    self.skiporiginal(pos.current(), pos)
    self.contents.append(FormulaConstant(symbol))

class FormulaNumber(FormulaBit):
  "A string of digits in a formula"

  def detect(self, pos):
    "Detect a digit"
    return pos.current().isdigit()

  def parsebit(self, pos):
    "Parse a bunch of digits"
    digits = pos.glob(lambda: pos.current().isdigit())
    self.add(FormulaConstant(digits))
    self.type = 'number'

class Comment(FormulaBit):
  "A LaTeX comment: % to the end of the line."

  start = FormulaConfig.starts['comment']

  def detect(self, pos):
    "Detect the %."
    return pos.current() == self.start

  def parsebit(self, pos):
    "Parse to the end of the line."
    self.original += pos.globincluding('\n')

class WhiteSpace(FormulaBit):
  "Some white space inside a formula."

  def detect(self, pos):
    "Detect the white space."
    return pos.current().isspace()

  def parsebit(self, pos):
    "Parse all whitespace."
    self.original += pos.skipspace()

  def __unicode__(self):
    "Return a printable representation."
    return 'Whitespace: *' + self.original + '*'

class Bracket(FormulaBit):
  "A {} bracket inside a formula"

  start = FormulaConfig.starts['bracket']
  ending = FormulaConfig.endings['bracket']

  def __init__(self):
    "Create a (possibly literal) new bracket"
    FormulaBit.__init__(self)
    self.inner = None

  def detect(self, pos):
    "Detect the start of a bracket"
    return pos.checkfor(self.start)

  def parsebit(self, pos):
    "Parse the bracket"
    self.parsecomplete(pos, self.innerformula)
    return self

  def parsetext(self, pos):
    "Parse a text bracket"
    self.parsecomplete(pos, self.innertext)
    return self

  def parseliteral(self, pos):
    "Parse a literal bracket"
    self.parsecomplete(pos, self.innerliteral)
    return self

  def parsecomplete(self, pos, innerparser):
    "Parse the start and end marks"
    if not pos.checkfor(self.start):
      Trace.error('Bracket should start with ' + self.start + ' at ' + pos.identifier())
      return None
    self.skiporiginal(self.start, pos)
    pos.pushending(self.ending)
    innerparser(pos)
    self.original += pos.popending(self.ending)
    self.computesize()

  def innerformula(self, pos):
    "Parse a whole formula inside the bracket"
    while not pos.finished():
      self.add(self.factory.parseany(pos))

  def innertext(self, pos):
    "Parse some text inside the bracket, following textual rules."
    specialchars = list(FormulaConfig.symbolfunctions.keys())
    specialchars.append(FormulaConfig.starts['command'])
    specialchars.append(FormulaConfig.starts['bracket'])
    specialchars.append(Comment.start)
    while not pos.finished():
      if pos.current() in specialchars:
        self.add(self.factory.parseany(pos))
        if pos.checkskip(' '):
          self.original += ' '
      else:
        self.add(FormulaConstant(pos.skipcurrent()))

  def innerliteral(self, pos):
    "Parse a literal inside the bracket, which does not generate HTML."
    self.literal = ''
    while not pos.finished() and not pos.current() == self.ending:
      if pos.current() == self.start:
        self.parseliteral(pos)
      else:
        self.literal += pos.skipcurrent()
    self.original += self.literal

class SquareBracket(Bracket):
  "A [] bracket inside a formula"

  start = FormulaConfig.starts['squarebracket']
  ending = FormulaConfig.endings['squarebracket']

  def clone(self):
    "Return a new square bracket with the same contents."
    bracket = SquareBracket()
    bracket.contents = self.contents
    return bracket



class MathsProcessor(object):
  "A processor for a maths construction inside the FormulaProcessor."

  def process(self, contents, index):
    "Process an element inside a formula."
    Trace.error('Unimplemented process() in ' + str(self))

  def __unicode__(self):
    "Return a printable description."
    return 'Maths processor ' + self.__class__.__name__

class FormulaProcessor(object):
  "A processor specifically for formulas."

  processors = []

  def process(self, bit):
    "Process the contents of every formula bit, recursively."
    self.processcontents(bit)
    self.processinsides(bit)
    self.traversewhole(bit)

  def processcontents(self, bit):
    "Process the contents of a formula bit."
    if not isinstance(bit, FormulaBit):
      return
    bit.process()
    for element in bit.contents:
      self.processcontents(element)

  def processinsides(self, bit):
    "Process the insides (limits, brackets) in a formula bit."
    if not isinstance(bit, FormulaBit):
      return
    for index, element in enumerate(bit.contents):
      for processor in self.processors:
        processor.process(bit.contents, index)
      # continue with recursive processing
      self.processinsides(element)

  def traversewhole(self, formula):
    "Traverse over the contents to alter variables and space units."
    last = None
    for bit, contents in self.traverse(formula):
      if bit.type == 'alpha':
        self.italicize(bit, contents)
      elif bit.type == 'font' and last and last.type == 'number':
        bit.contents.insert(0, FormulaConstant(' '))
      last = bit

  def traverse(self, bit):
    "Traverse a formula and yield a flattened structure of (bit, list) pairs."
    for element in bit.contents:
      if hasattr(element, 'type') and element.type:
        yield (element, bit.contents)
      elif isinstance(element, FormulaBit):
        for pair in self.traverse(element):
          yield pair

  def italicize(self, bit, contents):
    "Italicize the given bit of text."
    index = contents.index(bit)
    contents[index] = TaggedBit().complete([bit], 'i')




class Formula(Container):
  "A LaTeX formula"

  def __init__(self):
    self.parser = FormulaParser()
    self.output = TaggedOutput().settag('span class="formula"')

  def process(self):
    "Convert the formula to tags"
    if self.header[0] == 'inline':
      DocumentParameters.displaymode = False
    else:
      DocumentParameters.displaymode = True
      self.output.settag('div class="formula"', True)
    if Options.jsmath:
      self.jsmath()
    elif Options.mathjax:
      self.mathjax()
    elif Options.googlecharts:
      self.googlecharts()
    else:
      self.classic()

  def jsmath(self):
    "Make the contents for jsMath."
    if self.header[0] != 'inline':
      self.output = TaggedOutput().settag('div class="math"')
    else:
      self.output = TaggedOutput().settag('span class="math"')
    self.contents = [Constant(self.parsed)]

  def mathjax(self):
    "Make the contents for MathJax."
    self.output.tag = 'span class="MathJax_Preview"'
    tag = 'script type="math/tex'
    if self.header[0] != 'inline':
      tag += ';mode=display'
    self.contents = [TaggedText().constant(self.parsed, tag + '"', True)]

  def googlecharts(self):
    "Make the contents using Google Charts http://code.google.com/apis/chart/."
    url = FormulaConfig.urls['googlecharts'] + urllib.parse.quote_plus(self.parsed)
    img = '<img class="chart" src="' + url + '" alt="' + self.parsed + '"/>'
    self.contents = [Constant(img)]

  def classic(self):
    "Make the contents using classic output generation with XHTML and CSS."
    whole = FormulaFactory().parseformula(self.parsed)
    FormulaProcessor().process(whole)
    whole.parent = self
    self.contents = [whole]

  def parse(self, pos):
    "Parse using a parse position instead of self.parser."
    if pos.checkskip('$$'):
      self.parsedollarblock(pos)
    elif pos.checkskip('$'):
      self.parsedollarinline(pos)
    elif pos.checkskip('\\('):
      self.parseinlineto(pos, '\\)')
    elif pos.checkskip('\\['):
      self.parseblockto(pos, '\\]')
    else:
      pos.error('Unparseable formula')
    self.process()
    return self

  def parsedollarinline(self, pos):
    "Parse a $...$ formula."
    self.header = ['inline']
    self.parsedollar(pos)

  def parsedollarblock(self, pos):
    "Parse a $$...$$ formula."
    self.header = ['block']
    self.parsedollar(pos)
    if not pos.checkskip('$'):
      pos.error('Formula should be $$...$$, but last $ is missing.')

  def parsedollar(self, pos):
    "Parse to the next $."
    pos.pushending('$')
    self.parsed = pos.globexcluding('$')
    pos.popending('$')

  def parseinlineto(self, pos, limit):
    "Parse a \\(...\\) formula."
    self.header = ['inline']
    self.parseupto(pos, limit)

  def parseblockto(self, pos, limit):
    "Parse a \\[...\\] formula."
    self.header = ['block']
    self.parseupto(pos, limit)

  def parseupto(self, pos, limit):
    "Parse a formula that ends with the given command."
    pos.pushending(limit)
    self.parsed = pos.glob(lambda: True)
    pos.popending(limit)

  def __unicode__(self):
    "Return a printable representation."
    if self.partkey and self.partkey.number:
      return 'Formula (' + self.partkey.number + ')'
    return 'Unnumbered formula'

class WholeFormula(FormulaBit):
  "Parse a whole formula"

  def detect(self, pos):
    "Not outside the formula is enough."
    return not pos.finished()

  def parsebit(self, pos):
    "Parse with any formula bit"
    while not pos.finished():
      self.add(self.factory.parseany(pos))

class FormulaFactory(object):
  "Construct bits of formula"

  # bit types will be appended later
  types = [FormulaSymbol, RawText, FormulaNumber, Bracket, Comment, WhiteSpace]
  skippedtypes = [Comment, WhiteSpace]
  defining = False

  def __init__(self):
    "Initialize the map of instances."
    self.instances = dict()

  def detecttype(self, type, pos):
    "Detect a bit of a given type."
    if pos.finished():
      return False
    return self.instance(type).detect(pos)

  def instance(self, type):
    "Get an instance of the given type."
    if not type in self.instances or not self.instances[type]:
      self.instances[type] = self.create(type)
    return self.instances[type]

  def create(self, type):
    "Create a new formula bit of the given type."
    return Cloner.create(type).setfactory(self)

  def clearskipped(self, pos):
    "Clear any skipped types."
    while not pos.finished():
      if not self.skipany(pos):
        return
    return

  def skipany(self, pos):
    "Skip any skipped types."
    for type in self.skippedtypes:
      if self.instance(type).detect(pos):
        return self.parsetype(type, pos)
    return None

  def parseany(self, pos):
    "Parse any formula bit at the current location."
    for type in self.types + self.skippedtypes:
      if self.detecttype(type, pos):
        return self.parsetype(type, pos)
    Trace.error('Unrecognized formula at ' + pos.identifier())
    return FormulaConstant(pos.skipcurrent())

  def parsetype(self, type, pos):
    "Parse the given type and return it."
    bit = self.instance(type)
    self.instances[type] = None
    returnedbit = bit.parsebit(pos)
    if returnedbit:
      return returnedbit.setfactory(self)
    return bit

  def parseformula(self, formula):
    "Parse a string of text that contains a whole formula."
    pos = TextPosition(formula)
    whole = self.create(WholeFormula)
    if whole.detect(pos):
      whole.parsebit(pos)
      return whole
    # no formula found
    if not pos.finished():
      Trace.error('Unknown formula at: ' + pos.identifier())
      whole.add(TaggedBit().constant(formula, 'span class="unknown"'))
    return whole




import unicodedata












import gettext


class Translator(object):
  "Reads the configuration file and tries to find a translation."
  "Otherwise falls back to the messages in the config file."

  instance = None

  def translate(cls, key):
    "Get the translated message for a key."
    return cls.instance.getmessage(key)

  translate = classmethod(translate)

  def __init__(self):
    self.translation = None
    self.first = True

  def findtranslation(self):
    "Find the translation for the document language."
    self.langcodes = None
    if not DocumentParameters.language:
      Trace.error('No language in document')
      return
    if not DocumentParameters.language in TranslationConfig.languages:
      Trace.error('Unknown language ' + DocumentParameters.language)
      return
    if TranslationConfig.languages[DocumentParameters.language] == 'en':
      return
    langcodes = [TranslationConfig.languages[DocumentParameters.language]]
    try:
      self.translation = gettext.translation('elyxer', None, langcodes)
    except IOError:
      Trace.error('No translation for ' + str(langcodes))

  def getmessage(self, key):
    "Get the translated message for the given key."
    if self.first:
      self.findtranslation()
      self.first = False
    message = self.getuntranslated(key)
    if not self.translation:
      return message
    try:
      message = self.translation.ugettext(message)
    except IOError:
      pass
    return message

  def getuntranslated(self, key):
    "Get the untranslated message."
    if not key in TranslationConfig.constants:
      Trace.error('Cannot translate ' + key)
      return key
    return TranslationConfig.constants[key]

Translator.instance = Translator()



class NumberCounter(object):
  "A counter for numbers (by default)."
  "The type can be changed to return letters, roman numbers..."

  name = None
  value = None
  mode = None
  master = None

  letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  symbols = NumberingConfig.sequence['symbols']
  romannumerals = [
      ('M', 1000), ('CM', 900), ('D', 500), ('CD', 400), ('C', 100),
      ('XC', 90), ('L', 50), ('XL', 40), ('X', 10), ('IX', 9), ('V', 5),
      ('IV', 4), ('I', 1)
      ]

  def __init__(self, name):
    "Give a name to the counter."
    self.name = name

  def setmode(self, mode):
    "Set the counter mode. Can be changed at runtime."
    self.mode = mode
    return self

  def init(self, value):
    "Set an initial value."
    self.value = value

  def gettext(self):
    "Get the next value as a text string."
    return str(self.value)

  def getletter(self):
    "Get the next value as a letter."
    return self.getsequence(self.letters)

  def getsymbol(self):
    "Get the next value as a symbol."
    return self.getsequence(self.symbols)

  def getsequence(self, sequence):
    "Get the next value from elyxer.a sequence."
    return sequence[(self.value - 1) % len(sequence)]

  def getroman(self):
    "Get the next value as a roman number."
    result = ''
    number = self.value
    for numeral, value in self.romannumerals:
      if number >= value:
        result += numeral * (number / value)
        number = number % value
    return result

  def getvalue(self):
    "Get the current value as configured in the current mode."
    if not self.mode or self.mode in ['text', '1']:
      return self.gettext()
    if self.mode == 'A':
      return self.getletter()
    if self.mode == 'a':
      return self.getletter().lower()
    if self.mode == 'I':
      return self.getroman()
    if self.mode == '*':
      return self.getsymbol()
    Trace.error('Unknown counter mode ' + self.mode)
    return self.gettext()

  def getnext(self):
    "Increase the current value and get the next value as configured."
    if not self.value:
      self.value = 0
    self.value += 1
    return self.getvalue()

  def reset(self):
    "Reset the counter."
    self.value = 0

  def __unicode__(self):
    "Return a printable representation."
    result = 'Counter ' + self.name
    if self.mode:
      result += ' in mode ' + self.mode
    return result

class DependentCounter(NumberCounter):
  "A counter which depends on another one (the master)."

  def setmaster(self, master):
    "Set the master counter."
    self.master = master
    self.last = self.master.getvalue()
    return self

  def getnext(self):
    "Increase or, if the master counter has changed, restart."
    if self.last != self.master.getvalue():
      self.reset()
    value = NumberCounter.getnext(self)
    self.last = self.master.getvalue()
    return value

  def getvalue(self):
    "Get the value of the combined counter: master.dependent."
    return self.master.getvalue() + '.' + NumberCounter.getvalue(self)

class NumberGenerator(object):
  "A number generator for unique sequences and hierarchical structures. Used in:"
  "  * ordered part numbers: Chapter 3, Section 5.3."
  "  * unique part numbers: Footnote 15, Bibliography cite [15]."
  "  * chaptered part numbers: Figure 3.15, Equation (8.3)."
  "  * unique roman part numbers: Part I, Book IV."

  chaptered = None
  generator = None

  romanlayouts = [x.lower() for x in NumberingConfig.layouts['roman']]
  orderedlayouts = [x.lower() for x in NumberingConfig.layouts['ordered']]

  counters = dict()
  appendix = None

  def deasterisk(self, type):
    "Remove the possible asterisk in a layout type."
    return type.replace('*', '')

  def isunique(self, type):
    "Find out if the layout type corresponds to a unique part."
    return self.isroman(type)

  def isroman(self, type):
    "Find out if the layout type should have roman numeration."
    return self.deasterisk(type).lower() in self.romanlayouts

  def isinordered(self, type):
    "Find out if the layout type corresponds to an (un)ordered part."
    return self.deasterisk(type).lower() in self.orderedlayouts

  def isnumbered(self, type):
    "Find out if the type for a layout corresponds to a numbered layout."
    if '*' in type:
      return False
    if self.isroman(type):
      return True
    if not self.isinordered(type):
      return False
    if self.getlevel(type) > DocumentParameters.maxdepth:
      return False
    return True

  def isunordered(self, type):
    "Find out if the type contains an asterisk, basically."
    return '*' in type

  def getlevel(self, type):
    "Get the level that corresponds to a layout type."
    if self.isunique(type):
      return 0
    if not self.isinordered(type):
      Trace.error('Unknown layout type ' + type)
      return 0
    type = self.deasterisk(type).lower()
    level = self.orderedlayouts.index(type) + 1
    return level - DocumentParameters.startinglevel

  def getparttype(self, type):
    "Obtain the type for the part: without the asterisk, "
    "and switched to Appendix if necessary."
    if NumberGenerator.appendix and self.getlevel(type) == 1:
      return 'Appendix'
    return self.deasterisk(type)

  def generate(self, type):
    "Generate a number for a layout type."
    "Unique part types such as Part or Book generate roman numbers: Part I."
    "Ordered part types return dot-separated tuples: Chapter 5, Subsection 2.3.5."
    "Everything else generates unique numbers: Bibliography [1]."
    "Each invocation results in a new number."
    return self.getcounter(type).getnext()

  def getcounter(self, type):
    "Get the counter for the given type."
    type = type.lower()
    if not type in self.counters:
      self.counters[type] = self.create(type)
    return self.counters[type]

  def create(self, type):
    "Create a counter for the given type."
    if self.isnumbered(type) and self.getlevel(type) > 1:
      index = self.orderedlayouts.index(type)
      above = self.orderedlayouts[index - 1]
      master = self.getcounter(above)
      return self.createdependent(type, master)
    counter = NumberCounter(type)
    if self.isroman(type):
      counter.setmode('I')
    return counter

  def getdependentcounter(self, type, master):
    "Get (or create) a counter of the given type that depends on another."
    if not type in self.counters or not self.counters[type].master:
      self.counters[type] = self.createdependent(type, master)
    return self.counters[type]

  def createdependent(self, type, master):
    "Create a dependent counter given the master."
    return DependentCounter(type).setmaster(master)

  def startappendix(self):
    "Start appendices here."
    firsttype = self.orderedlayouts[DocumentParameters.startinglevel]
    counter = self.getcounter(firsttype)
    counter.setmode('A').reset()
    NumberGenerator.appendix = True

class ChapteredGenerator(NumberGenerator):
  "Generate chaptered numbers, as in Chapter.Number."
  "Used in equations, figures: Equation (5.3), figure 8.15."

  def generate(self, type):
    "Generate a number which goes with first-level numbers (chapters). "
    "For the article classes a unique number is generated."
    if DocumentParameters.startinglevel > 0:
      return NumberGenerator.generator.generate(type)
    chapter = self.getcounter('Chapter')
    return self.getdependentcounter(type, chapter).getnext()


NumberGenerator.chaptered = ChapteredGenerator()
NumberGenerator.generator = NumberGenerator()






class ContainerSize(object):
  "The size of a container."

  width = None
  height = None
  maxwidth = None
  maxheight = None
  scale = None

  def set(self, width = None, height = None):
    "Set the proper size with width and height."
    self.setvalue('width', width)
    self.setvalue('height', height)
    return self

  def setmax(self, maxwidth = None, maxheight = None):
    "Set max width and/or height."
    self.setvalue('maxwidth', maxwidth)
    self.setvalue('maxheight', maxheight)
    return self

  def readparameters(self, container):
    "Read some size parameters off a container."
    self.setparameter(container, 'width')
    self.setparameter(container, 'height')
    self.setparameter(container, 'scale')
    self.checkvalidheight(container)
    return self

  def setparameter(self, container, name):
    "Read a size parameter off a container, and set it if present."
    value = container.getparameter(name)
    self.setvalue(name, value)

  def setvalue(self, name, value):
    "Set the value of a parameter name, only if it's valid."
    value = self.processparameter(value)
    if value:
      setattr(self, name, value)

  def checkvalidheight(self, container):
    "Check if the height parameter is valid; otherwise erase it."
    heightspecial = container.getparameter('height_special')
    if self.height and self.extractnumber(self.height) == '1' and heightspecial == 'totalheight':
      self.height = None

  def processparameter(self, value):
    "Do the full processing on a parameter."
    if not value:
      return None
    if self.extractnumber(value) == '0':
      return None
    for ignored in StyleConfig.size['ignoredtexts']:
      if ignored in value:
        value = value.replace(ignored, '')
    return value

  def extractnumber(self, text):
    "Extract the first number in the given text."
    result = ''
    decimal = False
    for char in text:
      if char.isdigit():
        result += char
      elif char == '.' and not decimal:
        result += char
        decimal = True
      else:
        return result
    return result

  def checkimage(self, width, height):
    "Check image dimensions, set them if possible."
    if width:
      self.maxwidth = str(width) + 'px'
      if self.scale and not self.width:
        self.width = self.scalevalue(width)
    if height:
      self.maxheight = str(height) + 'px'
      if self.scale and not self.height:
        self.height = self.scalevalue(height)
    if self.width and not self.height:
      self.height = 'auto'
    if self.height and not self.width:
      self.width = 'auto'

  def scalevalue(self, value):
    "Scale the value according to the image scale and return it as unicode."
    scaled = value * int(self.scale) / 100
    return str(int(scaled)) + 'px'

  def removepercentwidth(self):
    "Remove percent width if present, to set it at the figure level."
    if not self.width:
      return None
    if not '%' in self.width:
      return None
    width = self.width
    self.width = None
    if self.height == 'auto':
      self.height = None
    return width

  def addstyle(self, container):
    "Add the proper style attribute to the output tag."
    if not isinstance(container.output, TaggedOutput):
      Trace.error('No tag to add style, in ' + str(container))
    if not self.width and not self.height and not self.maxwidth and not self.maxheight:
      # nothing to see here; move along
      return
    tag = ' style="'
    tag += self.styleparameter('width')
    tag += self.styleparameter('maxwidth')
    tag += self.styleparameter('height')
    tag += self.styleparameter('maxheight')
    if tag[-1] == ' ':
      tag = tag[:-1]
    tag += '"'
    container.output.tag += tag

  def styleparameter(self, name):
    "Get the style for a single parameter."
    value = getattr(self, name)
    if value:
      return name.replace('max', 'max-') + ': ' + value + '; '
    return ''



class QuoteContainer(Container):
  "A container for a pretty quote"

  def __init__(self):
    self.parser = BoundedParser()
    self.output = FixedOutput()

  def process(self):
    "Process contents"
    self.type = self.header[2]
    if not self.type in StyleConfig.quotes:
      Trace.error('Quote type ' + self.type + ' not found')
      self.html = ['"']
      return
    self.html = [StyleConfig.quotes[self.type]]

class LyXLine(Container):
  "A Lyx line"

  def __init__(self):
    self.parser = LoneCommand()
    self.output = FixedOutput()

  def process(self):
    self.html = ['<hr class="line" />']

class EmphaticText(TaggedText):
  "Text with emphatic mode"

  def process(self):
    self.output.tag = 'i'

class ShapedText(TaggedText):
  "Text shaped (italic, slanted)"

  def process(self):
    self.type = self.header[1]
    if not self.type in TagConfig.shaped:
      Trace.error('Unrecognized shape ' + self.header[1])
      self.output.tag = 'span'
      return
    self.output.tag = TagConfig.shaped[self.type]

class VersalitasText(TaggedText):
  "Text in versalitas"

  def process(self):
    self.output.tag = 'span class="versalitas"'

class ColorText(TaggedText):
  "Colored text"

  def process(self):
    self.color = self.header[1]
    self.output.tag = 'span class="' + self.color + '"'

class SizeText(TaggedText):
  "Sized text"

  def process(self):
    self.size = self.header[1]
    self.output.tag = 'span class="' + self.size + '"'

class BoldText(TaggedText):
  "Bold text"

  def process(self):
    self.output.tag = 'b'

class TextFamily(TaggedText):
  "A bit of text from elyxer.a different family"

  def process(self):
    "Parse the type of family"
    self.type = self.header[1]
    if not self.type in TagConfig.family:
      Trace.error('Unrecognized family ' + type)
      self.output.tag = 'span'
      return
    self.output.tag = TagConfig.family[self.type]

class Hfill(TaggedText):
  "Horizontall fill"

  def process(self):
    self.output.tag = 'span class="hfill"'

class BarredText(TaggedText):
  "Text with a bar somewhere"

  def process(self):
    "Parse the type of bar"
    self.type = self.header[1]
    if not self.type in TagConfig.barred:
      Trace.error('Unknown bar type ' + self.type)
      self.output.tag = 'span'
      return
    self.output.tag = TagConfig.barred[self.type]

class LangLine(TaggedText):
  "A line with language information"

  def process(self):
    "Only generate a span with lang info when the language is recognized."
    lang = self.header[1]
    if not lang in TranslationConfig.languages:
      self.output = ContentsOutput()
      return
    isolang = TranslationConfig.languages[lang]
    self.output = TaggedOutput().settag('span lang="' + isolang + '"', False)

class InsetLength(BlackBox):
  "A length measure inside an inset."

  def process(self):
    self.length = self.header[1]

class Space(Container):
  "A space of several types"

  def __init__(self):
    self.parser = InsetParser()
    self.output = FixedOutput()
  
  def process(self):
    self.type = self.header[2]
    if self.type not in StyleConfig.hspaces:
      Trace.error('Unknown space type ' + self.type)
      self.html = [' ']
      return
    self.html = [StyleConfig.hspaces[self.type]]
    length = self.getlength()
    if not length:
      return
    self.output = TaggedOutput().settag('span class="hspace"', False)
    ContainerSize().set(length).addstyle(self)

  def getlength(self):
    "Get the space length from elyxer.the contents or parameters."
    if len(self.contents) == 0 or not isinstance(self.contents[0], InsetLength):
      return None
    return self.contents[0].length

class VerticalSpace(Container):
  "An inset that contains a vertical space."

  def __init__(self):
    self.parser = InsetParser()
    self.output = FixedOutput()

  def process(self):
    "Set the correct tag"
    self.type = self.header[2]
    if self.type not in StyleConfig.vspaces:
      self.output = TaggedOutput().settag('div class="vspace" style="height: ' + self.type + ';"', True)
      return
    self.html = [StyleConfig.vspaces[self.type]]

class Align(Container):
  "Bit of aligned text"

  def __init__(self):
    self.parser = ExcludingParser()
    self.output = TaggedOutput().setbreaklines(True)

  def process(self):
    self.output.tag = 'div class="' + self.header[1] + '"'

class Newline(Container):
  "A newline"

  def __init__(self):
    self.parser = LoneCommand()
    self.output = FixedOutput()

  def process(self):
    "Process contents"
    self.html = ['<br/>\n']

class NewPage(Newline):
  "A new page"

  def process(self):
    "Process contents"
    self.html = ['<p><br/>\n</p>\n']

class Separator(Container):
  "A separator string which is not extracted by extracttext()."

  def __init__(self, constant):
    self.output = FixedOutput()
    self.contents = []
    self.html = [constant]

class StrikeOut(TaggedText):
  "Striken out text."

  def process(self):
    "Set the output tag to strike."
    self.output.tag = 'strike'

class StartAppendix(BlackBox):
  "Mark to start an appendix here."
  "From this point on, all chapters become appendices."

  def process(self):
    "Activate the special numbering scheme for appendices, using letters."
    NumberGenerator.generator.startappendix()






class Link(Container):
  "A link to another part of the document"

  anchor = None
  url = None
  type = None
  page = None
  target = None
  destination = None
  title = None

  def __init__(self):
    "Initialize the link, add target if configured."
    self.contents = []
    self.parser = InsetParser()
    self.output = LinkOutput()
    if Options.target:
      self.target = Options.target

  def complete(self, text, anchor = None, url = None, type = None, title = None):
    "Complete the link."
    self.contents = [Constant(text)]
    if anchor:
      self.anchor = anchor
    if url:
      self.url = url
    if type:
      self.type = type
    if title:
      self.title = title
    return self

  def computedestination(self):
    "Use the destination link to fill in the destination URL."
    if not self.destination:
      return
    self.url = ''
    if self.destination.anchor:
      self.url = '#' + self.destination.anchor
    if self.destination.page:
      self.url = self.destination.page + self.url

  def setmutualdestination(self, destination):
    "Set another link as destination, and set its destination to this one."
    self.destination = destination
    destination.destination = self

  def __unicode__(self):
    "Return a printable representation."
    result = 'Link'
    if self.anchor:
      result += ' #' + self.anchor
    if self.url:
      result += ' to ' + self.url
    return result

class URL(Link):
  "A clickable URL"

  def process(self):
    "Read URL from elyxer.parameters"
    target = self.escape(self.getparameter('target'))
    self.url = target
    type = self.getparameter('type')
    if type:
      self.url = self.escape(type) + target
    name = self.getparameter('name')
    if not name:
      name = target
    self.contents = [Constant(name)]

class FlexURL(URL):
  "A flexible URL"

  def process(self):
    "Read URL from elyxer.contents"
    self.url = self.extracttext()

class LinkOutput(ContainerOutput):
  "A link pointing to some destination"
  "Or an anchor (destination)"

  def gethtml(self, link):
    "Get the HTML code for the link"
    type = link.__class__.__name__
    if link.type:
      type = link.type
    tag = 'a class="' + type + '"'
    if link.anchor:
      tag += ' name="' + link.anchor + '"'
    if link.destination:
      link.computedestination()
    if link.url:
      tag += ' href="' + link.url + '"'
    if link.target:
      tag += ' target="' + link.target + '"'
    if link.title:
      tag += ' title="' + link.title + '"'
    return TaggedOutput().settag(tag).gethtml(link)





class Postprocessor(object):
  "Postprocess a container keeping some context"

  stages = []

  def __init__(self):
    self.stages = StageDict(Postprocessor.stages, self)
    self.current = None
    self.last = None

  def postprocess(self, next):
    "Postprocess a container and its contents."
    self.postrecursive(self.current)
    result = self.postcurrent(next)
    self.last = self.current
    self.current = next
    return result

  def postrecursive(self, container):
    "Postprocess the container contents recursively"
    if not hasattr(container, 'contents'):
      return
    if len(container.contents) == 0:
      return
    if hasattr(container, 'postprocess'):
      if not container.postprocess:
        return
    postprocessor = Postprocessor()
    contents = []
    for element in container.contents:
      post = postprocessor.postprocess(element)
      if post:
        contents.append(post)
    # two rounds to empty the pipeline
    for i in range(2):
      post = postprocessor.postprocess(None)
      if post:
        contents.append(post)
    container.contents = contents

  def postcurrent(self, next):
    "Postprocess the current element taking into account next and last."
    stage = self.stages.getstage(self.current)
    if not stage:
      return self.current
    return stage.postprocess(self.last, self.current, next)

class StageDict(object):
  "A dictionary of stages corresponding to classes"

  def __init__(self, classes, postprocessor):
    "Instantiate an element from elyxer.each class and store as a dictionary"
    instances = self.instantiate(classes, postprocessor)
    self.stagedict = dict([(x.processedclass, x) for x in instances])

  def instantiate(self, classes, postprocessor):
    "Instantiate an element from elyxer.each class"
    stages = [x.__new__(x) for x in classes]
    for element in stages:
      element.__init__()
      element.postprocessor = postprocessor
    return stages

  def getstage(self, element):
    "Get the stage for a given element, if the type is in the dict"
    if not element.__class__ in self.stagedict:
      return None
    return self.stagedict[element.__class__]



class Label(Link):
  "A label to be referenced"

  names = dict()
  lastlayout = None

  def __init__(self):
    Link.__init__(self)
    self.lastnumbered = None

  def process(self):
    "Process a label container."
    key = self.getparameter('name')
    self.create(' ', key)
    self.lastnumbered = Label.lastlayout

  def create(self, text, key, type = 'Label'):
    "Create the label for a given key."
    self.key = key
    self.complete(text, anchor = key, type = type)
    Label.names[key] = self
    if key in Reference.references:
      for reference in Reference.references[key]:
        reference.destination = self
    return self

  def findpartkey(self):
    "Get the part key for the latest numbered container seen."
    numbered = self.numbered(self)
    if numbered and numbered.partkey:
      return numbered.partkey
    return ''

  def numbered(self, container):
    "Get the numbered container for the label."
    if container.partkey:
      return container
    if not container.parent:
      if self.lastnumbered:
        return self.lastnumbered
      return None
    return self.numbered(container.parent)

  def __unicode__(self):
    "Return a printable representation."
    if not hasattr(self, 'key'):
      return 'Unnamed label'
    return 'Label ' + self.key

class Reference(Link):
  "A reference to a label."

  references = dict()
  key = 'none'

  def process(self):
    "Read the reference and set the arrow."
    self.key = self.getparameter('reference')
    if self.key in Label.names:
      self.direction = '↑'
      label = Label.names[self.key]
    else:
      self.direction = '↓'
      label = Label().complete(' ', self.key, 'preref')
    self.destination = label
    self.formatcontents()
    if not self.key in Reference.references:
      Reference.references[self.key] = []
    Reference.references[self.key].append(self)

  def formatcontents(self):
    "Format the reference contents."
    formatkey = self.getparameter('LatexCommand')
    if not formatkey:
      formatkey = 'ref'
    self.formatted = '↕'
    if formatkey in StyleConfig.referenceformats:
      self.formatted = StyleConfig.referenceformats[formatkey]
    else:
      Trace.error('Unknown reference format ' + formatkey)
    self.replace('↕', self.direction)
    self.replace('#', '1')
    self.replace('on-page', Translator.translate('on-page'))
    partkey = self.destination.findpartkey()
    # only if partkey and partkey.number are not null, send partkey.number
    self.replace('@', partkey and partkey.number)
    self.replace('¶', partkey and partkey.tocentry)
    if not '$' in self.formatted or not partkey or not partkey.titlecontents:
      # there is a $ left, but it should go away on preprocessing
      self.contents = [Constant(self.formatted)]
      return
    pieces = self.formatted.split('$')
    self.contents = [Constant(pieces[0])]
    for piece in pieces[1:]:
      self.contents += partkey.titlecontents
      self.contents.append(Constant(piece))

  def replace(self, key, value):
    "Replace a key in the format template with a value."
    if not key in self.formatted:
      return
    if not value:
      value = ''
    self.formatted = self.formatted.replace(key, value)

  def __unicode__(self):
    "Return a printable representation."
    return 'Reference ' + self.key



class FormulaCommand(FormulaBit):
  "A LaTeX command inside a formula"

  types = []
  start = FormulaConfig.starts['command']
  commandmap = None

  def detect(self, pos):
    "Find the current command."
    return pos.checkfor(FormulaCommand.start)

  def parsebit(self, pos):
    "Parse the command."
    command = self.extractcommand(pos)
    bit = self.parsewithcommand(command, pos)
    if bit:
      return bit
    if command.startswith('\\up') or command.startswith('\\Up'):
      upgreek = self.parseupgreek(command, pos)
      if upgreek:
        return upgreek
    if not self.factory.defining:
      Trace.error('Unknown command ' + command)
    self.output = TaggedOutput().settag('span class="unknown"')
    self.add(FormulaConstant(command))
    return None

  def parsewithcommand(self, command, pos):
    "Parse the command type once we have the command."
    for type in FormulaCommand.types:
      if command in type.commandmap:
        return self.parsecommandtype(command, type, pos)
    return None

  def parsecommandtype(self, command, type, pos):
    "Parse a given command type."
    bit = self.factory.create(type)
    bit.setcommand(command)
    returned = bit.parsebit(pos)
    if returned:
      return returned
    return bit

  def extractcommand(self, pos):
    "Extract the command from elyxer.the current position."
    if not pos.checkskip(FormulaCommand.start):
      pos.error('Missing command start ' + FormulaCommand.start)
      return
    if pos.finished():
      return self.emptycommand(pos)
    if pos.current().isalpha():
      # alpha command
      command = FormulaCommand.start + pos.globalpha()
      # skip mark of short command
      pos.checkskip('*')
      return command
    # symbol command
    return FormulaCommand.start + pos.skipcurrent()

  def emptycommand(self, pos):
    """Check for an empty command: look for command disguised as ending.
    Special case against '{ \\{ \\} }' situation."""
    command = ''
    if not pos.isout():
      ending = pos.nextending()
      if ending and pos.checkskip(ending):
        command = ending
    return FormulaCommand.start + command

  def parseupgreek(self, command, pos):
    "Parse the Greek \\up command.."
    if len(command) < 4:
      return None
    if command.startswith('\\up'):
      upcommand = '\\' + command[3:]
    elif pos.checkskip('\\Up'):
      upcommand = '\\' + command[3:4].upper() + command[4:]
    else:
      Trace.error('Impossible upgreek command: ' + command)
      return
    upgreek = self.parsewithcommand(upcommand, pos)
    if upgreek:
      upgreek.type = 'font'
    return upgreek

class CommandBit(FormulaCommand):
  "A formula bit that includes a command"

  def setcommand(self, command):
    "Set the command in the bit"
    self.command = command
    if self.commandmap:
      self.original += command
      self.translated = self.commandmap[self.command]
 
  def parseparameter(self, pos):
    "Parse a parameter at the current position"
    self.factory.clearskipped(pos)
    if pos.finished():
      return None
    parameter = self.factory.parseany(pos)
    self.add(parameter)
    return parameter

  def parsesquare(self, pos):
    "Parse a square bracket"
    self.factory.clearskipped(pos)
    if not self.factory.detecttype(SquareBracket, pos):
      return None
    bracket = self.factory.parsetype(SquareBracket, pos)
    self.add(bracket)
    return bracket

  def parseliteral(self, pos):
    "Parse a literal bracket."
    self.factory.clearskipped(pos)
    if not self.factory.detecttype(Bracket, pos):
      if not pos.isvalue():
        Trace.error('No literal parameter found at: ' + pos.identifier())
        return None
      return pos.globvalue()
    bracket = Bracket().setfactory(self.factory)
    self.add(bracket.parseliteral(pos))
    return bracket.literal

  def parsesquareliteral(self, pos):
    "Parse a square bracket literally."
    self.factory.clearskipped(pos)
    if not self.factory.detecttype(SquareBracket, pos):
      return None
    bracket = SquareBracket().setfactory(self.factory)
    self.add(bracket.parseliteral(pos))
    return bracket.literal

  def parsetext(self, pos):
    "Parse a text parameter."
    self.factory.clearskipped(pos)
    if not self.factory.detecttype(Bracket, pos):
      Trace.error('No text parameter for ' + self.command)
      return None
    bracket = Bracket().setfactory(self.factory).parsetext(pos)
    self.add(bracket)
    return bracket

class EmptyCommand(CommandBit):
  "An empty command (without parameters)"

  commandmap = FormulaConfig.commands

  def parsebit(self, pos):
    "Parse a command without parameters"
    self.contents = [FormulaConstant(self.translated)]

class SpacedCommand(CommandBit):
  "An empty command which should have math spacing in formulas."

  commandmap = FormulaConfig.spacedcommands

  def parsebit(self, pos):
    "Place as contents the command translated and spaced."
    self.contents = [FormulaConstant(' ' + self.translated + ' ')]

class AlphaCommand(EmptyCommand):
  "A command without paramters whose result is alphabetical"

  commandmap = FormulaConfig.alphacommands

  def parsebit(self, pos):
    "Parse the command and set type to alpha"
    EmptyCommand.parsebit(self, pos)
    self.type = 'alpha'

class OneParamFunction(CommandBit):
  "A function of one parameter"

  commandmap = FormulaConfig.onefunctions
  simplified = False

  def parsebit(self, pos):
    "Parse a function with one parameter"
    self.output = TaggedOutput().settag(self.translated)
    self.parseparameter(pos)
    self.simplifyifpossible()

  def simplifyifpossible(self):
    "Try to simplify to a single character."
    if self.original in self.commandmap:
      self.output = FixedOutput()
      self.html = [self.commandmap[self.original]]
      self.simplified = True

class SymbolFunction(CommandBit):
  "Find a function which is represented by a symbol (like _ or ^)"

  commandmap = FormulaConfig.symbolfunctions

  def detect(self, pos):
    "Find the symbol"
    return pos.current() in SymbolFunction.commandmap

  def parsebit(self, pos):
    "Parse the symbol"
    self.setcommand(pos.current())
    pos.skip(self.command)
    self.output = TaggedOutput().settag(self.translated)
    self.parseparameter(pos)

class TextFunction(CommandBit):
  "A function where parameters are read as text."

  commandmap = FormulaConfig.textfunctions

  def parsebit(self, pos):
    "Parse a text parameter"
    self.output = TaggedOutput().settag(self.translated)
    self.parsetext(pos)

  def process(self):
    "Set the type to font"
    self.type = 'font'

class LabelFunction(CommandBit):
  "A function that acts as a label"

  commandmap = FormulaConfig.labelfunctions

  def parsebit(self, pos):
    "Parse a literal parameter"
    self.key = self.parseliteral(pos)

  def process(self):
    "Add an anchor with the label contents."
    self.type = 'font'
    self.label = Label().create(' ', self.key, type = 'eqnumber')
    self.contents = [self.label]
    # store as a Label so we know it's been seen
    Label.names[self.key] = self.label

class FontFunction(OneParamFunction):
  "A function of one parameter that changes the font"

  commandmap = FormulaConfig.fontfunctions

  def process(self):
    "Simplify if possible using a single character."
    self.type = 'font'
    self.simplifyifpossible()

FormulaFactory.types += [FormulaCommand, SymbolFunction]
FormulaCommand.types = [
    AlphaCommand, EmptyCommand, OneParamFunction, FontFunction, LabelFunction,
    TextFunction, SpacedCommand,
    ]












class BigSymbol(object):
  "A big symbol generator."

  symbols = FormulaConfig.bigsymbols

  def __init__(self, symbol):
    "Create the big symbol."
    self.symbol = symbol

  def getpieces(self):
    "Get an array with all pieces."
    if not self.symbol in self.symbols:
      return [self.symbol]
    if self.smalllimit():
      return [self.symbol]
    return self.symbols[self.symbol]

  def smalllimit(self):
    "Decide if the limit should be a small, one-line symbol."
    if not DocumentParameters.displaymode:
      return True
    if len(self.symbols[self.symbol]) == 1:
      return True
    return Options.simplemath

class BigBracket(BigSymbol):
  "A big bracket generator."

  def __init__(self, size, bracket, alignment='l'):
    "Set the size and symbol for the bracket."
    self.size = size
    self.original = bracket
    self.alignment = alignment
    self.pieces = None
    if bracket in FormulaConfig.bigbrackets:
      self.pieces = FormulaConfig.bigbrackets[bracket]

  def getpiece(self, index):
    "Return the nth piece for the bracket."
    function = getattr(self, 'getpiece' + str(len(self.pieces)))
    return function(index)

  def getpiece1(self, index):
    "Return the only piece for a single-piece bracket."
    return self.pieces[0]

  def getpiece3(self, index):
    "Get the nth piece for a 3-piece bracket: parenthesis or square bracket."
    if index == 0:
      return self.pieces[0]
    if index == self.size - 1:
      return self.pieces[-1]
    return self.pieces[1]

  def getpiece4(self, index):
    "Get the nth piece for a 4-piece bracket: curly bracket."
    if index == 0:
      return self.pieces[0]
    if index == self.size - 1:
      return self.pieces[3]
    if index == (self.size - 1)/2:
      return self.pieces[2]
    return self.pieces[1]

  def getcell(self, index):
    "Get the bracket piece as an array cell."
    piece = self.getpiece(index)
    span = 'span class="bracket align-' + self.alignment + '"'
    return TaggedBit().constant(piece, span)

  def getcontents(self):
    "Get the bracket as an array or as a single bracket."
    if self.size == 1 or not self.pieces:
      return self.getsinglebracket()
    rows = []
    for index in range(self.size):
      cell = self.getcell(index)
      rows.append(TaggedBit().complete([cell], 'span class="arrayrow"'))
    return [TaggedBit().complete(rows, 'span class="array"')]

  def getsinglebracket(self):
    "Return the bracket as a single sign."
    if self.original == '.':
      return [TaggedBit().constant('', 'span class="emptydot"')]
    return [TaggedBit().constant(self.original, 'span class="symbol"')]






class FormulaEquation(CommandBit):
  "A simple numbered equation."

  piece = 'equation'

  def parsebit(self, pos):
    "Parse the array"
    self.output = ContentsOutput()
    self.add(self.factory.parsetype(WholeFormula, pos))

class FormulaCell(FormulaCommand):
  "An array cell inside a row"

  def setalignment(self, alignment):
    self.alignment = alignment
    self.output = TaggedOutput().settag('span class="arraycell align-' + alignment +'"', True)
    return self

  def parsebit(self, pos):
    self.factory.clearskipped(pos)
    if pos.finished():
      return
    self.add(self.factory.parsetype(WholeFormula, pos))

class FormulaRow(FormulaCommand):
  "An array row inside an array"

  cellseparator = FormulaConfig.array['cellseparator']

  def setalignments(self, alignments):
    self.alignments = alignments
    self.output = TaggedOutput().settag('span class="arrayrow"', True)
    return self

  def parsebit(self, pos):
    "Parse a whole row"
    index = 0
    pos.pushending(self.cellseparator, optional=True)
    while not pos.finished():
      cell = self.createcell(index)
      cell.parsebit(pos)
      self.add(cell)
      index += 1
      pos.checkskip(self.cellseparator)
    if len(self.contents) == 0:
      self.output = EmptyOutput()

  def createcell(self, index):
    "Create the cell that corresponds to the given index."
    alignment = self.alignments[index % len(self.alignments)]
    return self.factory.create(FormulaCell).setalignment(alignment)

class MultiRowFormula(CommandBit):
  "A formula with multiple rows."

  def parserows(self, pos):
    "Parse all rows, finish when no more row ends"
    self.rows = []
    first = True
    for row in self.iteraterows(pos):
      if first:
        first = False
      else:
        # intersparse empty rows
        self.addempty()
      row.parsebit(pos)
      self.addrow(row)
    self.size = len(self.rows)

  def iteraterows(self, pos):
    "Iterate over all rows, end when no more row ends"
    rowseparator = FormulaConfig.array['rowseparator']
    while True:
      pos.pushending(rowseparator, True)
      row = self.factory.create(FormulaRow)
      yield row.setalignments(self.alignments)
      if pos.checkfor(rowseparator):
        self.original += pos.popending(rowseparator)
      else:
        return

  def addempty(self):
    "Add an empty row."
    row = self.factory.create(FormulaRow).setalignments(self.alignments)
    for index, originalcell in enumerate(self.rows[-1].contents):
      cell = row.createcell(index)
      cell.add(FormulaConstant(' '))
      row.add(cell)
    self.addrow(row)

  def addrow(self, row):
    "Add a row to the contents and to the list of rows."
    self.rows.append(row)
    self.add(row)

class FormulaArray(MultiRowFormula):
  "An array within a formula"

  piece = 'array'

  def parsebit(self, pos):
    "Parse the array"
    self.output = TaggedOutput().settag('span class="array"', False)
    self.parsealignments(pos)
    self.parserows(pos)

  def parsealignments(self, pos):
    "Parse the different alignments"
    # vertical
    self.valign = 'c'
    literal = self.parsesquareliteral(pos)
    if literal:
      self.valign = literal
    # horizontal
    literal = self.parseliteral(pos)
    self.alignments = []
    for l in literal:
      self.alignments.append(l)

class FormulaMatrix(MultiRowFormula):
  "A matrix (array with center alignment)."

  piece = 'matrix'

  def parsebit(self, pos):
    "Parse the matrix, set alignments to 'c'."
    self.output = TaggedOutput().settag('span class="array"', False)
    self.valign = 'c'
    self.alignments = ['c']
    self.parserows(pos)

class FormulaCases(MultiRowFormula):
  "A cases statement"

  piece = 'cases'

  def parsebit(self, pos):
    "Parse the cases"
    self.output = ContentsOutput()
    self.alignments = ['l', 'l']
    self.parserows(pos)
    for row in self.contents:
      for cell in row.contents:
        cell.output.settag('span class="case align-l"', True)
        cell.contents.append(FormulaConstant(' '))
    array = TaggedBit().complete(self.contents, 'span class="bracketcases"', True)
    brace = BigBracket(len(self.contents), '{', 'l')
    self.contents = brace.getcontents() + [array]

class EquationEnvironment(MultiRowFormula):
  "A \\begin{}...\\end equation environment with rows and cells."

  def parsebit(self, pos):
    "Parse the whole environment."
    self.output = TaggedOutput().settag('span class="environment"', False)
    environment = self.piece.replace('*', '')
    if environment in FormulaConfig.environments:
      self.alignments = FormulaConfig.environments[environment]
    else:
      Trace.error('Unknown equation environment ' + self.piece)
      self.alignments = ['l']
    self.parserows(pos)

class BeginCommand(CommandBit):
  "A \\begin{}...\\end command and what it entails (array, cases, aligned)"

  commandmap = {FormulaConfig.array['begin']:''}

  types = [FormulaEquation, FormulaArray, FormulaCases, FormulaMatrix]

  def parsebit(self, pos):
    "Parse the begin command"
    command = self.parseliteral(pos)
    bit = self.findbit(command)
    ending = FormulaConfig.array['end'] + '{' + command + '}'
    pos.pushending(ending)
    bit.parsebit(pos)
    self.add(bit)
    self.original += pos.popending(ending)
    self.size = bit.size

  def findbit(self, piece):
    "Find the command bit corresponding to the \\begin{piece}"
    for type in BeginCommand.types:
      if piece.replace('*', '') == type.piece:
        return self.factory.create(type)
    bit = self.factory.create(EquationEnvironment)
    bit.piece = piece
    return bit

FormulaCommand.types += [BeginCommand]


import datetime


class CombiningFunction(OneParamFunction):

  commandmap = FormulaConfig.combiningfunctions

  def parsebit(self, pos):
    "Parse a combining function."
    self.type = 'alpha'
    combining = self.translated
    parameter = self.parsesingleparameter(pos)
    if not parameter:
      Trace.error('Empty parameter for combining function ' + self.command)
    elif len(parameter.extracttext()) != 1:
      Trace.error('Applying combining function ' + self.command + ' to invalid string "' + parameter.extracttext() + '"')
    self.contents.append(Constant(combining))

  def parsesingleparameter(self, pos):
    "Parse a parameter, or a single letter."
    self.factory.clearskipped(pos)
    if pos.finished():
      Trace.error('Error while parsing single parameter at ' + pos.identifier())
      return None
    if self.factory.detecttype(Bracket, pos) \
        or self.factory.detecttype(FormulaCommand, pos):
      return self.parseparameter(pos)
    letter = FormulaConstant(pos.skipcurrent())
    self.add(letter)
    return letter

class DecoratingFunction(OneParamFunction):
  "A function that decorates some bit of text"

  commandmap = FormulaConfig.decoratingfunctions

  def parsebit(self, pos):
    "Parse a decorating function"
    self.type = 'alpha'
    symbol = self.translated
    self.symbol = TaggedBit().constant(symbol, 'span class="symbolover"')
    self.parameter = self.parseparameter(pos)
    self.output = TaggedOutput().settag('span class="withsymbol"')
    self.contents.insert(0, self.symbol)
    self.parameter.output = TaggedOutput().settag('span class="undersymbol"')
    self.simplifyifpossible()

class LimitCommand(EmptyCommand):
  "A command which accepts limits above and below, in display mode."

  commandmap = FormulaConfig.limitcommands

  def parsebit(self, pos):
    "Parse a limit command."
    pieces = BigSymbol(self.translated).getpieces()
    self.output = TaggedOutput().settag('span class="limits"')
    for piece in pieces:
      self.contents.append(TaggedBit().constant(piece, 'span class="limit"'))

class LimitPreviousCommand(LimitCommand):
  "A command to limit the previous command."

  commandmap = None

  def parsebit(self, pos):
    "Do nothing."
    self.output = TaggedOutput().settag('span class="limits"')
    self.factory.clearskipped(pos)

  def __unicode__(self):
    "Return a printable representation."
    return 'Limit previous command'

class LimitsProcessor(MathsProcessor):
  "A processor for limits inside an element."

  def process(self, contents, index):
    "Process the limits for an element."
    if Options.simplemath:
      return
    if self.checklimits(contents, index):
      self.modifylimits(contents, index)
    if self.checkscript(contents, index) and self.checkscript(contents, index + 1):
      self.modifyscripts(contents, index)

  def checklimits(self, contents, index):
    "Check if the current position has a limits command."
    if not DocumentParameters.displaymode:
      return False
    if self.checkcommand(contents, index + 1, LimitPreviousCommand):
      self.limitsahead(contents, index)
      return False
    if not isinstance(contents[index], LimitCommand):
      return False
    return self.checkscript(contents, index + 1)

  def limitsahead(self, contents, index):
    "Limit the current element based on the next."
    contents[index + 1].add(contents[index].clone())
    contents[index].output = EmptyOutput()

  def modifylimits(self, contents, index):
    "Modify a limits commands so that the limits appear above and below."
    limited = contents[index]
    subscript = self.getlimit(contents, index + 1)
    limited.contents.append(subscript)
    if self.checkscript(contents, index + 1):
      superscript = self.getlimit(contents, index  + 1)
    else:
      superscript = TaggedBit().constant(' ', 'sup class="limit"')
    limited.contents.insert(0, superscript)

  def getlimit(self, contents, index):
    "Get the limit for a limits command."
    limit = self.getscript(contents, index)
    limit.output.tag = limit.output.tag.replace('script', 'limit')
    return limit

  def modifyscripts(self, contents, index):
    "Modify the super- and subscript to appear vertically aligned."
    subscript = self.getscript(contents, index)
    # subscript removed so instead of index + 1 we get index again
    superscript = self.getscript(contents, index)
    scripts = TaggedBit().complete([superscript, subscript], 'span class="scripts"')
    contents.insert(index, scripts)

  def checkscript(self, contents, index):
    "Check if the current element is a sub- or superscript."
    return self.checkcommand(contents, index, SymbolFunction)

  def checkcommand(self, contents, index, type):
    "Check for the given type as the current element."
    if len(contents) <= index:
      return False
    return isinstance(contents[index], type)

  def getscript(self, contents, index):
    "Get the sub- or superscript."
    bit = contents[index]
    bit.output.tag += ' class="script"'
    del contents[index]
    return bit

class BracketCommand(OneParamFunction):
  "A command which defines a bracket."

  commandmap = FormulaConfig.bracketcommands

  def parsebit(self, pos):
    "Parse the bracket."
    OneParamFunction.parsebit(self, pos)

  def create(self, direction, character):
    "Create the bracket for the given character."
    self.original = character
    self.command = '\\' + direction
    self.contents = [FormulaConstant(character)]
    return self

class BracketProcessor(MathsProcessor):
  "A processor for bracket commands."

  def process(self, contents, index):
    "Convert the bracket using Unicode pieces, if possible."
    if Options.simplemath:
      return
    if self.checkleft(contents, index):
      return self.processleft(contents, index)

  def processleft(self, contents, index):
    "Process a left bracket."
    rightindex = self.findright(contents, index + 1)
    if not rightindex:
      return
    size = self.findmax(contents, index, rightindex)
    self.resize(contents[index], size)
    self.resize(contents[rightindex], size)

  def checkleft(self, contents, index):
    "Check if the command at the given index is left."
    return self.checkdirection(contents[index], '\\left')
  
  def checkright(self, contents, index):
    "Check if the command at the given index is right."
    return self.checkdirection(contents[index], '\\right')

  def checkdirection(self, bit, command):
    "Check if the given bit is the desired bracket command."
    if not isinstance(bit, BracketCommand):
      return False
    return bit.command == command

  def findright(self, contents, index):
    "Find the right bracket starting at the given index, or 0."
    depth = 1
    while index < len(contents):
      if self.checkleft(contents, index):
        depth += 1
      if self.checkright(contents, index):
        depth -= 1
      if depth == 0:
        return index
      index += 1
    return None

  def findmax(self, contents, leftindex, rightindex):
    "Find the max size of the contents between the two given indices."
    sliced = contents[leftindex:rightindex]
    return max([element.size for element in sliced])

  def resize(self, command, size):
    "Resize a bracket command to the given size."
    character = command.extracttext()
    alignment = command.command.replace('\\', '')
    bracket = BigBracket(size, character, alignment)
    command.output = ContentsOutput()
    command.contents = bracket.getcontents()

class TodayCommand(EmptyCommand):
  "Shows today's date."

  commandmap = None

  def parsebit(self, pos):
    "Parse a command without parameters"
    self.output = FixedOutput()
    self.html = [datetime.date.today().strftime('%b %d, %Y')]


FormulaCommand.types += [
    DecoratingFunction, CombiningFunction, LimitCommand, BracketCommand,
    ]

FormulaProcessor.processors += [
    LimitsProcessor(), BracketProcessor(),
    ]



class ParameterDefinition(object):
  "The definition of a parameter in a hybrid function."
  "[] parameters are optional, {} parameters are mandatory."
  "Each parameter has a one-character name, like {$1} or {$p}."
  "A parameter that ends in ! like {$p!} is a literal."
  "Example: [$1]{$p!} reads an optional parameter $1 and a literal mandatory parameter p."

  parambrackets = [('[', ']'), ('{', '}')]

  def __init__(self):
    self.name = None
    self.literal = False
    self.optional = False
    self.value = None
    self.literalvalue = None

  def parse(self, pos):
    "Parse a parameter definition: [$0], {$x}, {$1!}..."
    for (opening, closing) in ParameterDefinition.parambrackets:
      if pos.checkskip(opening):
        if opening == '[':
          self.optional = True
        if not pos.checkskip('$'):
          Trace.error('Wrong parameter name, did you mean $' + pos.current() + '?')
          return None
        self.name = pos.skipcurrent()
        if pos.checkskip('!'):
          self.literal = True
        if not pos.checkskip(closing):
          Trace.error('Wrong parameter closing ' + pos.skipcurrent())
          return None
        return self
    Trace.error('Wrong character in parameter template: ' + pos.skipcurrent())
    return None

  def read(self, pos, function):
    "Read the parameter itself using the definition."
    if self.literal:
      if self.optional:
        self.literalvalue = function.parsesquareliteral(pos)
      else:
        self.literalvalue = function.parseliteral(pos)
      if self.literalvalue:
        self.value = FormulaConstant(self.literalvalue)
    elif self.optional:
      self.value = function.parsesquare(pos)
    else:
      self.value = function.parseparameter(pos)

  def __unicode__(self):
    "Return a printable representation."
    result = 'param ' + self.name
    if self.value:
      result += ': ' + str(self.value)
    else:
      result += ' (empty)'
    return result

class ParameterFunction(CommandBit):
  "A function with a variable number of parameters defined in a template."
  "The parameters are defined as a parameter definition."

  def readparams(self, readtemplate, pos):
    "Read the params according to the template."
    self.params = dict()
    for paramdef in self.paramdefs(readtemplate):
      paramdef.read(pos, self)
      self.params['$' + paramdef.name] = paramdef

  def paramdefs(self, readtemplate):
    "Read each param definition in the template"
    pos = TextPosition(readtemplate)
    while not pos.finished():
      paramdef = ParameterDefinition().parse(pos)
      if paramdef:
        yield paramdef

  def getparam(self, name):
    "Get a parameter as parsed."
    if not name in self.params:
      return None
    return self.params[name]

  def getvalue(self, name):
    "Get the value of a parameter."
    return self.getparam(name).value

  def getliteralvalue(self, name):
    "Get the literal value of a parameter."
    param = self.getparam(name)
    if not param or not param.literalvalue:
      return None
    return param.literalvalue

class HybridFunction(ParameterFunction):
  """
  A parameter function where the output is also defined using a template.
  The template can use a number of functions; each function has an associated
  tag.
  Example: [f0{$1},span class="fbox"] defines a function f0 which corresponds
  to a span of class fbox, yielding <span class="fbox">$1</span>.
  Literal parameters can be used in tags definitions:
    [f0{$1},span style="color: $p;"]
  yields <span style="color: $p;">$1</span>, where $p is a literal parameter.
  Sizes can be specified in hybridsizes, e.g. adding parameter sizes. By
  default the resulting size is the max of all arguments. Sizes are used
  to generate the right parameters.
  A function followed by a single / is output as a self-closing XHTML tag:
    [f0/,hr]
  will generate <hr/>.
  """

  commandmap = FormulaConfig.hybridfunctions

  def parsebit(self, pos):
    "Parse a function with [] and {} parameters"
    readtemplate = self.translated[0]
    writetemplate = self.translated[1]
    self.readparams(readtemplate, pos)
    self.contents = self.writeparams(writetemplate)
    self.computehybridsize()

  def writeparams(self, writetemplate):
    "Write all params according to the template"
    return self.writepos(TextPosition(writetemplate))

  def writepos(self, pos):
    "Write all params as read in the parse position."
    result = []
    while not pos.finished():
      if pos.checkskip('$'):
        param = self.writeparam(pos)
        if param:
          result.append(param)
      elif pos.checkskip('f'):
        function = self.writefunction(pos)
        if function:
          function.type = None
          result.append(function)
      elif pos.checkskip('('):
        result.append(self.writebracket('left', '('))
      elif pos.checkskip(')'):
        result.append(self.writebracket('right', ')'))
      else:
        result.append(FormulaConstant(pos.skipcurrent()))
    return result

  def writeparam(self, pos):
    "Write a single param of the form $0, $x..."
    name = '$' + pos.skipcurrent()
    if not name in self.params:
      Trace.error('Unknown parameter ' + name)
      return None
    if not self.params[name]:
      return None
    if pos.checkskip('.'):
      self.params[name].value.type = pos.globalpha()
    return self.params[name].value

  def writefunction(self, pos):
    "Write a single function f0,...,fn."
    tag = self.readtag(pos)
    if not tag:
      return None
    if pos.checkskip('/'):
      # self-closing XHTML tag, such as <hr/>
      return TaggedBit().selfcomplete(tag)
    if not pos.checkskip('{'):
      Trace.error('Function should be defined in {}')
      return None
    pos.pushending('}')
    contents = self.writepos(pos)
    pos.popending()
    if len(contents) == 0:
      return None
    return TaggedBit().complete(contents, tag)

  def readtag(self, pos):
    "Get the tag corresponding to the given index. Does parameter substitution."
    if not pos.current().isdigit():
      Trace.error('Function should be f0,...,f9: f' + pos.current())
      return None
    index = int(pos.skipcurrent())
    if 2 + index > len(self.translated):
      Trace.error('Function f' + str(index) + ' is not defined')
      return None
    tag = self.translated[2 + index]
    if not '$' in tag:
      return tag
    for variable in self.params:
      if variable in tag:
        param = self.params[variable]
        if not param.literal:
          Trace.error('Parameters in tag ' + tag + ' should be literal: {' + variable + '!}')
          continue
        if param.literalvalue:
          value = param.literalvalue
        else:
          value = ''
        tag = tag.replace(variable, value)
    return tag

  def writebracket(self, direction, character):
    "Return a new bracket looking at the given direction."
    return self.factory.create(BracketCommand).create(direction, character)
  
  def computehybridsize(self):
    "Compute the size of the hybrid function."
    if not self.command in HybridSize.configsizes:
      self.computesize()
      return
    self.size = HybridSize().getsize(self)
    # set the size in all elements at first level
    for element in self.contents:
      element.size = self.size

class HybridSize(object):
  "The size associated with a hybrid function."

  configsizes = FormulaConfig.hybridsizes

  def getsize(self, function):
    "Read the size for a function and parse it."
    sizestring = self.configsizes[function.command]
    for name in function.params:
      if name in sizestring:
        size = function.params[name].value.computesize()
        sizestring = sizestring.replace(name, str(size))
    if '$' in sizestring:
      Trace.error('Unconverted variable in hybrid size: ' + sizestring)
      return 1
    return eval(sizestring)


FormulaCommand.types += [HybridFunction]









class HeaderParser(Parser):
  "Parses the LyX header"

  def parse(self, reader):
    "Parse header parameters into a dictionary, return the preamble."
    contents = []
    self.parseending(reader, lambda: self.parseline(reader, contents))
    # skip last line
    reader.nextline()
    return contents

  def parseline(self, reader, contents):
    "Parse a single line as a parameter or as a start"
    line = reader.currentline()
    if line.startswith(HeaderConfig.parameters['branch']):
      self.parsebranch(reader)
      return
    elif line.startswith(HeaderConfig.parameters['lstset']):
      LstParser().parselstset(reader)
      return
    elif line.startswith(HeaderConfig.parameters['beginpreamble']):
      contents.append(self.factory.createcontainer(reader))
      return
    # no match
    self.parseparameter(reader)

  def parsebranch(self, reader):
    "Parse all branch definitions."
    branch = reader.currentline().split()[1]
    reader.nextline()
    subparser = HeaderParser().complete(HeaderConfig.parameters['endbranch'])
    subparser.parse(reader)
    options = BranchOptions(branch)
    for key in subparser.parameters:
      options.set(key, subparser.parameters[key])
    Options.branches[branch] = options

  def complete(self, ending):
    "Complete the parser with the given ending."
    self.ending = ending
    return self

class PreambleParser(Parser):
  "A parser for the LyX preamble."

  preamble = []

  def parse(self, reader):
    "Parse the full preamble with all statements."
    self.ending = HeaderConfig.parameters['endpreamble']
    self.parseending(reader, lambda: self.parsepreambleline(reader))
    return []

  def parsepreambleline(self, reader):
    "Parse a single preamble line."
    PreambleParser.preamble.append(reader.currentline())
    reader.nextline()

class LstParser(object):
  "Parse global and local lstparams."

  globalparams = dict()

  def parselstset(self, reader):
    "Parse a declaration of lstparams in lstset."
    paramtext = self.extractlstset(reader)
    if not '{' in paramtext:
      Trace.error('Missing opening bracket in lstset: ' + paramtext)
      return
    lefttext = paramtext.split('{')[1]
    croppedtext = lefttext[:-1]
    LstParser.globalparams = self.parselstparams(croppedtext)

  def extractlstset(self, reader):
    "Extract the global lstset parameters."
    paramtext = ''
    while not reader.finished():
      paramtext += reader.currentline()
      reader.nextline()
      if paramtext.endswith('}'):
        return paramtext
    Trace.error('Could not find end of \\lstset settings; aborting')

  def parsecontainer(self, container):
    "Parse some lstparams from elyxer.a container."
    container.lstparams = LstParser.globalparams.copy()
    paramlist = container.getparameterlist('lstparams')
    container.lstparams.update(self.parselstparams(paramlist))

  def parselstparams(self, paramlist):
    "Process a number of lstparams from elyxer.a list."
    paramdict = dict()
    for param in paramlist:
      if not '=' in param:
        if len(param.strip()) > 0:
          Trace.error('Invalid listing parameter ' + param)
      else:
        key, value = param.split('=', 1)
        paramdict[key] = value
    return paramdict




class MacroDefinition(CommandBit):
  "A function that defines a new command (a macro)."

  macros = dict()

  def parsebit(self, pos):
    "Parse the function that defines the macro."
    self.output = EmptyOutput()
    self.parameternumber = 0
    self.defaults = []
    self.factory.defining = True
    self.parseparameters(pos)
    self.factory.defining = False
    Trace.debug('New command ' + self.newcommand + ' (' + \
        str(self.parameternumber) + ' parameters)')
    self.macros[self.newcommand] = self

  def parseparameters(self, pos):
    "Parse all optional parameters (number of parameters, default values)"
    "and the mandatory definition."
    self.newcommand = self.parsenewcommand(pos)
    # parse number of parameters
    literal = self.parsesquareliteral(pos)
    if literal:
      self.parameternumber = int(literal)
    # parse all default values
    bracket = self.parsesquare(pos)
    while bracket:
      self.defaults.append(bracket)
      bracket = self.parsesquare(pos)
    # parse mandatory definition
    self.definition = self.parseparameter(pos)

  def parsenewcommand(self, pos):
    "Parse the name of the new command."
    self.factory.clearskipped(pos)
    if self.factory.detecttype(Bracket, pos):
      return self.parseliteral(pos)
    if self.factory.detecttype(FormulaCommand, pos):
      return self.factory.create(FormulaCommand).extractcommand(pos)
    Trace.error('Unknown formula bit in defining function at ' + pos.identifier())
    return 'unknown'

  def instantiate(self):
    "Return an instance of the macro."
    return self.definition.clone()

class MacroParameter(FormulaBit):
  "A parameter from elyxer.a macro."

  def detect(self, pos):
    "Find a macro parameter: #n."
    return pos.checkfor('#')

  def parsebit(self, pos):
    "Parse the parameter: #n."
    if not pos.checkskip('#'):
      Trace.error('Missing parameter start #.')
      return
    self.number = int(pos.skipcurrent())
    self.original = '#' + str(self.number)
    self.contents = [TaggedBit().constant('#' + str(self.number), 'span class="unknown"')]

class MacroFunction(CommandBit):
  "A function that was defined using a macro."

  commandmap = MacroDefinition.macros

  def parsebit(self, pos):
    "Parse a number of input parameters."
    self.output = FilteredOutput()
    self.values = []
    macro = self.translated
    self.parseparameters(pos, macro)
    self.completemacro(macro)

  def parseparameters(self, pos, macro):
    "Parse as many parameters as are needed."
    self.parseoptional(pos, list(macro.defaults))
    self.parsemandatory(pos, macro.parameternumber - len(macro.defaults))
    if len(self.values) < macro.parameternumber:
      Trace.error('Missing parameters in macro ' + str(self))

  def parseoptional(self, pos, defaults):
    "Parse optional parameters."
    optional = []
    while self.factory.detecttype(SquareBracket, pos):
      optional.append(self.parsesquare(pos))
      if len(optional) > len(defaults):
        break
    for value in optional:
      default = defaults.pop()
      if len(value.contents) > 0:
        self.values.append(value)
      else:
        self.values.append(default)
    self.values += defaults

  def parsemandatory(self, pos, number):
    "Parse a number of mandatory parameters."
    for index in range(number):
      parameter = self.parsemacroparameter(pos, number - index)
      if not parameter:
        return
      self.values.append(parameter)

  def parsemacroparameter(self, pos, remaining):
    "Parse a macro parameter. Could be a bracket or a single letter."
    "If there are just two values remaining and there is a running number,"
    "parse as two separater numbers."
    self.factory.clearskipped(pos)
    if pos.finished():
      return None
    if self.factory.detecttype(FormulaNumber, pos):
      return self.parsenumbers(pos, remaining)
    return self.parseparameter(pos)

  def parsenumbers(self, pos, remaining):
    "Parse the remaining parameters as a running number."
    "For example, 12 would be {1}{2}."
    number = self.factory.parsetype(FormulaNumber, pos)
    if not len(number.original) == remaining:
      return number
    for digit in number.original:
      value = self.factory.create(FormulaNumber)
      value.add(FormulaConstant(digit))
      value.type = number
      self.values.append(value)
    return None

  def completemacro(self, macro):
    "Complete the macro with the parameters read."
    self.contents = [macro.instantiate()]
    replaced = [False] * len(self.values)
    for parameter in self.searchall(MacroParameter):
      index = parameter.number - 1
      if index >= len(self.values):
        Trace.error('Macro parameter index out of bounds: ' + str(index))
        return
      replaced[index] = True
      parameter.contents = [self.values[index].clone()]
    for index in range(len(self.values)):
      if not replaced[index]:
        self.addfilter(index, self.values[index])

  def addfilter(self, index, value):
    "Add a filter for the given parameter number and parameter value."
    original = '#' + str(index + 1)
    value = ''.join(self.values[0].gethtml())
    self.output.addfilter(original, value)

class FormulaMacro(Formula):
  "A math macro defined in an inset."

  def __init__(self):
    self.parser = MacroParser()
    self.output = EmptyOutput()

  def __unicode__(self):
    "Return a printable representation."
    return 'Math macro'

FormulaFactory.types += [ MacroParameter ]

FormulaCommand.types += [
    MacroFunction,
    ]



def math2html(formula):
  "Convert some TeX math to HTML."
  factory = FormulaFactory()
  whole = factory.parseformula(formula)
  FormulaProcessor().process(whole)
  whole.process()
  return ''.join(whole.gethtml())

def main():
  "Main function, called if invoked from elyxer.the command line"
  args = sys.argv
  Options().parseoptions(args)
  if len(args) != 1:
    Trace.error('Usage: math2html.py escaped_string')
    exit()
  result = math2html(args[0])
  Trace.message(result)

if __name__ == '__main__':
  main()

