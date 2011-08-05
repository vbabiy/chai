'''
Implementation of stubbing
'''
import inspect
import types
import os
import sys
import gc

from expectation import Expectation, ArgumentsExpectationRule
from exception import *
from termcolor import colored

# NOTE: imports at the bottom

# For clarity here and in tests, could make these class or static methods on
# Stub. Chai base class would hide that.
def stub(obj, attr=None):
  '''
  Stub an object. If attr is not None, will attempt to stub that attribute
  on the object. Only required for modules and other rare cases where we
  can't determine the binding from the object.
  '''
  handler = Handler.detect(obj, attr)
  
  if isinstance(handler, Stub):
    return handler
  
  # Use StubProperty for properties
  if isinstance(handler, PropertyHandler):
    return StubProperty(handler)

  return Stub(handler)

class Stub(object):
  '''
  Base class for all stubs.
  '''

  def __init__(self, handler):
    '''
    Setup the structs for expectations
    '''
    self._expectations = []
    self.handler = handler
    self.handler.set(self)

  @property
  def name(self):
    return str(self.handler)

  def unmet_expectations(self):
    '''
    Assert that all expectations on the stub have been met.
    '''
    unmet = []
    for exp in self._expectations:
      if not exp.closed(with_counts=True):
        unmet.append(ExpectationNotSatisfied(exp))
    return unmet

  def teardown(self):
    '''
    Clean up all expectations and restore the original attribute of the mocked
    object.
    '''
    self.handler.replace()
    self._expectations = []

  def expect(self):
    '''
    Add an expectation to this stub. Return the expectation
    '''
    exp = Expectation(self)
    self._expectations.append( exp )
    return exp

  def __call__(self, *args, **kwargs):
    for exp in self._expectations:
      # If expectation closed skip
      if exp.closed():
        continue

      # If args don't match the expectation, close it and move on, else
      # pass to it for testing.
      if not exp.match(*args, **kwargs):
        exp.close(*args, **kwargs)
      else:
        return exp.test(*args, **kwargs)

    raise UnexpectedCall("\n\n" + self._format_exception(ArgumentsExpectationRule.pretty_format_args(*args, **kwargs)))

  def _format_exception(self, args_str):
    result = [
      colored("No expectation in place for %s with %s" % (self.name, args_str), "red"),
      "All Expectations:"
    ]
    for exception in self._expectations:
      result.append(str(exception))

    return "\n".join(result)

class StubProperty(Stub, property):
  '''
  Property stubbing.
  '''

  def __init__(self, handler):
    property.__init__(self, lambda x: self(),
      lambda x, val: self.setter(val), lambda x: self.deleter() )

    super(StubProperty,self).__init__(handler)

from handlers import *