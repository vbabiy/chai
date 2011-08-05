"""
A collection of classes to handle replacing a stub/mock with the original value.
"""

from exception import UnknownType

import inspect
import types
import sys
import gc

class BaseHandler(object):

  def __init__(self, obj, attr_name, use_class=False):
    self._obj = obj
    self._attr_name = attr_name
    self._use_class = use_class
  
  def set(self, value):
    obj = self._obj
    if self._use_class:
      obj = self.get_class()
    
    # Back up original value
    if not self._attr_name:
      import ipdb; ipdb.set_trace() # FIXME: Remove debugger
    self._original = getattr(obj, self._attr_name) 

    setattr(obj, self._attr_name, value)
  
  def replace(self):
    obj = self._obj
    if self._use_class:
      obj = self.get_class()
    
    setattr(obj, self._attr_name, self._original)
  
  def get_class(self):
    if not inspect.isclass(self._obj):
      if inspect.ismodule(self._obj):
        raise Exception("%s, is a module it has not class", repr(self._obj))
      return self._obj.__class__
    return self._obj

class PropertyHandler(BaseHandler):

  def __init__(self, obj, attr_name=None):
    if not attr_name:
      # We don't have the attr_name, get it.
      if isinstance(obj, property):
        klass = None
        for ref in gc.get_referrers( obj ):
          if obj and attr_name: break
          if isinstance(ref,dict) and ref.get('prop',None) is obj :
            klass = getattr( ref.get('__dict__',None), '__objclass__', None )
            for name,val in getattr(klass,'__dict__',{}).iteritems():
              if val is obj:
                attr_name = name
                break
        obj = klass

      else:
        raise Exception("Can't handle property")
      
    super(PropertyHandler, self).__init__(obj, attr_name, use_class=True)

  def set(self, value):
    # Use a simple Mock object for the deleter and setter. Use same namespace
    # as property type so that it simply works.
    # Annoying circular reference requires importing here. Would like to see
    # this cleaned up. @AW
    from mock import Mock
    value.setter = Mock()
    value.deleter = Mock()

    super(PropertyHandler, self).set(value)
  
  def __str__(self):
    return "%s.%s" % (self.get_class().__name__, self._attr_name)

class MethodHandler(BaseHandler):

  def __init__(self, obj, attr_name):
    if not attr_name:
      # If we don't have to the name get the name and pass it on to the base handler
      attr_name = obj.im_func.func_name
      obj = obj.im_self

    super(MethodHandler, self).__init__(obj, attr_name)
  
  def replace(self):
    '''
    Put the original method back in place. This will also handle the special case
    when it putting back a class method.

    The following code snippet best describe why it fails using settar, the
    class method would be replaced with a bound method not a class method.

    >>> class Example(object):
    ...     @classmethod
    ...     def a_classmethod(self):
    ...         pass
    ...
    >>> Example.__dict__['a_classmethod'] # Note the classmethod is returned.
    <classmethod object at 0x7f5e6c298be8>
    >>> orig = getattr(Example, 'a_classmethod')
    >>> orig
    <bound method type.a_classmethod of <class '__main__.Example'>>
    >>> setattr(Example, 'a_classmethod', orig)
    >>> Example.__dict__['a_classmethod'] # Note that setattr set a bound method not a class method.
    <bound method type.a_classmethod of <class '__main__.Example'>>

    The only way to figure out if this is a class method is to check and see if
    the bound method im_self is a class, if so then we need to wrap the function
    object (im_func) with class method before setting it back on the class.

    '''
    # Figure out if this is a classmethod
    if inspect.isclass(self._obj): # Figure out if this is a class method
      # Wrap it and set it back on the class
      setattr(self._obj, self._attr_name, classmethod(self._original.im_func))
    else:
      setattr(self._obj, self._attr_name, self._original)
  
  def __str__(self):
    if hasattr(self._obj, 'im_class'):
      from mock import Mock
      if issubclass(self._obj.im_class, Mock):
        return "%s (on mock object)" % self._obj.im_self._name

    # Always use the class to get the name
    klass = self._obj
    if not inspect.isclass(self._obj):
      klass = self._obj.__class__

    return "%s.%s" % (klass.__name__, self._attr_name)

class MockHandler(BaseHandler):
  def __init__(self, obj, attr_name):
    if attr_name:
      super(MockHandler, self).__init__(getattr(obj, attr_name), '__call__')  
    else:
      super(MockHandler, self).__init__(obj, '__call__')

class FunctionHandler(BaseHandler):
  def __init__(self, obj, attr_name):
    if not attr_name:
      # If we don't have to the name get the name and pass it on to the base handler
      attr_name = obj.func_name
      obj = sys.modules[obj.__module__]

    super(FunctionHandler, self).__init__(obj, attr_name)

class UnboundMethodHandler(BaseHandler):
  def __init__(self, obj, attr_name):
    if not attr_name:
      # If we don't have to the name get the name and pass it on to the base handler
      attr_name = obj.im_func.func_name
      obj = obj.im_class

    super(UnboundMethodHandler, self).__init__(obj, attr_name)


class MethodWrapperHandler(BaseHandler):
  def __init__(self, obj, attr_name):
    if not attr_name:
      # If we don't have to the name get the name and pass it on to the base handler
      attr_name = obj.__name__
      obj = obj.__self__

    super(MethodWrapperHandler, self).__init__(obj, attr_name)


class Handler(object):

  @classmethod
  def detect(self, obj, attr_name):
    """
    A factor function to detect the type attr and returns the correct handler.
    """
    if self.is_property(obj, attr_name):
      return PropertyHandler(obj, attr_name)
    
    if self.is_stub(obj, attr_name):
      if attr_name:
        return getattr(obj, attr_name)
      else:
        return obj
    
    if self.is_mock(obj, attr_name):
      return MockHandler(obj, attr_name)
    
    if self.is_function(obj, attr_name):
      return FunctionHandler(obj, attr_name)
    
    if self.is_unbound_method(obj, attr_name):
      return UnboundMethodHandler(obj, attr_name)
    
    if self.is_bound_method(obj, attr_name):
      return MethodHandler(obj, attr_name)
    
    if self.is_method_wrapper(obj, attr_name):
      return MethodWrapperHandler(obj, attr_name)
    
    if self.is_wrapper_discriptor(obj, attr_name):
      raise Exception("Can't find an example") # FIXME: NOW
      return WrapperDiscriptorHandler(obj, attr_name)
    
    raise UnknownType("Not able to detect type: %s", obj)
    
  
  @classmethod
  def is_property(self, obj, attr_name):
    """
    Does the magic need to figure out if this a property
    """
    if attr_name:
      attr = None
      if inspect.isclass(obj):
        attr = getattr(obj, attr_name)
      else:
        if not inspect.ismodule(obj):
          attr = getattr(obj.__class__, attr_name)
        else:
          return False
      
      if isinstance(attr, property):
        return True
    else:
      if isinstance(obj, property):
        return True
    return False

  @classmethod
  def is_stub(self, *args):
    """
    Check to see if this is a stub.
    """
    from stub import Stub
    return self._check_type(args, Stub)

  @classmethod
  def is_mock(self, *args):
    """
    Check to see if this is a Mock.
    """
    from mock import Mock
    return self._check_type(args, Mock)
  
  @classmethod
  def is_function(self, obj, attr_name):
    """
    Check to see if this is function with in a module
    """
    if inspect.ismodule(obj) or isinstance(obj, types.FunctionType):
      return True
    return False
  
  @classmethod
  def is_unbound_method(self, obj, attr_name):
    method = None

    if attr_name:
      method = getattr(obj, attr_name)
    else:
      method = obj

    if isinstance(method, types.MethodType):
      if method.im_self is None:
        return True
    
    return False

  @classmethod
  def is_bound_method(self, obj, attr_name):
    method = None

    if attr_name:
      method = getattr(obj, attr_name)
    else:
      method = obj

    if isinstance(method, types.MethodType):
      if method.im_self:
        return True
    
    return False

  @classmethod
  def is_method_wrapper(self, obj, attr_name):
    attr = obj
    if attr_name:
      attr = getattr(obj, attr_name)
    # FIXME: is there no better way to figure this out.
    return type(attr).__name__ == 'method-wrapper'

  @classmethod
  def is_wrapper_discriptor(self, obj, attr_name):
    attr = obj
    if attr_name:
      attr = getattr(obj, attr_name)

    # FIXME: is there no better way to figure this out.
    return type(attr).__name__ == 'wrapper_descriptor'

  # Helpers
  
  @classmethod
  def _check_type(self, args, types):
    if len(args) > 1:
      if all(args):
        return isinstance(getattr(args[0], args[1]), types)
    return isinstance(args[0], types)
