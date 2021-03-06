
import unittest
from collections import deque

from chai import Chai
from chai.chai import ChaiTestType
from chai.mock import Mock
from chai.stub import Stub
from chai.exception import *
from chai.comparators import Comparator
from chai.handlers import *

class CupOf(Chai):
  '''
  An example of a subclass on which we can test certain features.
  '''

  class msg_equals(Comparator):
    '''
    A Comparator used for check message equality
    '''
    def __init__(self, (key,value)):
      self._key = key
      self._value = value

    def test(self, value):
      if isinstance(value,dict):
        return self._value==value.get(self._key)
      return False

  def assert_msg_sent(self, msg):
    '''
    Assert that a message was sent and marked that it was handled.
    '''
    return msg.get('sent_at') and msg.get('received')

  def test_local_definitions_work_and_are_global(self):
    class Foo(object):
      def _save_data(self, msg):
        pass #dosomethingtottalyawesomewiththismessage
        
      def do_it(self, msg):
        self._save_data(msg)
        msg['sent_at'] = 'now'
        msg['received'] = 'yes'

    f = Foo()
    expect( f._save_data ).args( msg_equals(('target','bob')) )
    
    msg = {'target':'bob'}
    f.do_it( msg )
    assert_msg_sent( msg )

  def test_something(self): pass
  def runTest(self, *args, **kwargs): pass

class ChaiTest(unittest.TestCase):

  def test_init(self):
    case = CupOf.__new__(CupOf)
    self.assertTrue( hasattr(case, 'assertEquals') )
    self.assertFalse( hasattr(case, 'assert_equals') )
    case.__init__()
    self.assertTrue( hasattr(case, 'assertEquals') )
    self.assertTrue( hasattr(case, 'assert_equals') )

  def test_setup(self):
    case = CupOf()
    case.setup()
    self.assertEquals( deque(), case._stubs )
    self.assertEquals( deque(), case._mocks )

  def test_teardown_closes_out_stubs_and_mocks(self):
      class Stub(object):
        calls = 0
        def teardown(self): self.calls += 1
    
      obj = type('test',(object,),{})()
      setattr(obj, 'mock1', 'foo')
      setattr(obj, 'mock2', 'bar')
      
      case = CupOf()
      stub = Stub()
      case._stubs = deque([stub])
      handler = MethodHandler(obj, 'mock1')
      handler._original = 'fee'
      case._mocks = deque([handler, (obj,'mock2')])
      case.teardown()
      self.assertEquals( 1, stub.calls )
      self.assertEquals( 'fee', obj.mock1 )
      self.assertFalse( hasattr(obj, 'mock2') )

  def test_stub(self):
    class Milk(object):
      def pour(self): pass

    case = CupOf()
    milk = Milk()
    case.setup()
    self.assertEquals( deque(), case._stubs )
    case.stub( milk.pour )
    self.assertTrue( isinstance(milk.pour, Stub) )
    self.assertEquals( deque([milk.pour]), case._stubs )

    # Test it's only added once
    case.stub( milk, 'pour' )
    self.assertEquals( deque([milk.pour]), case._stubs )

  def test_expect(self):
    class Milk(object):
      def pour(self): pass

    case = CupOf()
    milk = Milk()
    case.setup()
    self.assertEquals( deque(), case._stubs )
    case.expect( milk.pour )
    self.assertEquals( deque([milk.pour]), case._stubs )

    # Test it's only added once
    case.expect( milk, 'pour' )
    self.assertEquals( deque([milk.pour]), case._stubs )

    self.assertEquals( 2, len(milk.pour._expectations) )

  def test_mock_no_binding(self):
    case = CupOf()
    case.setup()

    self.assertEquals( deque(), case._mocks )
    mock1 = case.mock()
    self.assertTrue( isinstance(mock1, Mock) )
    self.assertEquals( deque(), case._mocks )
    mock2 = case.mock()
    self.assertTrue( isinstance(mock2, Mock) )
    self.assertEquals( deque(), case._mocks )
    self.assertNotEqual( mock1, mock2 )

  def test_mock_with_attr_binding(self):
    class Milk(object):
      def __init__(self): self._case = []
      def pour(self): return self._case.pop(0)

    case = CupOf()
    case.setup()
    milk = Milk()
    orig_pour = milk.pour

    self.assertEquals( deque(), case._mocks )
    mock1 = case.mock( milk, 'pour' )
    self.assertTrue( isinstance(mock1, Mock) )
    mock2 = case.mock( milk, 'pour' )
    self.assertTrue( isinstance(mock2, Mock) )
    self.assertNotEqual( mock1, mock2 )

    mock3 = case.mock( milk, 'foo' )
    self.assertTrue( isinstance(mock3, Mock) )
    
  def test_chai_class_use_metaclass(self):
    obj = CupOf()    
    self.assertTrue(obj, ChaiTestType)
    
  def test_runs_unmet_expectations(self):
    class Stub(object):
      calls = 0
      def unmet_expectations(self): self.calls += 1; return []
      def teardown(self): self.calls += 1

    # obj = type('test',(object,),{})()
    # setattr(obj, 'mock1', 'foo')
    # setattr(obj, 'mock2', 'bar')
    
    case = CupOf()
    stub = Stub()
    case._stubs = deque([stub])
    
    case.test_local_definitions_work_and_are_global()
    self.assertEquals(stub.calls, 1)