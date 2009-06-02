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

import os

def html_module_exceptions(filename, exceptions, template, long_desc):
    exception_list = []
    exceptions.sort()
    for module_name in exceptions:
        exception_list.append(template.EXCEPTION_LINE %vars())
    exception_list = os.linesep.join(exception_list)

    fo = file(filename, 'wb+')
    print >>fo, template.TOP
    print >>fo, template.CONTENT_HEADER
    print >>fo, template.CONTENT_BODY %vars()
    print >>fo, template.BOTTOM
    fo.close()

