import os
from vmprofconvert import convert
from vmprofconvert import Converter

def test_example():
    path = os.path.join(os.path.dirname(__file__), "example.prof")
    result = convert(path)
    
def test_stringtable():
    c = Converter()
    index = c.add_string("Hallo")
    assert index == 0
    index = c.add_string("Hallo")
    assert index == 0
    index = c.add_string("Huhu")
    assert index == 1
    assert c.stringtable == ["Hallo", "Huhu"]

def test_stacktable():
    c = Converter()
    assert c.add_stack([]) is None
    stackindex0 = c.add_stack([1,2,3])# Top of Stack is 3
    stackindex1 = c.add_stack([1,2,3])
    assert stackindex0 == stackindex1 == 2
    assert c.stacktable == [[1,None], [2,0], [3,1]]
    stackindex2 = c.add_stack([1,2,3,4])
    assert stackindex2 == stackindex1 + 1

