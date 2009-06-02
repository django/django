"""
Copyright 2009 55 Minutes (http://www.55minutes.com)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

TOP = """\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
  <head>
    <meta http-equiv="Content-type" content="text/html;charset=UTF-8" />
    <title>Test coverage report: %(title)s</title>
    <style type="text/css" media="screen">
      a
      {
        color: #3d707a;
      }
      
      a:hover, a:active
      {
        color: #bf7d18;
      }
    
      body 
      {
        font-family: "Lucida Sans Unicode", "Lucida Grande", sans-serif;
        font-size: 13px;
      }
      
      .nav 
      {
        font-size: 12px;
        margin-left: 50px;
      }

      .ignored
      {
        color: #707070;
      }

      .executed 
      {
        color: #3d9900;
      }

      .missed 
      {
        color: red;
        font-weight: bold;
      }

      .excluded 
      {
        color: #6090f0;
        font-weight: lighter;
      }
    
      #content-header 
      {
        font-size: 12px;
        padding: 18px 0 18px 50px;
      }

      #content-header h1 
      {
        font-size: 16px;
        margin: 10px 0 0 0;
        color: #909090;
      }
      
      #module-name
      {
        color: #583707;
      }
    
      #content-header p
      {
        font-size: 13px;
        margin: 0;
        color: #909090;
      }

      #content-header .normal 
      {
        color: #609030;
      }

      #content-header .warning 
      {
        color: #d0a000;
      }

      #content-header .critical 
      {
        color: red;
      }
      
      #source-listing 
      {
        margin-bottom: 24px;
      }

      #source-listing ol 
      {
        padding: 0 0 0 50px;
        width: 90%%;
        font-family: monospace;
        list-style-position: outside;
      }

      #source-listing ol li 
      {
        line-height: 18px;
        font-size: small;
      }
        
      #source-listing ol code 
      {
        padding:  0 .001em 0 0; /* Firefox doesn't render empty li's properly */
        font-size: medium;
        white-space: pre;
      }
   </style>
  </head>

  <body>
"""

NAV = """\
<div class="nav">
  <a href="%(prev_link)s">%(prev_label)s</a> &lt;&lt;
  <a href="%(up_link)s">%(up_label)s</a>
  &gt;&gt; <a href="%(next_link)s">%(next_label)s</a>
</div>
"""

NAV_NO_PREV = """\
<div class="nav">
  <a href="%(up_link)s">%(up_label)s</a>
  &gt;&gt; <a href="%(next_link)s">%(next_label)s</a>
</div>
"""

NAV_NO_NEXT = """\
<div class="nav">
  <a href="%(prev_link)s">%(prev_label)s</a> &lt;&lt;
  <a href="%(up_link)s">%(up_label)s</a>
</div>
"""

CONTENT_HEADER = """\
<div id="content-header">
  <h1>
    <span id="module-name">%(title)s</span>:
    %(total_count)d total statements,
    <span class="%(severity)s">%(percent_covered)0.1f%% covered</span>
  </h1>
  <p>Generated: %(test_timestamp)s</p>
  <p>Source file: %(source_file)s</p>
  <p>
    Stats:
    <span class="executed">%(executed_count)d executed</span>,
    <span class="missed">%(missed_count)d missed</span>,
    <span class="excluded">%(excluded_count)d excluded</span>,
    <span class="ignored">%(ignored_count)d ignored</span> 
  </p> 
</div>
"""

CONTENT_BODY = """\
<div id="source-listing">
  <ol>
    %(source_lines)s
  </ol>
</div>
"""

SOURCE_LINE = '<li class="%(line_status)s"><code>%(source_line)s</code></li>'

BOTTOM = """\
  </body>
</html>
"""
