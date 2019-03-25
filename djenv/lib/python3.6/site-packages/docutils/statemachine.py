 # $Id: statemachine.py 7464 2012-06-25 13:16:03Z milde $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

"""
A finite state machine specialized for regular-expression-based text filters,
this module defines the following classes:

- `StateMachine`, a state machine
- `State`, a state superclass
- `StateMachineWS`, a whitespace-sensitive version of `StateMachine`
- `StateWS`, a state superclass for use with `StateMachineWS`
- `SearchStateMachine`, uses `re.search()` instead of `re.match()`
- `SearchStateMachineWS`, uses `re.search()` instead of `re.match()`
- `ViewList`, extends standard Python lists.
- `StringList`, string-specific ViewList.

Exception classes:

- `StateMachineError`
- `UnknownStateError`
- `DuplicateStateError`
- `UnknownTransitionError`
- `DuplicateTransitionError`
- `TransitionPatternNotFound`
- `TransitionMethodNotFound`
- `UnexpectedIndentationError`
- `TransitionCorrection`: Raised to switch to another transition.
- `StateCorrection`: Raised to switch to another state & transition.

Functions:

- `string2lines()`: split a multi-line string into a list of one-line strings


How To Use This Module
======================
(See the individual classes, methods, and attributes for details.)

1. Import it: ``import statemachine`` or ``from statemachine import ...``.
   You will also need to ``import re``.

2. Derive a subclass of `State` (or `StateWS`) for each state in your state
   machine::

       class MyState(statemachine.State):

   Within the state's class definition:

   a) Include a pattern for each transition, in `State.patterns`::

          patterns = {'atransition': r'pattern', ...}

   b) Include a list of initial transitions to be set up automatically, in
      `State.initial_transitions`::

          initial_transitions = ['atransition', ...]

   c) Define a method for each transition, with the same name as the
      transition pattern::

          def atransition(self, match, context, next_state):
              # do something
              result = [...]  # a list
              return context, next_state, result
              # context, next_state may be altered

      Transition methods may raise an `EOFError` to cut processing short.

   d) You may wish to override the `State.bof()` and/or `State.eof()` implicit
      transition methods, which handle the beginning- and end-of-file.

   e) In order to handle nested processing, you may wish to override the
      attributes `State.nested_sm` and/or `State.nested_sm_kwargs`.

      If you are using `StateWS` as a base class, in order to handle nested
      indented blocks, you may wish to:

      - override the attributes `StateWS.indent_sm`,
        `StateWS.indent_sm_kwargs`, `StateWS.known_indent_sm`, and/or
        `StateWS.known_indent_sm_kwargs`;
      - override the `StateWS.blank()` method; and/or
      - override or extend the `StateWS.indent()`, `StateWS.known_indent()`,
        and/or `StateWS.firstknown_indent()` methods.

3. Create a state machine object::

       sm = StateMachine(state_classes=[MyState, ...],
                         initial_state='MyState')

4. Obtain the input text, which needs to be converted into a tab-free list of
   one-line strings. For example, to read text from a file called
   'inputfile'::

       input_string = open('inputfile').read()
       input_lines = statemachine.string2lines(input_string)

5. Run the state machine on the input text and collect the results, a list::

       results = sm.run(input_lines)

6. Remove any lingering circular references::

       sm.unlink()
"""

__docformat__ = 'restructuredtext'

import sys
import re
import types
import unicodedata
from docutils import utils
from docutils.utils.error_reporting import ErrorOutput


class StateMachine:

    """
    A finite state machine for text filters using regular expressions.

    The input is provided in the form of a list of one-line strings (no
    newlines). States are subclasses of the `State` class. Transitions consist
    of regular expression patterns and transition methods, and are defined in
    each state.

    The state machine is started with the `run()` method, which returns the
    results of processing in a list.
    """

    def __init__(self, state_classes, initial_state, debug=False):
        """
        Initialize a `StateMachine` object; add state objects.

        Parameters:

        - `state_classes`: a list of `State` (sub)classes.
        - `initial_state`: a string, the class name of the initial state.
        - `debug`: a boolean; produce verbose output if true (nonzero).
        """

        self.input_lines = None
        """`StringList` of input lines (without newlines).
        Filled by `self.run()`."""

        self.input_offset = 0
        """Offset of `self.input_lines` from the beginning of the file."""

        self.line = None
        """Current input line."""

        self.line_offset = -1
        """Current input line offset from beginning of `self.input_lines`."""

        self.debug = debug
        """Debugging mode on/off."""

        self.initial_state = initial_state
        """The name of the initial state (key to `self.states`)."""

        self.current_state = initial_state
        """The name of the current state (key to `self.states`)."""

        self.states = {}
        """Mapping of {state_name: State_object}."""

        self.add_states(state_classes)

        self.observers = []
        """List of bound methods or functions to call whenever the current
        line changes.  Observers are called with one argument, ``self``.
        Cleared at the end of `run()`."""

        self._stderr = ErrorOutput()
        """Wrapper around sys.stderr catching en-/decoding errors"""


    def unlink(self):
        """Remove circular references to objects no longer required."""
        for state in list(self.states.values()):
            state.unlink()
        self.states = None

    def run(self, input_lines, input_offset=0, context=None,
            input_source=None, initial_state=None):
        """
        Run the state machine on `input_lines`. Return results (a list).

        Reset `self.line_offset` and `self.current_state`. Run the
        beginning-of-file transition. Input one line at a time and check for a
        matching transition. If a match is found, call the transition method
        and possibly change the state. Store the context returned by the
        transition method to be passed on to the next transition matched.
        Accumulate the results returned by the transition methods in a list.
        Run the end-of-file transition. Finally, return the accumulated
        results.

        Parameters:

        - `input_lines`: a list of strings without newlines, or `StringList`.
        - `input_offset`: the line offset of `input_lines` from the beginning
          of the file.
        - `context`: application-specific storage.
        - `input_source`: name or path of source of `input_lines`.
        - `initial_state`: name of initial state.
        """
        self.runtime_init()
        if isinstance(input_lines, StringList):
            self.input_lines = input_lines
        else:
            self.input_lines = StringList(input_lines, source=input_source)
        self.input_offset = input_offset
        self.line_offset = -1
        self.current_state = initial_state or self.initial_state
        if self.debug:
            print((
                '\nStateMachine.run: input_lines (line_offset=%s):\n| %s'
                % (self.line_offset, '\n| '.join(self.input_lines))), file=self._stderr)
        transitions = None
        results = []
        state = self.get_state()
        try:
            if self.debug:
                print('\nStateMachine.run: bof transition', file=self._stderr)
            context, result = state.bof(context)
            results.extend(result)
            while True:
                try:
                    try:
                        self.next_line()
                        if self.debug:
                            source, offset = self.input_lines.info(
                                self.line_offset)
                            print((
                                '\nStateMachine.run: line (source=%r, '
                                'offset=%r):\n| %s'
                                % (source, offset, self.line)), file=self._stderr)
                        context, next_state, result = self.check_line(
                            context, state, transitions)
                    except EOFError:
                        if self.debug:
                            print((
                                '\nStateMachine.run: %s.eof transition'
                                % state.__class__.__name__), file=self._stderr)
                        result = state.eof(context)
                        results.extend(result)
                        break
                    else:
                        results.extend(result)
                except TransitionCorrection as exception:
                    self.previous_line() # back up for another try
                    transitions = (exception.args[0],)
                    if self.debug:
                        print((
                              '\nStateMachine.run: TransitionCorrection to '
                              'state "%s", transition %s.'
                              % (state.__class__.__name__, transitions[0])), file=self._stderr)
                    continue
                except StateCorrection as exception:
                    self.previous_line() # back up for another try
                    next_state = exception.args[0]
                    if len(exception.args) == 1:
                        transitions = None
                    else:
                        transitions = (exception.args[1],)
                    if self.debug:
                        print((
                              '\nStateMachine.run: StateCorrection to state '
                              '"%s", transition %s.'
                              % (next_state, transitions[0])), file=self._stderr)
                else:
                    transitions = None
                state = self.get_state(next_state)
        except:
            if self.debug:
                self.error()
            raise
        self.observers = []
        return results

    def get_state(self, next_state=None):
        """
        Return current state object; set it first if `next_state` given.

        Parameter `next_state`: a string, the name of the next state.

        Exception: `UnknownStateError` raised if `next_state` unknown.
        """
        if next_state:
            if self.debug and next_state != self.current_state:
                print((
                    '\nStateMachine.get_state: Changing state from '
                    '"%s" to "%s" (input line %s).'
                    % (self.current_state, next_state,
                       self.abs_line_number())), file=self._stderr)
            self.current_state = next_state
        try:
            return self.states[self.current_state]
        except KeyError:
            raise UnknownStateError(self.current_state)

    def next_line(self, n=1):
        """Load `self.line` with the `n`'th next line and return it."""
        try:
            try:
                self.line_offset += n
                self.line = self.input_lines[self.line_offset]
            except IndexError:
                self.line = None
                raise EOFError
            return self.line
        finally:
            self.notify_observers()

    def is_next_line_blank(self):
        """Return 1 if the next line is blank or non-existant."""
        try:
            return not self.input_lines[self.line_offset + 1].strip()
        except IndexError:
            return 1

    def at_eof(self):
        """Return 1 if the input is at or past end-of-file."""
        return self.line_offset >= len(self.input_lines) - 1

    def at_bof(self):
        """Return 1 if the input is at or before beginning-of-file."""
        return self.line_offset <= 0

    def previous_line(self, n=1):
        """Load `self.line` with the `n`'th previous line and return it."""
        self.line_offset -= n
        if self.line_offset < 0:
            self.line = None
        else:
            self.line = self.input_lines[self.line_offset]
        self.notify_observers()
        return self.line

    def goto_line(self, line_offset):
        """Jump to absolute line offset `line_offset`, load and return it."""
        try:
            try:
                self.line_offset = line_offset - self.input_offset
                self.line = self.input_lines[self.line_offset]
            except IndexError:
                self.line = None
                raise EOFError
            return self.line
        finally:
            self.notify_observers()

    def get_source(self, line_offset):
        """Return source of line at absolute line offset `line_offset`."""
        return self.input_lines.source(line_offset - self.input_offset)

    def abs_line_offset(self):
        """Return line offset of current line, from beginning of file."""
        return self.line_offset + self.input_offset

    def abs_line_number(self):
        """Return line number of current line (counting from 1)."""
        return self.line_offset + self.input_offset + 1

    def get_source_and_line(self, lineno=None):
        """Return (source, line) tuple for current or given line number.

        Looks up the source and line number in the `self.input_lines`
        StringList instance to count for included source files.

        If the optional argument `lineno` is given, convert it from an
        absolute line number to the corresponding (source, line) pair.
        """
        if lineno is None:
            offset = self.line_offset
        else:
            offset = lineno - self.input_offset - 1
        try:
            src, srcoffset = self.input_lines.info(offset)
            srcline = srcoffset + 1
        except (TypeError):
            # line is None if index is "Just past the end"
            src, srcline = self.get_source_and_line(offset + self.input_offset)
            return src, srcline + 1
        except (IndexError): # `offset` is off the list
            src, srcline = None, None
            # raise AssertionError('cannot find line %d in %s lines' %
            #                      (offset, len(self.input_lines)))
            #                      # list(self.input_lines.lines())))
        # assert offset == srcoffset, str(self.input_lines)
        # print "get_source_and_line(%s):" % lineno,
        # print offset + 1, '->', src, srcline
        # print self.input_lines
        return (src, srcline)

    def insert_input(self, input_lines, source):
        self.input_lines.insert(self.line_offset + 1, '',
                                source='internal padding after '+source,
                                offset=len(input_lines))
        self.input_lines.insert(self.line_offset + 1, '',
                                source='internal padding before '+source,
                                offset=-1)
        self.input_lines.insert(self.line_offset + 2,
                                StringList(input_lines, source))

    def get_text_block(self, flush_left=False):
        """
        Return a contiguous block of text.

        If `flush_left` is true, raise `UnexpectedIndentationError` if an
        indented line is encountered before the text block ends (with a blank
        line).
        """
        try:
            block = self.input_lines.get_text_block(self.line_offset,
                                                    flush_left)
            self.next_line(len(block) - 1)
            return block
        except UnexpectedIndentationError as err:
            block = err.args[0]
            self.next_line(len(block) - 1) # advance to last line of block
            raise

    def check_line(self, context, state, transitions=None):
        """
        Examine one line of input for a transition match & execute its method.

        Parameters:

        - `context`: application-dependent storage.
        - `state`: a `State` object, the current state.
        - `transitions`: an optional ordered list of transition names to try,
          instead of ``state.transition_order``.

        Return the values returned by the transition method:

        - context: possibly modified from the parameter `context`;
        - next state name (`State` subclass name);
        - the result output of the transition, a list.

        When there is no match, ``state.no_match()`` is called and its return
        value is returned.
        """
        if transitions is None:
            transitions =  state.transition_order
        state_correction = None
        if self.debug:
            print((
                  '\nStateMachine.check_line: state="%s", transitions=%r.'
                  % (state.__class__.__name__, transitions)), file=self._stderr)
        for name in transitions:
            pattern, method, next_state = state.transitions[name]
            match = pattern.match(self.line)
            if match:
                if self.debug:
                    print((
                          '\nStateMachine.check_line: Matched transition '
                          '"%s" in state "%s".'
                          % (name, state.__class__.__name__)), file=self._stderr)
                return method(match, context, next_state)
        else:
            if self.debug:
                print((
                      '\nStateMachine.check_line: No match in state "%s".'
                      % state.__class__.__name__), file=self._stderr)
            return state.no_match(context, transitions)

    def add_state(self, state_class):
        """
        Initialize & add a `state_class` (`State` subclass) object.

        Exception: `DuplicateStateError` raised if `state_class` was already
        added.
        """
        statename = state_class.__name__
        if statename in self.states:
            raise DuplicateStateError(statename)
        self.states[statename] = state_class(self, self.debug)

    def add_states(self, state_classes):
        """
        Add `state_classes` (a list of `State` subclasses).
        """
        for state_class in state_classes:
            self.add_state(state_class)

    def runtime_init(self):
        """
        Initialize `self.states`.
        """
        for state in list(self.states.values()):
            state.runtime_init()

    def error(self):
        """Report error details."""
        type, value, module, line, function = _exception_data()
        print('%s: %s' % (type, value), file=self._stderr)
        print('input line %s' % (self.abs_line_number()), file=self._stderr)
        print(('module %s, line %s, function %s' %
                               (module, line, function)), file=self._stderr)

    def attach_observer(self, observer):
        """
        The `observer` parameter is a function or bound method which takes two
        arguments, the source and offset of the current line.
        """
        self.observers.append(observer)

    def detach_observer(self, observer):
        self.observers.remove(observer)

    def notify_observers(self):
        for observer in self.observers:
            try:
                info = self.input_lines.info(self.line_offset)
            except IndexError:
                info = (None, None)
            observer(*info)


class State:

    """
    State superclass. Contains a list of transitions, and transition methods.

    Transition methods all have the same signature. They take 3 parameters:

    - An `re` match object. ``match.string`` contains the matched input line,
      ``match.start()`` gives the start index of the match, and
      ``match.end()`` gives the end index.
    - A context object, whose meaning is application-defined (initial value
      ``None``). It can be used to store any information required by the state
      machine, and the retured context is passed on to the next transition
      method unchanged.
    - The name of the next state, a string, taken from the transitions list;
      normally it is returned unchanged, but it may be altered by the
      transition method if necessary.

    Transition methods all return a 3-tuple:

    - A context object, as (potentially) modified by the transition method.
    - The next state name (a return value of ``None`` means no state change).
    - The processing result, a list, which is accumulated by the state
      machine.

    Transition methods may raise an `EOFError` to cut processing short.

    There are two implicit transitions, and corresponding transition methods
    are defined: `bof()` handles the beginning-of-file, and `eof()` handles
    the end-of-file. These methods have non-standard signatures and return
    values. `bof()` returns the initial context and results, and may be used
    to return a header string, or do any other processing needed. `eof()`
    should handle any remaining context and wrap things up; it returns the
    final processing result.

    Typical applications need only subclass `State` (or a subclass), set the
    `patterns` and `initial_transitions` class attributes, and provide
    corresponding transition methods. The default object initialization will
    take care of constructing the list of transitions.
    """

    patterns = None
    """
    {Name: pattern} mapping, used by `make_transition()`. Each pattern may
    be a string or a compiled `re` pattern. Override in subclasses.
    """

    initial_transitions = None
    """
    A list of transitions to initialize when a `State` is instantiated.
    Each entry is either a transition name string, or a (transition name, next
    state name) pair. See `make_transitions()`. Override in subclasses.
    """

    nested_sm = None
    """
    The `StateMachine` class for handling nested processing.

    If left as ``None``, `nested_sm` defaults to the class of the state's
    controlling state machine. Override it in subclasses to avoid the default.
    """

    nested_sm_kwargs = None
    """
    Keyword arguments dictionary, passed to the `nested_sm` constructor.

    Two keys must have entries in the dictionary:

    - Key 'state_classes' must be set to a list of `State` classes.
    - Key 'initial_state' must be set to the name of the initial state class.

    If `nested_sm_kwargs` is left as ``None``, 'state_classes' defaults to the
    class of the current state, and 'initial_state' defaults to the name of
    the class of the current state. Override in subclasses to avoid the
    defaults.
    """

    def __init__(self, state_machine, debug=False):
        """
        Initialize a `State` object; make & add initial transitions.

        Parameters:

        - `statemachine`: the controlling `StateMachine` object.
        - `debug`: a boolean; produce verbose output if true.
        """

        self.transition_order = []
        """A list of transition names in search order."""

        self.transitions = {}
        """
        A mapping of transition names to 3-tuples containing
        (compiled_pattern, transition_method, next_state_name). Initialized as
        an instance attribute dynamically (instead of as a class attribute)
        because it may make forward references to patterns and methods in this
        or other classes.
        """

        self.add_initial_transitions()

        self.state_machine = state_machine
        """A reference to the controlling `StateMachine` object."""

        self.debug = debug
        """Debugging mode on/off."""

        if self.nested_sm is None:
            self.nested_sm = self.state_machine.__class__
        if self.nested_sm_kwargs is None:
            self.nested_sm_kwargs = {'state_classes': [self.__class__],
                                     'initial_state': self.__class__.__name__}

    def runtime_init(self):
        """
        Initialize this `State` before running the state machine; called from
        `self.state_machine.run()`.
        """
        pass

    def unlink(self):
        """Remove circular references to objects no longer required."""
        self.state_machine = None

    def add_initial_transitions(self):
        """Make and add transitions listed in `self.initial_transitions`."""
        if self.initial_transitions:
            names, transitions = self.make_transitions(
                  self.initial_transitions)
            self.add_transitions(names, transitions)

    def add_transitions(self, names, transitions):
        """
        Add a list of transitions to the start of the transition list.

        Parameters:

        - `names`: a list of transition names.
        - `transitions`: a mapping of names to transition tuples.

        Exceptions: `DuplicateTransitionError`, `UnknownTransitionError`.
        """
        for name in names:
            if name in self.transitions:
                raise DuplicateTransitionError(name)
            if name not in transitions:
                raise UnknownTransitionError(name)
        self.transition_order[:0] = names
        self.transitions.update(transitions)

    def add_transition(self, name, transition):
        """
        Add a transition to the start of the transition list.

        Parameter `transition`: a ready-made transition 3-tuple.

        Exception: `DuplicateTransitionError`.
        """
        if name in self.transitions:
            raise DuplicateTransitionError(name)
        self.transition_order[:0] = [name]
        self.transitions[name] = transition

    def remove_transition(self, name):
        """
        Remove a transition by `name`.

        Exception: `UnknownTransitionError`.
        """
        try:
            del self.transitions[name]
            self.transition_order.remove(name)
        except:
            raise UnknownTransitionError(name)

    def make_transition(self, name, next_state=None):
        """
        Make & return a transition tuple based on `name`.

        This is a convenience function to simplify transition creation.

        Parameters:

        - `name`: a string, the name of the transition pattern & method. This
          `State` object must have a method called '`name`', and a dictionary
          `self.patterns` containing a key '`name`'.
        - `next_state`: a string, the name of the next `State` object for this
          transition. A value of ``None`` (or absent) implies no state change
          (i.e., continue with the same state).

        Exceptions: `TransitionPatternNotFound`, `TransitionMethodNotFound`.
        """
        if next_state is None:
            next_state = self.__class__.__name__
        try:
            pattern = self.patterns[name]
            if not hasattr(pattern, 'match'):
                pattern = re.compile(pattern)
        except KeyError:
            raise TransitionPatternNotFound(
                  '%s.patterns[%r]' % (self.__class__.__name__, name))
        try:
            method = getattr(self, name)
        except AttributeError:
            raise TransitionMethodNotFound(
                  '%s.%s' % (self.__class__.__name__, name))
        return (pattern, method, next_state)

    def make_transitions(self, name_list):
        """
        Return a list of transition names and a transition mapping.

        Parameter `name_list`: a list, where each entry is either a transition
        name string, or a 1- or 2-tuple (transition name, optional next state
        name).
        """
        stringtype = type('')
        names = []
        transitions = {}
        for namestate in name_list:
            if type(namestate) is stringtype:
                transitions[namestate] = self.make_transition(namestate)
                names.append(namestate)
            else:
                transitions[namestate[0]] = self.make_transition(*namestate)
                names.append(namestate[0])
        return names, transitions

    def no_match(self, context, transitions):
        """
        Called when there is no match from `StateMachine.check_line()`.

        Return the same values returned by transition methods:

        - context: unchanged;
        - next state name: ``None``;
        - empty result list.

        Override in subclasses to catch this event.
        """
        return context, None, []

    def bof(self, context):
        """
        Handle beginning-of-file. Return unchanged `context`, empty result.

        Override in subclasses.

        Parameter `context`: application-defined storage.
        """
        return context, []

    def eof(self, context):
        """
        Handle end-of-file. Return empty result.

        Override in subclasses.

        Parameter `context`: application-defined storage.
        """
        return []

    def nop(self, match, context, next_state):
        """
        A "do nothing" transition method.

        Return unchanged `context` & `next_state`, empty result. Useful for
        simple state changes (actionless transitions).
        """
        return context, next_state, []


class StateMachineWS(StateMachine):

    """
    `StateMachine` subclass specialized for whitespace recognition.

    There are three methods provided for extracting indented text blocks:

    - `get_indented()`: use when the indent is unknown.
    - `get_known_indented()`: use when the indent is known for all lines.
    - `get_first_known_indented()`: use when only the first line's indent is
      known.
    """

    def get_indented(self, until_blank=False, strip_indent=True):
        """
        Return a block of indented lines of text, and info.

        Extract an indented block where the indent is unknown for all lines.

        :Parameters:
            - `until_blank`: Stop collecting at the first blank line if true.
            - `strip_indent`: Strip common leading indent if true (default).

        :Return:
            - the indented block (a list of lines of text),
            - its indent,
            - its first line offset from BOF, and
            - whether or not it finished with a blank line.
        """
        offset = self.abs_line_offset()
        indented, indent, blank_finish = self.input_lines.get_indented(
              self.line_offset, until_blank, strip_indent)
        if indented:
            self.next_line(len(indented) - 1) # advance to last indented line
        while indented and not indented[0].strip():
            indented.trim_start()
            offset += 1
        return indented, indent, offset, blank_finish

    def get_known_indented(self, indent, until_blank=False, strip_indent=True):
        """
        Return an indented block and info.

        Extract an indented block where the indent is known for all lines.
        Starting with the current line, extract the entire text block with at
        least `indent` indentation (which must be whitespace, except for the
        first line).

        :Parameters:
            - `indent`: The number of indent columns/characters.
            - `until_blank`: Stop collecting at the first blank line if true.
            - `strip_indent`: Strip `indent` characters of indentation if true
              (default).

        :Return:
            - the indented block,
            - its first line offset from BOF, and
            - whether or not it finished with a blank line.
        """
        offset = self.abs_line_offset()
        indented, indent, blank_finish = self.input_lines.get_indented(
              self.line_offset, until_blank, strip_indent,
              block_indent=indent)
        self.next_line(len(indented) - 1) # advance to last indented line
        while indented and not indented[0].strip():
            indented.trim_start()
            offset += 1
        return indented, offset, blank_finish

    def get_first_known_indented(self, indent, until_blank=False, 
                                 strip_indent=True, strip_top=True):
        """
        Return an indented block and info.

        Extract an indented block where the indent is known for the first line
        and unknown for all other lines.

        :Parameters:
            - `indent`: The first line's indent (# of columns/characters).
            - `until_blank`: Stop collecting at the first blank line if true
              (1).
            - `strip_indent`: Strip `indent` characters of indentation if true
              (1, default).
            - `strip_top`: Strip blank lines from the beginning of the block.

        :Return:
            - the indented block,
            - its indent,
            - its first line offset from BOF, and
            - whether or not it finished with a blank line.
        """
        offset = self.abs_line_offset()
        indented, indent, blank_finish = self.input_lines.get_indented(
              self.line_offset, until_blank, strip_indent,
              first_indent=indent)
        self.next_line(len(indented) - 1) # advance to last indented line
        if strip_top:
            while indented and not indented[0].strip():
                indented.trim_start()
                offset += 1
        return indented, indent, offset, blank_finish


class StateWS(State):

    """
    State superclass specialized for whitespace (blank lines & indents).

    Use this class with `StateMachineWS`.  The transitions 'blank' (for blank
    lines) and 'indent' (for indented text blocks) are added automatically,
    before any other transitions.  The transition method `blank()` handles
    blank lines and `indent()` handles nested indented blocks.  Indented
    blocks trigger a new state machine to be created by `indent()` and run.
    The class of the state machine to be created is in `indent_sm`, and the
    constructor keyword arguments are in the dictionary `indent_sm_kwargs`.

    The methods `known_indent()` and `firstknown_indent()` are provided for
    indented blocks where the indent (all lines' and first line's only,
    respectively) is known to the transition method, along with the attributes
    `known_indent_sm` and `known_indent_sm_kwargs`.  Neither transition method
    is triggered automatically.
    """

    indent_sm = None
    """
    The `StateMachine` class handling indented text blocks.

    If left as ``None``, `indent_sm` defaults to the value of
    `State.nested_sm`.  Override it in subclasses to avoid the default.
    """

    indent_sm_kwargs = None
    """
    Keyword arguments dictionary, passed to the `indent_sm` constructor.

    If left as ``None``, `indent_sm_kwargs` defaults to the value of
    `State.nested_sm_kwargs`. Override it in subclasses to avoid the default.
    """

    known_indent_sm = None
    """
    The `StateMachine` class handling known-indented text blocks.

    If left as ``None``, `known_indent_sm` defaults to the value of
    `indent_sm`.  Override it in subclasses to avoid the default.
    """

    known_indent_sm_kwargs = None
    """
    Keyword arguments dictionary, passed to the `known_indent_sm` constructor.

    If left as ``None``, `known_indent_sm_kwargs` defaults to the value of
    `indent_sm_kwargs`. Override it in subclasses to avoid the default.
    """

    ws_patterns = {'blank': ' *$',
                   'indent': ' +'}
    """Patterns for default whitespace transitions.  May be overridden in
    subclasses."""

    ws_initial_transitions = ('blank', 'indent')
    """Default initial whitespace transitions, added before those listed in
    `State.initial_transitions`.  May be overridden in subclasses."""

    def __init__(self, state_machine, debug=False):
        """
        Initialize a `StateSM` object; extends `State.__init__()`.

        Check for indent state machine attributes, set defaults if not set.
        """
        State.__init__(self, state_machine, debug)
        if self.indent_sm is None:
            self.indent_sm = self.nested_sm
        if self.indent_sm_kwargs is None:
            self.indent_sm_kwargs = self.nested_sm_kwargs
        if self.known_indent_sm is None:
            self.known_indent_sm = self.indent_sm
        if self.known_indent_sm_kwargs is None:
            self.known_indent_sm_kwargs = self.indent_sm_kwargs

    def add_initial_transitions(self):
        """
        Add whitespace-specific transitions before those defined in subclass.

        Extends `State.add_initial_transitions()`.
        """
        State.add_initial_transitions(self)
        if self.patterns is None:
            self.patterns = {}
        self.patterns.update(self.ws_patterns)
        names, transitions = self.make_transitions(
            self.ws_initial_transitions)
        self.add_transitions(names, transitions)

    def blank(self, match, context, next_state):
        """Handle blank lines. Does nothing. Override in subclasses."""
        return self.nop(match, context, next_state)

    def indent(self, match, context, next_state):
        """
        Handle an indented text block. Extend or override in subclasses.

        Recursively run the registered state machine for indented blocks
        (`self.indent_sm`).
        """
        indented, indent, line_offset, blank_finish = \
              self.state_machine.get_indented()
        sm = self.indent_sm(debug=self.debug, **self.indent_sm_kwargs)
        results = sm.run(indented, input_offset=line_offset)
        return context, next_state, results

    def known_indent(self, match, context, next_state):
        """
        Handle a known-indent text block. Extend or override in subclasses.

        Recursively run the registered state machine for known-indent indented
        blocks (`self.known_indent_sm`). The indent is the length of the
        match, ``match.end()``.
        """
        indented, line_offset, blank_finish = \
              self.state_machine.get_known_indented(match.end())
        sm = self.known_indent_sm(debug=self.debug,
                                 **self.known_indent_sm_kwargs)
        results = sm.run(indented, input_offset=line_offset)
        return context, next_state, results

    def first_known_indent(self, match, context, next_state):
        """
        Handle an indented text block (first line's indent known).

        Extend or override in subclasses.

        Recursively run the registered state machine for known-indent indented
        blocks (`self.known_indent_sm`). The indent is the length of the
        match, ``match.end()``.
        """
        indented, line_offset, blank_finish = \
              self.state_machine.get_first_known_indented(match.end())
        sm = self.known_indent_sm(debug=self.debug,
                                 **self.known_indent_sm_kwargs)
        results = sm.run(indented, input_offset=line_offset)
        return context, next_state, results


class _SearchOverride:

    """
    Mix-in class to override `StateMachine` regular expression behavior.

    Changes regular expression matching, from the default `re.match()`
    (succeeds only if the pattern matches at the start of `self.line`) to
    `re.search()` (succeeds if the pattern matches anywhere in `self.line`).
    When subclassing a `StateMachine`, list this class **first** in the
    inheritance list of the class definition.
    """

    def match(self, pattern):
        """
        Return the result of a regular expression search.

        Overrides `StateMachine.match()`.

        Parameter `pattern`: `re` compiled regular expression.
        """
        return pattern.search(self.line)


class SearchStateMachine(_SearchOverride, StateMachine):
    """`StateMachine` which uses `re.search()` instead of `re.match()`."""
    pass


class SearchStateMachineWS(_SearchOverride, StateMachineWS):
    """`StateMachineWS` which uses `re.search()` instead of `re.match()`."""
    pass


class ViewList:

    """
    List with extended functionality: slices of ViewList objects are child
    lists, linked to their parents. Changes made to a child list also affect
    the parent list.  A child list is effectively a "view" (in the SQL sense)
    of the parent list.  Changes to parent lists, however, do *not* affect
    active child lists.  If a parent list is changed, any active child lists
    should be recreated.

    The start and end of the slice can be trimmed using the `trim_start()` and
    `trim_end()` methods, without affecting the parent list.  The link between
    child and parent lists can be broken by calling `disconnect()` on the
    child list.

    Also, ViewList objects keep track of the source & offset of each item.
    This information is accessible via the `source()`, `offset()`, and
    `info()` methods.
    """

    def __init__(self, initlist=None, source=None, items=None,
                 parent=None, parent_offset=None):
        self.data = []
        """The actual list of data, flattened from various sources."""

        self.items = []
        """A list of (source, offset) pairs, same length as `self.data`: the
        source of each line and the offset of each line from the beginning of
        its source."""

        self.parent = parent
        """The parent list."""

        self.parent_offset = parent_offset
        """Offset of this list from the beginning of the parent list."""

        if isinstance(initlist, ViewList):
            self.data = initlist.data[:]
            self.items = initlist.items[:]
        elif initlist is not None:
            self.data = list(initlist)
            if items:
                self.items = items
            else:
                self.items = [(source, i) for i in range(len(initlist))]
        assert len(self.data) == len(self.items), 'data mismatch'

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return '%s(%s, items=%s)' % (self.__class__.__name__,
                                     self.data, self.items)

    def __lt__(self, other): return self.data <  self.__cast(other)
    def __le__(self, other): return self.data <= self.__cast(other)
    def __eq__(self, other): return self.data == self.__cast(other)
    def __ne__(self, other): return self.data != self.__cast(other)
    def __gt__(self, other): return self.data >  self.__cast(other)
    def __ge__(self, other): return self.data >= self.__cast(other)
    def __cmp__(self, other): return cmp(self.data, self.__cast(other))

    def __cast(self, other):
        if isinstance(other, ViewList):
            return other.data
        else:
            return other

    def __contains__(self, item): return item in self.data
    def __len__(self): return len(self.data)

    # The __getitem__()/__setitem__() methods check whether the index
    # is a slice first, since indexing a native list with a slice object
    # just works.

    def __getitem__(self, i):
        if isinstance(i, slice):
            assert i.step in (None, 1),  'cannot handle slice with stride'
            return self.__class__(self.data[i.start:i.stop],
                                  items=self.items[i.start:i.stop],
                                  parent=self, parent_offset=i.start or 0)
        else:
            return self.data[i]

    def __setitem__(self, i, item):
        if isinstance(i, slice):
            assert i.step in (None, 1), 'cannot handle slice with stride'
            if not isinstance(item, ViewList):
                raise TypeError('assigning non-ViewList to ViewList slice')
            self.data[i.start:i.stop] = item.data
            self.items[i.start:i.stop] = item.items
            assert len(self.data) == len(self.items), 'data mismatch'
            if self.parent:
                self.parent[(i.start or 0) + self.parent_offset
                            : (i.stop or len(self)) + self.parent_offset] = item
        else:
            self.data[i] = item
            if self.parent:
                self.parent[i + self.parent_offset] = item

    def __delitem__(self, i):
        try:
            del self.data[i]
            del self.items[i]
            if self.parent:
                del self.parent[i + self.parent_offset]
        except TypeError:
            assert i.step is None, 'cannot handle slice with stride'
            del self.data[i.start:i.stop]
            del self.items[i.start:i.stop]
            if self.parent:
                del self.parent[(i.start or 0) + self.parent_offset
                                : (i.stop or len(self)) + self.parent_offset]

    def __add__(self, other):
        if isinstance(other, ViewList):
            return self.__class__(self.data + other.data,
                                  items=(self.items + other.items))
        else:
            raise TypeError('adding non-ViewList to a ViewList')

    def __radd__(self, other):
        if isinstance(other, ViewList):
            return self.__class__(other.data + self.data,
                                  items=(other.items + self.items))
        else:
            raise TypeError('adding ViewList to a non-ViewList')

    def __iadd__(self, other):
        if isinstance(other, ViewList):
            self.data += other.data
        else:
            raise TypeError('argument to += must be a ViewList')
        return self

    def __mul__(self, n):
        return self.__class__(self.data * n, items=(self.items * n))

    __rmul__ = __mul__

    def __imul__(self, n):
        self.data *= n
        self.items *= n
        return self

    def extend(self, other):
        if not isinstance(other, ViewList):
            raise TypeError('extending a ViewList with a non-ViewList')
        if self.parent:
            self.parent.insert(len(self.data) + self.parent_offset, other)
        self.data.extend(other.data)
        self.items.extend(other.items)

    def append(self, item, source=None, offset=0):
        if source is None:
            self.extend(item)
        else:
            if self.parent:
                self.parent.insert(len(self.data) + self.parent_offset, item,
                                   source, offset)
            self.data.append(item)
            self.items.append((source, offset))

    def insert(self, i, item, source=None, offset=0):
        if source is None:
            if not isinstance(item, ViewList):
                raise TypeError('inserting non-ViewList with no source given')
            self.data[i:i] = item.data
            self.items[i:i] = item.items
            if self.parent:
                index = (len(self.data) + i) % len(self.data)
                self.parent.insert(index + self.parent_offset, item)
        else:
            self.data.insert(i, item)
            self.items.insert(i, (source, offset))
            if self.parent:
                index = (len(self.data) + i) % len(self.data)
                self.parent.insert(index + self.parent_offset, item,
                                   source, offset)

    def pop(self, i=-1):
        if self.parent:
            index = (len(self.data) + i) % len(self.data)
            self.parent.pop(index + self.parent_offset)
        self.items.pop(i)
        return self.data.pop(i)

    def trim_start(self, n=1):
        """
        Remove items from the start of the list, without touching the parent.
        """
        if n > len(self.data):
            raise IndexError("Size of trim too large; can't trim %s items "
                             "from a list of size %s." % (n, len(self.data)))
        elif n < 0:
            raise IndexError('Trim size must be >= 0.')
        del self.data[:n]
        del self.items[:n]
        if self.parent:
            self.parent_offset += n

    def trim_end(self, n=1):
        """
        Remove items from the end of the list, without touching the parent.
        """
        if n > len(self.data):
            raise IndexError("Size of trim too large; can't trim %s items "
                             "from a list of size %s." % (n, len(self.data)))
        elif n < 0:
            raise IndexError('Trim size must be >= 0.')
        del self.data[-n:]
        del self.items[-n:]

    def remove(self, item):
        index = self.index(item)
        del self[index]

    def count(self, item): return self.data.count(item)
    def index(self, item): return self.data.index(item)

    def reverse(self):
        self.data.reverse()
        self.items.reverse()
        self.parent = None

    def sort(self, *args):
        tmp = list(zip(self.data, self.items))
        tmp.sort(*args)
        self.data = [entry[0] for entry in tmp]
        self.items = [entry[1] for entry in tmp]
        self.parent = None

    def info(self, i):
        """Return source & offset for index `i`."""
        try:
            return self.items[i]
        except IndexError:
            if i == len(self.data):     # Just past the end
                return self.items[i - 1][0], None
            else:
                raise

    def source(self, i):
        """Return source for index `i`."""
        return self.info(i)[0]

    def offset(self, i):
        """Return offset for index `i`."""
        return self.info(i)[1]

    def disconnect(self):
        """Break link between this list and parent list."""
        self.parent = None

    def xitems(self):
        """Return iterator yielding (source, offset, value) tuples."""
        for (value, (source, offset)) in zip(self.data, self.items):
            yield (source, offset, value)

    def pprint(self):
        """Print the list in `grep` format (`source:offset:value` lines)"""
        for line in self.xitems():
            print("%s:%d:%s" % line)


class StringList(ViewList):

    """A `ViewList` with string-specific methods."""

    def trim_left(self, length, start=0, end=sys.maxsize):
        """
        Trim `length` characters off the beginning of each item, in-place,
        from index `start` to `end`.  No whitespace-checking is done on the
        trimmed text.  Does not affect slice parent.
        """
        self.data[start:end] = [line[length:]
                                for line in self.data[start:end]]

    def get_text_block(self, start, flush_left=False):
        """
        Return a contiguous block of text.

        If `flush_left` is true, raise `UnexpectedIndentationError` if an
        indented line is encountered before the text block ends (with a blank
        line).
        """
        end = start
        last = len(self.data)
        while end < last:
            line = self.data[end]
            if not line.strip():
                break
            if flush_left and (line[0] == ' '):
                source, offset = self.info(end)
                raise UnexpectedIndentationError(self[start:end], source,
                                                 offset + 1)
            end += 1
        return self[start:end]

    def get_indented(self, start=0, until_blank=False, strip_indent=True,
                     block_indent=None, first_indent=None):
        """
        Extract and return a StringList of indented lines of text.

        Collect all lines with indentation, determine the minimum indentation,
        remove the minimum indentation from all indented lines (unless
        `strip_indent` is false), and return them. All lines up to but not
        including the first unindented line will be returned.

        :Parameters:
          - `start`: The index of the first line to examine.
          - `until_blank`: Stop collecting at the first blank line if true.
          - `strip_indent`: Strip common leading indent if true (default).
          - `block_indent`: The indent of the entire block, if known.
          - `first_indent`: The indent of the first line, if known.

        :Return:
          - a StringList of indented lines with mininum indent removed;
          - the amount of the indent;
          - a boolean: did the indented block finish with a blank line or EOF?
        """
        indent = block_indent           # start with None if unknown
        end = start
        if block_indent is not None and first_indent is None:
            first_indent = block_indent
        if first_indent is not None:
            end += 1
        last = len(self.data)
        while end < last:
            line = self.data[end]
            if line and (line[0] != ' '
                         or (block_indent is not None
                             and line[:block_indent].strip())):
                # Line not indented or insufficiently indented.
                # Block finished properly iff the last indented line blank:
                blank_finish = ((end > start)
                                and not self.data[end - 1].strip())
                break
            stripped = line.lstrip()
            if not stripped:            # blank line
                if until_blank:
                    blank_finish = 1
                    break
            elif block_indent is None:
                line_indent = len(line) - len(stripped)
                if indent is None:
                    indent = line_indent
                else:
                    indent = min(indent, line_indent)
            end += 1
        else:
            blank_finish = 1            # block ends at end of lines
        block = self[start:end]
        if first_indent is not None and block:
            block.data[0] = block.data[0][first_indent:]
        if indent and strip_indent:
            block.trim_left(indent, start=(first_indent is not None))
        return block, indent or 0, blank_finish

    def get_2D_block(self, top, left, bottom, right, strip_indent=True):
        block = self[top:bottom]
        indent = right
        for i in range(len(block.data)):
            # get slice from line, care for combining characters
            ci = utils.column_indices(block.data[i])
            try:
                left = ci[left]
            except IndexError:
                left += len(block.data[i]) - len(ci)
            try:
                right = ci[right]
            except IndexError:
                right += len(block.data[i]) - len(ci)
            block.data[i] = line = block.data[i][left:right].rstrip()
            if line:
                indent = min(indent, len(line) - len(line.lstrip()))
        if strip_indent and 0 < indent < right:
            block.data = [line[indent:] for line in block.data]
        return block

    def pad_double_width(self, pad_char):
        """
        Pad all double-width characters in self by appending `pad_char` to each.
        For East Asian language support.
        """
        if hasattr(unicodedata, 'east_asian_width'):
            east_asian_width = unicodedata.east_asian_width
        else:
            return                      # new in Python 2.4
        for i in range(len(self.data)):
            line = self.data[i]
            if isinstance(line, str):
                new = []
                for char in line:
                    new.append(char)
                    if east_asian_width(char) in 'WF': # 'W'ide & 'F'ull-width
                        new.append(pad_char)
                self.data[i] = ''.join(new)

    def replace(self, old, new):
        """Replace all occurrences of substring `old` with `new`."""
        for i in range(len(self.data)):
            self.data[i] = self.data[i].replace(old, new)


class StateMachineError(Exception): pass
class UnknownStateError(StateMachineError): pass
class DuplicateStateError(StateMachineError): pass
class UnknownTransitionError(StateMachineError): pass
class DuplicateTransitionError(StateMachineError): pass
class TransitionPatternNotFound(StateMachineError): pass
class TransitionMethodNotFound(StateMachineError): pass
class UnexpectedIndentationError(StateMachineError): pass


class TransitionCorrection(Exception):

    """
    Raise from within a transition method to switch to another transition.

    Raise with one argument, the new transition name.
    """


class StateCorrection(Exception):

    """
    Raise from within a transition method to switch to another state.

    Raise with one or two arguments: new state name, and an optional new
    transition name.
    """


def string2lines(astring, tab_width=8, convert_whitespace=False,
                 whitespace=re.compile('[\v\f]')):
    """
    Return a list of one-line strings with tabs expanded, no newlines, and
    trailing whitespace stripped.

    Each tab is expanded with between 1 and `tab_width` spaces, so that the
    next character's index becomes a multiple of `tab_width` (8 by default).

    Parameters:

    - `astring`: a multi-line string.
    - `tab_width`: the number of columns between tab stops.
    - `convert_whitespace`: convert form feeds and vertical tabs to spaces?
    """
    if convert_whitespace:
        astring = whitespace.sub(' ', astring)
    return [s.expandtabs(tab_width).rstrip() for s in astring.splitlines()]

def _exception_data():
    """
    Return exception information:

    - the exception's class name;
    - the exception object;
    - the name of the file containing the offending code;
    - the line number of the offending code;
    - the function name of the offending code.
    """
    type, value, traceback = sys.exc_info()
    while traceback.tb_next:
        traceback = traceback.tb_next
    code = traceback.tb_frame.f_code
    return (type.__name__, value, code.co_filename, traceback.tb_lineno,
            code.co_name)
