import os
import json
import vmprof
from vmprofconvert import convert
from vmprofconvert import convert_vmprof
from vmprofconvert import convert_stats
from vmprofconvert import Converter

class Dummystats():
    def __init__(self, profiles):
        self.profiles = profiles
        self.profile_lines = True
    
    def get_addr_info(self, addr):
        return ("py", addr, 0, "dummyfile.py")
    
def test_example():
    path = os.path.join(os.path.dirname(__file__), "profiles/example.prof")
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
    frameindex0 = c.add_frame("duck", -1)# string, line
    frameindex1 = c.add_frame("duck", -1)
    assert frameindex0 == frameindex1 == 0
    frameindex2 = c.add_frame("goose", -1)
    assert frameindex2 == frameindex1 + 1
    assert c.frametable == [[0, -1],[1, -1]]
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
    assert c.frametable == [[0, 7], [1, 17], [2, 117]]# stringtableindex, line
    assert c.stacktable == [[0, None], [1, 0], [2, 0]]
    assert c.samples == [[1, 0, 7], [2, 1, 7]]# stackindex time dummyeventdelay = 7

def test_walksample_vmprof():
    path = os.path.join(os.path.dirname(__file__), "profiles/example.prof")
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
    jsonstr = c.dumps_static()
    path = os.path.join(os.path.dirname(__file__), "profiles/example.json")
    with open(path, "w") as output_file:
        output_file.write(json.dumps(json.loads(jsonstr), indent=2))
    jsonobject = json.loads(jsonstr)
    dumped_frametable = jsonobject["threads"][0]["frameTable"]["data"]
    expected_dumped_frametable = [[0, False, 2, 1, 7], [1, False, 2, 1, 17], [2, False, 2, 1, 27]] # stringtableindex, relevantforJS, innerwindowID, implementation, line
    assert dumped_frametable == expected_dumped_frametable

def test_dumps_vmprof_no_lines():
    path = os.path.join(os.path.dirname(__file__), "profiles/example.prof")#profile_lines == False
    c = convert(path)
    jsonstr = c.dumps_static()
    path = os.path.join(os.path.dirname(__file__), "profiles/example.json")
    jsonobject = json.loads(jsonstr)
    dumped_frametable_schema = jsonobject["threads"][0]["frameTable"]["schema"]
    expected_frametable_schema = {
        "location": 0,
        "relevantForJS": 1,
        "innerWindowID": 2,
        "implementation": 3
    }
    assert dumped_frametable_schema == expected_frametable_schema

    
def test_dumps_vmprof():
    path = os.path.join(os.path.dirname(__file__), "profiles/example.prof")
    c = convert(path)
    jsonstr = c.dumps_static()
    path = os.path.join(os.path.dirname(__file__), "profiles/example.json")
    with open(path, "w") as output_file:
        output_file.write(json.dumps(json.loads(jsonstr), indent=2))
    assert "function_a" in str(c.stringtable)


def test_dump_vmprof_meta():
    path = os.path.join(os.path.dirname(__file__), "profiles/example.prof")
    stats = vmprof.read_profile(path)
    c = Converter()
    meta = c.dump_vmprof_meta(stats)
    assert meta["interval"] == 0.000194
    assert meta["startTime"] == 1681890179831.0
    assert meta["shutdownTime"] == 1681890180325.0
    assert meta["platform"] == "Windows"
    assert meta["oscpu"] == "Windows 64bit"
    assert meta["abi"] == "cpython"# data from example.prof

def test_dumps_vmprof_with_meta():
    path = os.path.join(os.path.dirname(__file__), "profiles/example.prof")
    jsonstr = convert_stats(path)
    path = os.path.join(os.path.dirname(__file__), "profiles/example.json")
    with open(path, "w") as output_file:
        output_file.write(json.dumps(json.loads(jsonstr), indent=2))
    assert True

def test_profiles():
    #testing multiple profiles in one run
    profiles = ["profiles/example.prof", "profiles/vmprof_cpuburn.prof"]# cpuburn.py can be found in vmprof-python github repo
    expected_samples_count = {}
    expected_samples_count["profiles/example.prof"] = 2535
    expected_samples_count["profiles/vmprof_cpuburn.prof"] = 951242
    for profile in profiles:
        path = os.path.join(os.path.dirname(__file__), profile)
        c = convert_vmprof(path)
        assert len(c.samples) == expected_samples_count[profile]