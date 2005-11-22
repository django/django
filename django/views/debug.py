import re
import os
import sys
import inspect
from django.conf import settings
from os.path import dirname, join as pathjoin
from django.core.template import Template, Context
from django.utils.httpwrappers import HttpResponseServerError, HttpResponseNotFound
from itertools import count, izip
from django.utils.html import escape

HIDDEN_SETTINGS = re.compile('SECRET|PASSWORD')

def linebreak_iter(template_source):
        import re
        newline_re = re.compile("^", re.M)
        for match in newline_re.finditer(template_source):
            yield match.start()
        yield len(template_source) + 1

def get_template_exception_info(exc_type,exc_value,tb):
    origin, (start, end) = exc_value.source
    template_source = origin.reload()
    context_lines = 10
    line = 0
    upto = 0
    source_lines = []
    linebreaks = izip(count(0), linebreak_iter(template_source))
    linebreaks.next() # skip the nothing before initial line start
    for num, next in linebreaks:
        if start >= upto and end <= next :
            line = num
            before = escape(template_source[upto:start])
            during = escape(template_source[start:end])
            after = escape(template_source[end:next - 1])
        
        source_lines.append( (num, escape(template_source[upto:next - 1])) )
        upto = next
        
    total = len(source_lines)
    
    top = max(0, line - context_lines)
    bottom = min(total, line + 1 + context_lines)
    
    template_info =  {
                   'message'      : exc_value.args[0], 
                   'source_lines' : source_lines[top:bottom],
                   'before' : before, 
                   'during': during,
                   'after': after,
                   'top': top ,
                   'bottom': bottom ,
                   'total' : total,
                   'line'  : line,
                   'name' : origin.name,
                }
    exc_info = hasattr(exc_value, 'exc_info') and exc_value.exc_info or (exc_type,exc_value,tb)
    return exc_info + (template_info,)

def technical_500_response(request, exc_type, exc_value, tb):
    """
    Create a technical server error response.  The last three arguments are
    the values returned from sys.exc_info() and friends.
    """
    template_info = None
    if settings.TEMPLATE_DEBUG and hasattr(exc_value, 'source'):
        exc_type, exc_value, tb, template_info = get_template_exception_info(exc_type,exc_value,tb)
    frames = []
    while tb is not None:
        filename = tb.tb_frame.f_code.co_filename
        function = tb.tb_frame.f_code.co_name
        lineno = tb.tb_lineno - 1
        pre_context_lineno, pre_context, context_line, post_context = _get_lines_from_file(filename, lineno, 7)
        frames.append({
            'tb' : tb,
            'filename' : filename,
            'function' : function,
            'lineno' : lineno,
            'vars' : tb.tb_frame.f_locals.items(),
            'id' : id(tb),
            'pre_context' : pre_context,
            'context_line' : context_line,
            'post_context' : post_context,
            'pre_context_lineno' : pre_context_lineno,
        })
        tb = tb.tb_next

    # Turn the settings module into a dict, filtering out anything that
    # matches HIDDEN_SETTINGS along the way.
    settings_dict = {}
    for k in dir(settings):
        if k.isupper():
            if HIDDEN_SETTINGS.search(k):
                settings_dict[k] = '********************'
            else:
                settings_dict[k] = getattr(settings, k)

    t = Template(TECHNICAL_500_TEMPLATE)
    c = Context({
        'exception_type' : exc_type.__name__,
        'exception_value' : exc_value,
        'frames' : frames,
        'lastframe' : frames[-1],
        'request' : request,
        'request_protocol' : os.environ.get("HTTPS") == "on" and "https" or "http",
        'settings' : settings_dict,
        'template_info': template_info,
    })
    return HttpResponseServerError(t.render(c), mimetype='text/html')

def technical_404_response(request, exception):
    """
    Create a technical 404 error response.  The exception should be the Http404
    exception.
    """
    try:
        tried = exception.args[0]['tried']
    except (IndexError, TypeError):
        tried = []

    t = Template(TECHNICAL_404_TEMPLATE)
    c = Context({
        'root_urlconf' : settings.ROOT_URLCONF,
        'urlpatterns' : tried,
        'reason' : str(exception),
        'request' : request,
        'request_protocol' : os.environ.get("HTTPS") == "on" and "https" or "http",
        'settings' : dict([(k, getattr(settings, k)) for k in dir(settings) if k.isupper()]),
    })
    return HttpResponseNotFound(t.render(c), mimetype='text/html')

def _get_lines_from_file(filename, lineno, context_lines):
    """
    Returns context_lines before and after lineno from file.
    Returns (pre_context_lineno, pre_context, context_line, post_context).
    """
    try:
        source = open(filename).readlines()
        lower_bound = max(0, lineno - context_lines)
        upper_bound = lineno + context_lines

        pre_context = [line.strip('\n') for line in source[lower_bound:lineno]]
        context_line = source[lineno].strip('\n')
        post_context = [line.strip('\n') for line in source[lineno+1:upper_bound]]

        return lower_bound, pre_context, context_line, post_context
    except (OSError, IOError):
        return None, [], None, []

#
# Templates are embedded in the file so that we know the error handler will
# always work even if the template loader is broken.
#

TECHNICAL_500_TEMPLATE = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <meta name="robots" content="NONE,NOARCHIVE" />
  <title>{{ exception_type }} at {{ request.path }}</title>
  <style type="text/css">
    html * { padding:0; margin:0; }
    body * { padding:10px 20px; }
    body * * { padding:0; }
    body { font:small sans-serif; }
    body>div { border-bottom:1px solid #ddd; }
    h1 { font-weight:normal; }
    h2 { margin-bottom:.8em; }
    h2 span { font-size:80%; color:#666; font-weight:normal; }
    h3 { margin:1em 0 .5em 0; }
    h4 { margin:0 0 .5em 0; font-weight: normal; }
    table { border:1px solid #ccc; border-collapse: collapse; width:100%; background:white; }
    tbody td, tbody th { vertical-align:top; padding:2px 3px; }
    thead th { padding:1px 6px 1px 3px; background:#fefefe; text-align:left; font-weight:normal; font-size:11px; border:1px solid #ddd; }
    tbody th { width:12em; text-align:right; color:#666; padding-right:.5em; }
    table.vars { margin:5px 0 2px 40px; }
    table.vars td, table.req td { font-family:monospace; }
    table td.code { width:100%; }
    table td.code div { overflow:hidden; }
    ul.traceback { list-style-type:none; }
    ul.traceback li.frame { margin-bottom:1em; }
    div.context { margin: 10px 0; }
    div.context ol { padding-left:30px; margin:0 10px; list-style-position: inside; }
    div.context ol li { font-family:monospace; white-space:pre; color:#666; cursor:pointer; }
    div.context ol.context-line li { color:black; background-color:#ccc; }
    div.context ol.context-line li span { float: right; }
    div.commands { margin-left: 40px; }
    div.commands a { color:black; text-decoration:none; }
    #summary { background: #ffc; }
    #summary h2 { font-weight: normal; color: #666; }
    #explanation { background:#eee; }
    #traceback { background:#eee; }
    #requestinfo { background:#f6f6f6; padding-left:120px; }
    #summary table { border:none; background:transparent; }
    #requestinfo h2, #requestinfo h3 { position:relative; margin-left:-100px; }
    #requestinfo h3 { margin-bottom:-1em; }
    table.source td{ font-family: monospace; white-space: pre;}
    span.specific{background:#ffcab7;}
    .error { background:#ffc; }
  </style>
  <script type="text/javascript">
  //<!--
    function getElementsByClassName(oElm, strTagName, strClassName){
        // Written by Jonathan Snook, http://www.snook.ca/jon; Add-ons by Robert Nyman, http://www.robertnyman.com
        var arrElements = (strTagName == "*" && document.all)? document.all :
        oElm.getElementsByTagName(strTagName);
        var arrReturnElements = new Array();
        strClassName = strClassName.replace(/\-/g, "\\-");
        var oRegExp = new RegExp("(^|\\s)" + strClassName + "(\\s|$)");
        var oElement;
        for(var i=0; i<arrElements.length; i++){
            oElement = arrElements[i];
            if(oRegExp.test(oElement.className)){
                arrReturnElements.push(oElement);
            }
        }
        return (arrReturnElements)
    }
    function hideAll(elems) {
      for (var e = 0; e < elems.length; e++) {
        elems[e].style.display = 'none';
      }
    }
    window.onload = function() {
      hideAll(getElementsByClassName(document, 'table', 'vars'));
      hideAll(getElementsByClassName(document, 'ol', 'pre-context'));
      hideAll(getElementsByClassName(document, 'ol', 'post-context'));
    }
    function toggle() {
      for (var i = 0; i < arguments.length; i++) {
        var e = document.getElementById(arguments[i]);
        if (e) {
          e.style.display = e.style.display == 'none' ? 'block' : 'none';
        }
      }
      return false;
    }
    function varToggle(link, id) {
      toggle('v' + id);
      var s = link.getElementsByTagName('span')[0];
      var uarr = String.fromCharCode(0x25b6);
      var darr = String.fromCharCode(0x25bc);
      s.innerHTML = s.innerHTML == uarr ? darr : uarr;
      return false;
    }
    //-->
  </script>
</head>
<body>

<div id="summary">
  <h1>{{ exception_type }} at {{ request.path }}</h1>
  <h2>{{ exception_value }}</h2>
  <table class="meta">
    <tr>
      <th>Request Method:</th>
      <td>{{ request.META.REQUEST_METHOD }}</td>
    </tr>
    <tr>
      <th>Request URL:</th>
      <td>{{ request_protocol }}://{{ request.META.HTTP_HOST }}{{ request.path }}</td>
    </tr>
    <tr>
      <th>Exception Type:</th>
      <td>{{ exception_type }}</td>
    </tr>
    <tr>
      <th>Exception Value:</th>
      <td>{{ exception_value }}</td>
    </tr>
    <tr>
      <th>Exception Location:</th>
      <td>{{ lastframe.filename }} in {{ lastframe.function }}, line {{ lastframe.lineno }}</td>
    </tr>
  </table>
</div>
{%if template_info %}
<div id="template">
   <h2>Template</h2>
   In template {{template_info.name}}, error at line {{template_info.line}}
   <div>{{template_info.message|escape}}</div>
   <table class="source{%if template_info.top%} cut-top{%endif%}{%ifnotequal template_info.bottom template_info.total%} cut-bottom{%endifnotequal%}">
   {% for source_line in template_info.source_lines %}
   {%ifequal source_line.0 template_info.line %}
       <tr class="error"><td>{{source_line.0}}</td>
       <td> {{template_info.before}}<span class="specific">{{template_info.during}}</span>{{template_info.after}}</td></tr>
   {%else%}
      <tr><td>{{source_line.0}}</td>
      <td> {{source_line.1}}</td></tr>
   {%endifequal%}
   {%endfor%}
   </table>
</div>
{%endif%}
<div id="traceback">
  <h2>Traceback <span>(innermost last)</span></h2>
  <ul class="traceback">
    {% for frame in frames %}
      <li class="frame">
        <code>{{ frame.filename }}</code> in <code>{{ frame.function }}</code>

        {% if frame.context_line %}
          <div class="context" id="c{{ frame.id }}">
            {% if frame.pre_context %}
              <ol start="{{ frame.pre_context_lineno }}" class="pre-context" id="pre{{ frame.id }}">{% for line in frame.pre_context %}<li onclick="toggle('pre{{ frame.id }}', 'post{{ frame.id }}')">{{ line|escape }}</li>{% endfor %}</ol>
            {% endif %}
            <ol start="{{ frame.lineno }}" class="context-line"><li onclick="toggle('pre{{ frame.id }}', 'post{{ frame.id }}')">{{ frame.context_line|escape }} <span>...</span></li></ol>
            {% if frame.post_context %}
              <ol start='{{ frame.lineno|add:"1" }}' class="post-context" id="post{{ frame.id }}">{% for line in frame.post_context %}<li onclick="toggle('pre{{ frame.id }}', 'post{{ frame.id }}')">{{ line|escape }}</li>{% endfor %}</ol>
            {% endif %}
          </div>
        {% endif %}

        {% if frame.vars %}
          <div class="commands">
              <a href="#" onclick="return varToggle(this, '{{ frame.id }}')"><span>&#x25b6;</span> Local vars</a>
          </div>
          <table class="vars" id="v{{ frame.id }}">
            <thead>
              <tr>
                <th>Variable</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {% for var in frame.vars|dictsort:"0" %}
                <tr>
                  <td>{{ var.0 }}</td>
                  <td class="code"><div>{{ var.1|pprint|escape }}</div></td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        {% endif %}
      </li>
    {% endfor %}
  </ul>
</div>

<div id="requestinfo">
  <h2>Request information</h2>

  <h3 id="get-info">GET</h3>
  {% if request.GET %}
    <table class="req">
      <thead>
        <tr>
          <th>Variable</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {% for var in request.GET.items %}
          <tr>
            <td>{{ var.0 }}</td>
            <td class="code"><div>{{ var.1|pprint|escape }}</div></td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>No GET data</p>
  {% endif %}

  <h3 id="post-info">POST</h3>
  {% if request.POST %}
    <table class="req">
      <thead>
        <tr>
          <th>Variable</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {% for var in request.POST.items %}
          <tr>
            <td>{{ var.0 }}</td>
            <td class="code"><div>{{ var.1|pprint|escape }}</div></td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>No POST data</p>
  {% endif %}

  <h3 id="cookie-info">COOKIES</h3>
  {% if request.COOKIES %}
    <table class="req">
      <thead>
        <tr>
          <th>Variable</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {% for var in request.COOKIES.items %}
          <tr>
            <td>{{ var.0 }}</td>
            <td class="code"><div>{{ var.1|pprint|escape }}</div></td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p>No cookie data</p>
  {% endif %}

  <h3 id="meta-info">META</h3>
  <table class="req">
    <thead>
      <tr>
        <th>Variable</th>
        <th>Value</th>
      </tr>
    </thead>
    <tbody>
      {% for var in request.META.items|dictsort:"0" %}
        <tr>
          <td>{{ var.0 }}</td>
          <td class="code"><div>{{ var.1|pprint|escape }}</div></td>
        </tr>
      {% endfor %}
    </tbody>
  </table>

  <h3 id="settings-info">Settings</h3>
  <h4>Using settings module <code>{{ settings.SETTINGS_MODULE }}</code></h4>
  <table class="req">
    <thead>
      <tr>
        <th>Setting</th>
        <th>Value</th>
      </tr>
    </thead>
    <tbody>
      {% for var in settings.items|dictsort:"0" %}
        <tr>
          <td>{{ var.0 }}</td>
          <td class="code"><div>{{ var.1|pprint|escape }}</div></td>
        </tr>
      {% endfor %}
    </tbody>
  </table>

</div>

<div id="explanation">
  <p>
    You're seeing this error because you have <code>DEBUG = True</code> in your
    Django settings file. Change that to <code>False</code>, and Django will
    display a standard 500 page.
  </p>
</div>

</body>
</html>
"""

TECHNICAL_404_TEMPLATE = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en">
<head>
  <meta http-equiv="content-type" content="text/html; charset=utf-8" />
  <title>Page not found at {{ request.path }}</title>
  <meta name="robots" content="NONE,NOARCHIVE" />
  <style type="text/css">
    html * { padding:0; margin:0; }
    body * { padding:10px 20px; }
    body * * { padding:0; }
    body { font:small sans-serif; background:#eee; }
    body>div { border-bottom:1px solid #ddd; }
    h1 { font-weight:normal; margin-bottom:.4em; }
    h1 span { font-size:60%; color:#666; font-weight:normal; }
    table { border:none; border-collapse: collapse; width:100%; }
    td, th { vertical-align:top; padding:2px 3px; }
    th { width:12em; text-align:right; color:#666; padding-right:.5em; }
    #info { background:#f6f6f6; }
    #info ol { margin: 0.5em 4em; }
    #info ol li { font-family: monospace; }
    #summary { background: #ffc; }
    #explanation { background:#eee; border-bottom: 0px none; }
  </style>
</head>
<body>
  <div id="summary">
    <h1>Page not found <span>(404)</span></h1>
    <table class="meta">
      <tr>
        <th>Request Method:</th>
        <td>{{ request.META.REQUEST_METHOD }}</td>
      </tr>
      <tr>
        <th>Request URL:</th>
      <td>{{ request_protocol }}://{{ request.META.HTTP_HOST }}{{ request.path }}</td>
      </tr>
    </table>
  </div>
  <div id="info">
    {% if urlpatterns %}
      <p>
        Using the URLconf defined in <code>{{ settings.ROOT_URLCONF }}</code>,
        Django tried these URL patterns, in this order:
      </p>
      <ol>
        {% for pattern in urlpatterns %}
          <li>{{ pattern|escape }}</li>
        {% endfor %}
      </ol>
      <p>The current URL, <code>{{ request.path }}</code>, didn't match any of these.</p>
    {% else %}
      <p>{{ reason|escape }}</p>
    {% endif %}
  </div>

  <div id="explanation">
    <p>
      You're seeing this error because you have <code>DEBUG = True</code> in
      your Django settings file. Change that to <code>False</code>, and Django
      will display a standard 404 page.
    </p>
  </div>
</body>
</html>
"""