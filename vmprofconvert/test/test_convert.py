import os
import json
from vmprofconvert import convert
from vmprofconvert import convert_vmprof
from vmprofconvert import Converter

class Dummystats():
    def __init__(self, profiles):
        self.profiles = profiles
        self.profile_lines = True
    
    def get_addr_info(self, addr):
        return ("py", addr, 0, "dummyfile.py")
    
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

def test_frametable():
    c = Converter()
    frameindex0 = c.add_frame("duck")
    frameindex1 = c.add_frame("duck")
    assert frameindex0 == frameindex1 == 0
    frameindex2 = c.add_frame("goose")
    assert frameindex2 == frameindex1 + 1
    assert c.frametable == [0,1]
    assert c.stringtable == ["duck", "goose"]

def test_sampleslist():
    c = Converter()
    c.add_sample(0, 7, 3)# samples with same stack
    c.add_sample(0, 13, 3)# samples with same stack
    c.add_sample(1, 17, 4)
    assert c.samples == [[0, 7, 3], [0, 13, 3], [1, 17, 4]]

def test_walksamples():
    c = Converter()
    vmprof_like_sample0 = (
        ["function_a",
         -7,
         "function_b",
         -17], # callstack with line numbers
         1, # samples count
         12345, #thread id
         0 # memory usage in kb
    )
    vmprof_like_sample1 = (
        ["function_a",
         -7,
         "function_c",
         -117], # callstack with line numbers
         1, # samples count
         12345, #thread id
         0 # memory usage in kb
    )
    c.walk_samples(Dummystats([vmprof_like_sample0, vmprof_like_sample1]))
    assert c.stringtable == ["dummyfile.py:function_a", "dummyfile.py:function_b", "dummyfile.py:function_c"]
    assert c.frametable == [0, 1, 2]
    assert c.stacktable == [[0, None], [1, 0], [2, 0]]
    assert c.samples == [[1, 0, 7], [2, 1, 7]]# stackindex time dummyeventdelay = 7

def test_walksample_vmprof():
    path = os.path.join(os.path.dirname(__file__), "example.prof")
    c = convert_vmprof(path)
    assert len(c.samples) == 2535# number of samples in example.prof

def test_dumps_simple_profile():
    c = Converter()
    vmprof_like_sample0 = (
        ["function_a",
         -7,
         "function_b",
         -17], # callstack with line numbers
         1, # samples count
         12345, #thread id
         0 # memory usage in kb
    )
    vmprof_like_sample1 = (
        ["function_a",
         -7,
         "function_b",
         -17,
         "function_c",
         -27], # callstack with line numbers
         1, # samples count
         12345, #thread id
         0 # memory usage in kb
    )
    c.walk_samples(Dummystats([vmprof_like_sample0, vmprof_like_sample1]))
    jsonstr = c.dumps()
    path = os.path.join(os.path.dirname(__file__), "example.json")
    with open(path, "w") as output_file:
        output_file.write(json.dumps(json.loads(jsonstr), indent=2))
    assert True
    
def test_dumps_vmprof():
    path = os.path.join(os.path.dirname(__file__), "example.prof")
    c = convert(path)
    jsonstr = c.dumps()
    path = os.path.join(os.path.dirname(__file__), "example.json")
    with open(path, "w") as output_file:
        output_file.write(json.dumps(json.loads(jsonstr), indent=2))
    assert "function_a" in str(c.stringtable)
