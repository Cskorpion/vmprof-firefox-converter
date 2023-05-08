import os
import json
import vmprof
from vmprofconvert import convert
from vmprofconvert import convert_vmprof
from vmprofconvert import convert_stats
from vmprofconvert import Converter
from vmprofconvert import Thread

class Dummystats():
    def __init__(self, profiles):
        self.profiles = profiles
        self.profile_lines = True
        self.profile_memory = False
        self.end_time = Dummytime(10)
        self.start_time = Dummytime(0)
    
    def get_addr_info(self, addr):
        return ("py", addr, 0, "dummyfile.py")

class Dummytime():
    def __init__(self, time):
        self.time = time
    
    def timestamp(self):
        return self.time
    
def test_example():
    path = os.path.join(os.path.dirname(__file__), "profiles/example.prof")
    result = convert(path)
    
def test_stringarray():
    t = Thread()
    index = t.add_string("Hallo")
    assert index == 0
    index = t.add_string("Hallo")
    assert index == 0
    index = t.add_string("Huhu")
    assert index == 1
    assert t.stringarray == ["Hallo", "Huhu"]

def test_stacktable():
    t = Thread()
    assert t.add_stack([], 0) is None
    stackindex0 = t.add_stack([1,2,3], [0,0,0])# Top of Stack is 3    [stack], [categorys]
    stackindex1 = t.add_stack([1,2,3], [0,0,0])
    assert stackindex0 == stackindex1 == 2
    assert t.stacktable == [[1,None,0], [2,0,0], [3,1,0]]
    stackindex2 = t.add_stack([1,2,3,4], [0,0,0,1])
    print(t.stacktable)
    assert stackindex2 == stackindex1 + 1

def test_frametable():
    t = Thread()
    frameindex0 = t.add_frame("duck", -1, "dummyfile.py")# string, line, file
    frameindex1 = t.add_frame("duck", -1, "dummyfile.py")
    assert frameindex0 == frameindex1 == 0
    frameindex2 = t.add_frame("goose", -1, "dummyfile.py")
    assert frameindex2 == frameindex1 + 1
    assert t.frametable == [[0, -1],[1, -1]]
    assert t.stringarray == ["duck", "dummyfile.py" , "goose"]

def test_functable():
    t = Thread()
    funcindex0 = t.add_func("function_a", "dummyfile.py")# func, file
    funcindex1 = t.add_func("function_a", "dummyfile.py")
    assert funcindex0 == funcindex1 == 0
    funcindex2 = t.add_func("function_b", "dummyfile.py")
    assert funcindex2 == funcindex1 + 1
    assert t.functable == [[0,1],[2,1]]
    assert t.stringarray == ["function_a", "dummyfile.py" , "function_b"]

def test_sampleslist():
    t = Thread()
    t.add_sample(0, 7, 3)# samples with same stack
    t.add_sample(0, 13, 3)# samples with same stack
    t.add_sample(1, 17, 4)
    assert t.samples == [[0, 7, 3], [0, 13, 3], [1, 17, 4]]

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
    t = c.threads[12345] # info now stored in thread inside Converter
    assert t.stringarray == ["function_a", "dummyfile.py", "function_b", "function_c"]
    assert t.frametable == [[0, 7], [1, 17], [2, 117]]# stringtableindex, line
    assert t.stacktable == [[0, None, 0], [1, 0, 0], [2, 0, 0]]
    assert t.samples == [[1, 0.0, 7], [2, 5000.0, 7]]# stackindex time dummyeventdelay = 7

def test_walksample_vmprof():
    path = os.path.join(os.path.dirname(__file__), "profiles/example.prof")
    c = convert_vmprof(path)
    t = list(c.threads.values())[0]# get thread from Converter
    assert len(t.samples) == 2535# number of samples in example.prof

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
    dumped_funcreferences = jsonobject["threads"][0]["frameTable"]["func"]
    expected_dumped_funcreferences = [0,1,2]
    assert dumped_funcreferences == expected_dumped_funcreferences

def test_dumps_vmprof_no_lines():
    path = os.path.join(os.path.dirname(__file__), "profiles/example.prof")#profile_lines == False
    c = convert(path)
    jsonstr = c.dumps_static()
    path = os.path.join(os.path.dirname(__file__), "profiles/example.json")
    jsonobject = json.loads(jsonstr)
    dumped_frametable = jsonobject["threads"][0]["frameTable"]
    assert "line" not in dumped_frametable

    
def test_dumps_vmprof():
    path = os.path.join(os.path.dirname(__file__), "profiles/example.prof")
    c = convert(path)
    jsonstr = c.dumps_static()
    path = os.path.join(os.path.dirname(__file__), "profiles/example.json")
    with open(path, "w") as output_file:
        output_file.write(json.dumps(json.loads(jsonstr), indent=2))
    t = list(c.threads.values())[0]
    assert "function_a" in str(t.stringarray)


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
    path = os.path.join(os.path.dirname(__file__), "profiles/vmprof_cpuburn.prof")
    jsonstr = convert_stats(path)
    path = os.path.join(os.path.dirname(__file__), "profiles/vmprof_cpuburn.json")
    with open(path, "w") as output_file:
        output_file.write(json.dumps(json.loads(jsonstr), indent=2))
    assert True

def test_profiles():
    #test multiple profiles in one run
    profiles = []
    profiles.append("profiles/example.prof")
    profiles.append("profiles/vmprof_cpuburn.prof")# cpuburn.py can be found in vmprof-python github repo
    profiles.append("profiles/multithread_example.prof")
    expected_samples_count = {}
    expected_samples_count["profiles/example.prof"] = 2535
    expected_samples_count["profiles/vmprof_cpuburn.prof"] = 5551
    expected_samples_count["profiles/multithread_example.prof"] = 436
    for profile in profiles:
        path = os.path.join(os.path.dirname(__file__), profile)
        c = convert_vmprof(path)
        threads = list(c.threads.values())
        samples_c = sum(len(thread.samples) for thread in threads)
        assert samples_c == expected_samples_count[profile]

def test_multiple_threads():
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
        54321, #thread id
        0 # memory usage in kb
    )
    c.walk_samples(Dummystats([vmprof_like_sample0, vmprof_like_sample1]))
    path = os.path.join(os.path.dirname(__file__), "profiles/dummy.json")
    with open(path, "w") as output_file:
        output_file.write(json.dumps(json.loads(c.dumps_static()), indent=2))
    t_12345 = c.threads[12345]
    t_54321 = c.threads[54321]
    threadids = list(c.threads.keys())
    expected_threadids = [12345, 54321]
    assert  threadids == expected_threadids
    assert len(t_12345.stringarray) == 3
    assert len(t_54321.stringarray) == 4

def test_dumps_vmprof_memory():
    path = os.path.join(os.path.dirname(__file__), "profiles/vmprof_cpuburn.prof")
    jsonstr = convert_stats(path)
    path = os.path.join(os.path.dirname(__file__), "profiles/vmprof_cpuburn.json")
    profile = json.loads(jsonstr)
    memory_samples = profile["counters"][0]["sampleGroups"][0]["samples"]
    assert memory_samples["count"][0] == 11972000
    assert memory_samples["count"][1] == 11972000 # Firefox wont show memory unless two samples are not zero
    assert sum(memory_samples["count"][2:]) == 0
    assert len(memory_samples["count"]) == 5551