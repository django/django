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

__all__ = ('Packages', 'Modules', 'Excluded', 'Errors')

class SingletonType(type):
    def __call__(cls, *args, **kwargs):
        if getattr(cls, '__instance__', None) is None:
            instance = cls.__new__(cls)
            instance.__init__(*args, **kwargs)
            cls.__instance__ = instance
        return cls.__instance__

class Packages(object):
    __metaclass__ = SingletonType
    packages = {}

class Modules(object):
    __metaclass__ = SingletonType
    modules = {}

class Excluded(object):
    __metaclass__ = SingletonType
    excluded = []

class Errors(object):
    __metaclass__ = SingletonType
    errors = []

