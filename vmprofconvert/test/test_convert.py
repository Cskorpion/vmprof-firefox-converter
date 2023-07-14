import os
import json
import vmprof
from zipfile import ZipFile
from vmprof.reader import JittedCode, AssemblerCode
from vmprofconvert import convert
from vmprofconvert import convert_vmprof, convert_stats_with_pypylog
from vmprofconvert import convert_stats
from vmprofconvert import Converter
from vmprofconvert import Thread
from vmprofconvert import CATEGORY_PYTHON, CATEGORY_NATIVE, CATEGORY_JIT, CATEGORY_ASM, CATEGORY_JIT_INLINED, CATEGORY_MIXED, CATEGORY_INTERPRETER
from vmprofconvert.pypylog import parse_pypylog, cut_pypylog, rescale_pypylog, filter_top_level_logs
from vmprofconvert.__main__ import write_file_dict, save_zip, load_zip_dict, extract_files

class Dummystats():
    def __init__(self, profiles):
        self.profiles = profiles
        self.profile_lines = True
        self.profile_memory = False
        self.end_time = Dummytime(10)
        self.start_time = Dummytime(0)
    
    def get_addr_info(self, addr):
        return ("py", self.addr_dict[addr], 0, "dummyfile.py")

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
    stackindex0 = t.add_stack([1,2,3], [CATEGORY_PYTHON, CATEGORY_PYTHON, CATEGORY_PYTHON])# Top of Stack is 3    [stack], [categorys]
    stackindex1 = t.add_stack([1,2,3], [CATEGORY_PYTHON, CATEGORY_PYTHON, CATEGORY_PYTHON])
    assert stackindex0 == stackindex1 == 2
    assert t.stacktable == [[1,None, CATEGORY_PYTHON], [2,0, CATEGORY_PYTHON], [3,1, CATEGORY_PYTHON]]
    stackindex2 = t.add_stack([1,2,3,4], [CATEGORY_PYTHON, CATEGORY_PYTHON, CATEGORY_PYTHON, CATEGORY_NATIVE])
    assert stackindex2 == stackindex1 + 1

def test_frametable():
    t = Thread()
    frameindex0 = t.add_frame("duck", -1, "dummyfile.py", CATEGORY_PYTHON, -1, -1)# string, line, file, nativesymbol_index, addr
    frameindex1 = t.add_frame("duck", -1, "dummyfile.py", CATEGORY_PYTHON, -1, -1)
    assert frameindex0 == frameindex1 == 0
    frameindex2 = t.add_frame("goose", -1, "dummyfile.py", CATEGORY_PYTHON, -1, -1)
    assert frameindex2 == frameindex1 + 1
    assert t.frametable == [[0, -1, -1],[1, -1, -1]]
    assert t.stringarray == ["duck", "dummyfile.py" , "goose"]

def test_functable():
    t = Thread()
    funcindex0 = t.add_func("function_a", "dummyfile.py", 7, CATEGORY_PYTHON, -1)# func, file, line, resource
    funcindex1 = t.add_func("function_a", "dummyfile.py", 7, CATEGORY_PYTHON, -1 )
    assert funcindex0 == funcindex1 == 0
    funcindex2 = t.add_func("function_b", "dummyfile.py", 17, CATEGORY_PYTHON, -1)
    assert funcindex2 == funcindex1 + 1
    assert t.functable == [[0, 1, 7, -1],[2, 1, 17, -1]]
    assert t.stringarray == ["function_a", "dummyfile.py" , "function_b"]

def test_sampleslist():
    t = Thread()
    t.add_sample(0, 7)# samples with same stack
    t.add_sample(0, 13)# samples with same stack
    t.add_sample(1, 17)
    assert t.samples == [[0, 7], [0, 13], [1, 17]]

def test_walksamples():
    c = Converter()
    vmprof_like_sample0 = (
        [0,# address
         -7,# line
         1,
         -17], # callstack with line numbers
         1, # samples count
         12345, #thread id
         0 # memory usage in kb
    )
    vmprof_like_sample1 = (
        [0,
         -7,
         2,
         -117], # callstack with line numbers
         1, # samples count
         12345, #thread id
         0 # memory usage in kb
    )
    stats = Dummystats([vmprof_like_sample0, vmprof_like_sample1])
    stats.addr_dict = {0: "function_a", 1: "function_b", 2: "function_c"}
    c.walk_samples(stats)
    t = c.threads[12345] # info now stored in thread inside Converter
    assert t.stringarray == ["function_a", "dummyfile.py", "function_b", "function_c"]
    assert t.frametable == [[0, 0, 7], [1, 1, 17], [2, 2, 117]]# stringtableindex, nativesymbol_index
    assert t.stacktable == [[0, None, CATEGORY_PYTHON], [1, 0, CATEGORY_PYTHON], [2, 0, CATEGORY_PYTHON]]
    assert t.samples == [[1, 0.0], [2, 5000.0]]# stackindex time dummyeventdelay = 7

def test_walksample_vmprof():
    path = os.path.join(os.path.dirname(__file__), "profiles/example.prof")
    c = convert_vmprof(path)
    t = list(c.threads.values())[0]# get thread from Converter
    assert len(t.samples) == 2535# number of samples in example.prof

def test_dumps_simple_profile():
    c = Converter()
    vmprof_like_sample0 = (
        [0,# address
         -7,# line
         1,
         -17], # callstack with line numbers
         1, # samples count
         12345, #thread id
         0 # memory usage in kb
    )
    vmprof_like_sample1 = (
        [0,
         -7,
         1,
         -17,
         2,
         -27], # callstack with line numbers
         1, # samples count
         12345, #thread id
         0 # memory usage in kb
    )
    stats = Dummystats([vmprof_like_sample0, vmprof_like_sample1])
    stats.addr_dict = {0: "function_a", 1: "function_b", 2: "function_c"}
    c.walk_samples(stats)
    jsonstr = c.dumps_static()
    path = os.path.join(os.path.dirname(__file__), "profiles/example.json")
    with open(path, "w") as output_file:
        output_file.write(json.dumps(json.loads(jsonstr), indent=2))
    jsonobject = json.loads(jsonstr)
    dumped_funcreferences = jsonobject["threads"][0]["frameTable"]["func"]
    expected_dumped_funcreferences = [0,1,2]
    assert dumped_funcreferences == expected_dumped_funcreferences

def test_dumps_vmprof_no_lines():
    path = os.path.join(os.path.dirname(__file__), "profiles/example.prof")#profile_lines = False
    c = convert(path)
    jsonstr = c.dumps_static()
    path = os.path.join(os.path.dirname(__file__), "profiles/example.json")
    jsonobject = json.loads(jsonstr)
    dumped_frametable = jsonobject["threads"][0]["frameTable"]
    assert dumped_frametable["line"][0] == 172
    assert dumped_frametable["line"][1] == 64
    
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
    profiles.append("profiles/pypy-pystone.prof")
    profiles.append("profiles/example_with_lines.prof")
    expected_samples_count = {}
    expected_samples_count["profiles/example.prof"] = 2535
    expected_samples_count["profiles/vmprof_cpuburn.prof"] = 5551
    expected_samples_count["profiles/multithread_example.prof"] = 27688
    expected_samples_count["profiles/pypy-pystone.prof"] = 375
    expected_samples_count["profiles/example_with_lines.prof"] = 3431
    for profile in profiles:
        path = os.path.join(os.path.dirname(__file__), profile)
        c = convert_vmprof(path)
        threads = list(c.threads.values())
        samples_c = sum(len(thread.samples) for thread in threads)
        assert samples_c == expected_samples_count[profile]

def test_multiple_threads():
    c = Converter()
    vmprof_like_sample0 = (
        [0,# address
        -7,# line
        1,
        -17], # callstack with line numbers
        1, # samples count
        12345, #thread id
        0 # memory usage in kb
    )
    vmprof_like_sample1 = (
        [0,
        -7,
        1,
        -17,
        2,
        -27], # callstack with line numbers
        1, # samples count
        54321, #thread id
        0 # memory usage in kb
    )
    stats = Dummystats([vmprof_like_sample0, vmprof_like_sample1])
    stats.addr_dict = {0: "function_a", 1: "function_b", 2: "function_c"}
    c.walk_samples(stats)
    path = os.path.join(os.path.dirname(__file__), "profiles/dummy.json")
    with open(path, "w") as output_file:
        output_file.write(json.dumps(json.loads(c.dumps_static()), indent=2))
    t_12345 = c.threads[12345]
    t_54321 = c.threads[54321]
    threadids = list(c.threads.keys())
    expected_threadids = [12345, 54321]
    assert threadids == expected_threadids
    assert len(t_12345.stringarray) == 3
    assert len(t_54321.stringarray) == 4

def test_dumps_vmprof_memory():
    path = os.path.join(os.path.dirname(__file__), "profiles/vmprof_cpuburn.prof")
    jsonstr = convert_stats(path)
    profile = json.loads(jsonstr)
    memory_samples = profile["counters"][0]["sampleGroups"][0]["samples"]
    assert memory_samples["count"][0] == 11972000
    assert memory_samples["count"][1] == 11972000 # Firefox wont show memory unless two samples are not zero
    assert sum(memory_samples["count"][2:]) == 0
    assert len(memory_samples["count"]) == 5551

def test_dumps_filename_lines():
    path = os.path.join(os.path.dirname(__file__), "profiles/vmprof_cpuburn.prof")
    jsonstr = convert_stats(path)
    path = os.path.join(os.path.dirname(__file__), "profiles/vmprof_cpuburn.json")
    profile = json.loads(jsonstr)
    stringarray = profile["threads"][0]["stringArray"]
    functable = profile["threads"][0]["funcTable"] 
    native_file_index =  stringarray.index("-")
    assert native_file_index not in functable["fileName"]

def test_jit_asm_inline():
    c = Converter()
    vmprof_like_sample0 = (
        [0,
         0,# JIT/ASM/Native Frames have line == 0 in Dummystats
        JittedCode(0),# address
        7,# line
        JittedCode(1),# address
        17,# line
        AssemblerCode(2),
        -117], # callstack with line numbers
        1, # samples count
        12345, #thread id
        0 # memory usage in kb
    )
    stats = Dummystats([vmprof_like_sample0])
    stats.addr_dict = {0: "function_a", 1: "function_b", 2: "function_c"}
    c.walk_samples(stats)
    path = os.path.join(os.path.dirname(__file__), "profiles/dummy.json")
    with open(path, "w") as output_file:
        output_file.write(json.dumps(json.loads(c.dumps_static()), indent=2))
    thread = c.threads[12345]
    assert thread.stacktable == [[1, None, CATEGORY_MIXED], [2, 0, CATEGORY_JIT_INLINED]]

def test_pypy_pystone():
    path = os.path.join(os.path.dirname(__file__), "profiles/pypy-pystone.prof")
    jsonstr = convert_stats(path)
    path = os.path.join(os.path.dirname(__file__), "profiles/pypy-pystone.json")
    with open(path, "w") as output_file:
        output_file.write(json.dumps(json.loads(jsonstr), indent=2))
    profile = json.loads(jsonstr)
    stacktable = profile["threads"][0]["stackTable"]     
    assert CATEGORY_JIT not in stacktable["category"]
    assert CATEGORY_ASM not in stacktable["category"]

def test_check_asm_frame():
    categorys = []
    c = Converter()
    thread = Thread()
    stack_info = "asm_function"
    c.check_asm_frame(categorys, stack_info, thread, None)
    assert categorys == []# asm frames currently disabled 
    categorys.append(CATEGORY_JIT)
    thread.add_frame("jit_function", 7, "dummyfile.py", CATEGORY_JIT, 0, -1)
    c.check_asm_frame(categorys, stack_info, thread, 0)
    assert categorys == [CATEGORY_JIT_INLINED]# jit frame + asm frame => jit_inlined frame

def test_add_native_frame():
    c = Converter()
    thread = Thread()
    stack_info = "native_function"
    c.add_native_frame(thread, stack_info)
    assert thread.frametable == [[0, -1, -1]]
    assert thread.functable == [[0, 1, -1, -1]]
    assert thread.stringarray == [stack_info, ""]

def test_add_jit_frame_to_mixed():
    c = Converter()
    thread = Thread()
    categorys =  [CATEGORY_PYTHON]
    addr_info_jit = ("", "function_a", 7, "dummyfile.py")
    frame_index0 = thread.add_frame(addr_info_jit[1], 7, addr_info_jit[3], CATEGORY_PYTHON, -1, -1)
    frames = [frame_index0]
    frame_index1 = c.add_jit_frame(thread, categorys, addr_info_jit, frames)
    frames.append(frame_index1)
    assert categorys == [CATEGORY_MIXED]
    assert frames == [1]

def test_add_jit_frame_not_mixed():
    c = Converter()
    thread = Thread()
    categorys =  []
    frames = []
    addr_info_jit0 = ("", "function_a", 7, "dummyfile.py")
    addr_info_jit1 = ("", "function_b", 17, "dummyfile.py")
    frame_index0 = c.add_jit_frame(thread, categorys, addr_info_jit0, frames)
    frames.append(frame_index0)
    frame_index1 = c.add_jit_frame(thread, categorys, addr_info_jit1, frames)
    frames.append(frame_index1)
    assert categorys == [CATEGORY_JIT, CATEGORY_JIT]
    assert frames == [0,1]

def test_add_vmprof_frame():
    # def add_vmprof_frame(self, addr_info, thread, stack_info, lineprof, j):# native or python frame
    c = Converter()
    thread = Thread()
    addr_info_py = ("py", "function_a", 7, "dummyfile.py")
    addr_info_n = ("n", "function_b", 0, "dummyfile.py")
    stack_info = [0, -7, 1, 0]# addr, line, addr, line
    profile_lines = True
    c.add_vmprof_frame(addr_info_py, thread, stack_info, profile_lines, CATEGORY_PYTHON, 0)
    c.add_vmprof_frame(addr_info_n, thread, stack_info, profile_lines, CATEGORY_NATIVE, 2)
    assert thread.frametable == [[0, 0, 7], [1, 1, 0]]
    assert thread.functable == [[0, 1, 7, 0], [2, 1, 0, 1]]
    assert thread.stringarray == ["function_a", "dummyfile.py", "function_b"]

def test_add_lib():
    c = Converter()
    lib_index0 = c.add_lib("duck.py", "func_a")
    lib_index1 = c.add_lib("duck.py", "func_a")
    lib_index2 = c.add_lib("goose.py", "func_b")
    assert lib_index0 == lib_index1
    assert lib_index1 == lib_index2 - 1
    assert c.libs == [["duck.py","func_a"],["goose.py", "func_b"]]# Not in a thread

def test_add_native_symbol():
    t = Thread()
    nativesymbol_index0 = t.add_nativesymbol(0, "function_x", 7)
    nativesymbol_index1 = t.add_nativesymbol(1, "function_y", 17)
    assert nativesymbol_index0 == nativesymbol_index1 - 1
    assert t.nativesymbols == [[0, 0, 7],[1, 1, 17]]# libindex, stringindex, addr

def test_add_resource():
    t = Thread()
    lib_index0 = 0
    lib_index1 = 1
    string_index0 = t.add_string("function_x")
    string_index1 = t.add_string("function_y")
    resource_index0 = t.add_resource(lib_index0, string_index0)
    resource_index1 = t.add_resource(lib_index1, string_index1)
    assert resource_index0 == resource_index1 - 1
    assert t.resourcetable == [[0,0],[1,1]]# libindex, stringindex

def test_add_marker():
    t = Thread()
    t.add_marker(7, 17, 0) # starttime endtime stringtable_index
    t.add_marker(17, 117, 1)
    expected_marker0 = [7, 17, 0]
    expected_marker1 = [17, 117, 1]
    assert t.markers == [expected_marker0, expected_marker1]

def test_parse_pypylog():
    pypylog_path = os.path.join(os.path.dirname(__file__), "profiles/pystone.pypylog")
    pypylog = parse_pypylog(pypylog_path)
    assert pypylog[0] == [314906064138,"gc-set-nursery-size", True, 0]
    assert pypylog[-1] == [317567248367,"jit-summary", False, 0]
    assert len(pypylog) == 8248

def test_cut_pypylog():
    pypylog_path = os.path.join(os.path.dirname(__file__), "profiles/pystone.pypylog")
    initial_pypylog = parse_pypylog(pypylog_path)
    cutted_pypylog = cut_pypylog(initial_pypylog, 1000, 700)
    expected_length = int(8248 * 0.7)
    assert len(initial_pypylog) == 8248
    assert len(cutted_pypylog) == expected_length

def test_rescale_pypylog():
    pypylog_path = os.path.join(os.path.dirname(__file__), "profiles/pystone.pypylog")
    initial_pypylog = parse_pypylog(pypylog_path)
    rescaled_pypylog = rescale_pypylog(initial_pypylog[:1000], 10000000)
    assert rescaled_pypylog[7][0] == 70
    assert rescaled_pypylog[-1][0] == 9990

def test_filter_top_level_logs():
    pypylog_path = os.path.join(os.path.dirname(__file__), "profiles/pystone.pypylog")
    initial_pypylog = parse_pypylog(pypylog_path)
    filtered_pypylog = filter_top_level_logs(initial_pypylog[:25])
    assert initial_pypylog[6][1] != initial_pypylog[7][1]# nested action
    assert filtered_pypylog[6][1] == filtered_pypylog[7][1]# not nested action
    assert filtered_pypylog[6][2] != filtered_pypylog[7][2]# action start => action end

def test_create_pypylog_marker():
    pypylog_path = os.path.join(os.path.dirname(__file__), "profiles/pystone.pypylog")
    t = Thread()
    initial_pypylog = parse_pypylog(pypylog_path)
    rescaled_pypylog = rescale_pypylog(initial_pypylog[:1000], 10000000)
    filtered_pypylog = filter_top_level_logs(rescaled_pypylog[:20])
    t.create_pypylog_marker(filtered_pypylog)
    assert t.markers[0] == [0, 10, 1]#gc or jit
    assert t.markers[1] == [11, 19, 0]#interp
    assert t.markers[2] == [20, 30, 2]#gc or jit
    assert t.markers[3] == [31, 39, 0]#interp

def test_get_unused_tid():
    c = Converter()
    c.threads[2] = Thread()
    c.threads[7] = Thread()
    c.threads[17] = Thread()
    unused_tid = c.get_unused_tid()
    assert unused_tid == 1

def test_add_pypylog_sample():
    c = Converter()
    thread = Thread()
    logname = "gc_dummy"
    logtime_start = 7
    logtime_end = 17
    c.add_pypylog_sample(thread, logname, logtime_start, logtime_end)
    samples = thread.samples
    assert samples[0] == [0, 7]
    assert samples[1] == [0, 17]

def test_add_pypylog_interp_sample():
    c = Converter()
    thread = Thread()
    logtime_end = 17
    next_logtime_start = 117
    c.add_pypylog_interp_sample(thread, logtime_end, next_logtime_start)
    samples = thread.samples
    stacktable = thread.stacktable
    assert samples[0] == [0, 17]
    assert samples[1] == [0, 117]
    assert stacktable[0] == [0, None, CATEGORY_INTERPRETER]

def test_walk_pypylog():
    c = Converter()
    test_pypylog = [
        [7, "gc_example_action_a", True, 0],
        [17, "gc_example_action_a", False, 0]
    ]
    c.walk_pypylog(test_pypylog)
    t = c.threads[7]
    stringarray = t.stringarray
    assert stringarray[0] == "interpreter"
    assert stringarray[1] == "gc_example_action_a"
    
def test_dumps_vmprof_without_pypylog():
    vmprof_path = os.path.join(os.path.dirname(__file__), "profiles/vmprof_cpuburn.prof")
    pypylog_path = None
    times = None
    jsonstr, _ = convert_stats_with_pypylog(vmprof_path, pypylog_path, times)
    profile = json.loads(jsonstr)
    samples = profile["threads"][0]["samples"] 
    markers = profile["threads"][0]["markers"]
    assert len(samples["stack"]) == 5551
    assert markers["data"] == []

def test_dumps_vmprof_with_pypylog():
    vmprof_path = os.path.join(os.path.dirname(__file__), "profiles/vmprof_cpuburn.prof")
    pypylog_path = os.path.join(os.path.dirname(__file__), "profiles/pystone.pypylog")
    times = (0, 42.368387)
    jsonstr, _ = convert_stats_with_pypylog(vmprof_path, pypylog_path, times)
    profile = json.loads(jsonstr)
    samples = profile["threads"][0]["samples"] 
    stringarray = profile["threads"][1]["stringArray"]
    assert len(samples["stack"]) == 5551
    assert stringarray[0] == "interpreter"
    assert stringarray[1] == "gc-set-nursery-size"

def test_write_file_dict():
    file_dict = {
        "file_a": "duck.py",
        "file_b": "goose.prof"
    }
    zip_path = "tmpzip/examplezip.zip"
    dict_path = None
    json_dict = None
    
    os.mkdir("tmpzip")

    with ZipFile(zip_path, "w") as examplezip:# create zip file and write file_dict
        write_file_dict(file_dict, examplezip)

    with ZipFile(zip_path, "r") as examplezip:
        dict_path = examplezip.extract("dict.json")# extract file_dict

    with open(dict_path, "r") as exampledict:# load file_dict
        json_dict = json.loads(exampledict.read())

    os.remove(zip_path)# cleanup
    os.remove(dict_path)
    os.rmdir("tmpzip")

    assert not os.path.exists("tmp")
    assert json_dict["file_a"] == file_dict["file_a"]
    assert json_dict["file_b"] == file_dict["file_b"]

def test_save_zip():
    file_dict = {
        "duck.py": "duck.py",
        "/home/users/me/goose.prof": "goose.prof",
        "C:\\users\\myself\\frog.jitlog": "frog.jitlog"
    }

    with open(file_dict["duck.py"], "w") as file_a:# create dummy files
        file_a.write("print(\"quack\")")

    with open(file_dict["/home/users/me/goose.prof"], "w") as file_b:# create dummy files
        file_b.write("0x7")

    with open(file_dict["C:\\users\\myself\\frog.jitlog"], "w") as file_c:# create dummy files
        file_c.write("0x17")

    extract_folder = "extracted"
    zip_folder = "tmpzip"
    zip_path = zip_folder + "/examplezip.zip"
   
    os.mkdir(zip_folder)

    save_zip(zip_path, file_dict)# save dummy files in zip with dict

    os.remove(file_dict["duck.py"])# remove local dummy files
    os.remove(file_dict["/home/users/me/goose.prof"])
    os.remove(file_dict["C:\\users\\myself\\frog.jitlog"])

    os.mkdir(extract_folder)

    with ZipFile(zip_path, "r") as examplezip:# open zip extract dict
        dict_path = examplezip.extract("dict.json", extract_folder)

    with open(dict_path, "r") as exampledict:# read file_dict
        json_dict = json.loads(exampledict.read())
    
    new_file_paths = {}
    with ZipFile(zip_path, "r") as examplezip:# open zip extract files listed in file_dict
        for path in list(json_dict.keys()):
            filename = json_dict[path]
            new_file_paths[path] = examplezip.extract(filename, extract_folder)
 
    filecontent = {}
    for path in list(new_file_paths.keys()):# load content of extracted files 
        with open(new_file_paths[path], "r") as file:
            filecontent[path] = file.read()

    os.remove(zip_path)# cleanup
    os.rmdir(zip_folder)
    os.remove(dict_path)
    for file in new_file_paths:
        os.remove(new_file_paths[file])
    os.rmdir(extract_folder)

    assert filecontent["duck.py"] == "print(\"quack\")"
    assert filecontent["/home/users/me/goose.prof"] == "0x7"
    assert filecontent["C:\\users\\myself\\frog.jitlog"] == "0x17"


def test_load_zip_dict():
    file_dict = {
        "duck.py": "duck.py",
        "/home/users/me/goose.prof": "goose.prof",
        "C:\\users\\myself\\frog.jitlog": "frog.jitlog"
    }

    zip_folder = "tmpzip"
    zip_path = os.path.join(zip_folder, "examplezip.zip")
   
    os.mkdir(zip_folder)

    with ZipFile(zip_path, "w") as examplezip:# create zip file and write file_dict
        write_file_dict(file_dict, examplezip)
    
    zip_dict = load_zip_dict(zip_path, zip_folder)

    os.remove(zip_path)# cleanup
    os.rmdir(zip_folder)

    assert zip_dict == file_dict
    
def test_extract_files():
    file_dict = {
        "duck.py": "duck.py",
        "/home/users/me/goose.prof": "goose.prof",
        "C:\\users\\myself\\frog.jitlog": "frog.jitlog"
    }

    with open(file_dict["duck.py"], "w") as file_a:# create dummy files
        file_a.write("print(\"quack\")")

    with open(file_dict["/home/users/me/goose.prof"], "w") as file_b:# create dummy files
        file_b.write("0x7")

    with open(file_dict["C:\\users\\myself\\frog.jitlog"], "w") as file_c:# create dummy files
        file_c.write("0x17")

    extract_folder = "extracted"
    zip_folder = "tmpzip"
    zip_path = zip_folder + "/examplezip.zip"
   
    os.mkdir(zip_folder)

    save_zip(zip_path, file_dict)# save dummy files in zip with dict

    os.remove(file_dict["duck.py"])# remove local dummy files
    os.remove(file_dict["/home/users/me/goose.prof"])
    os.remove(file_dict["C:\\users\\myself\\frog.jitlog"])

    zip_dict = load_zip_dict(zip_path, zip_folder)

    new_file_paths = extract_files(zip_dict, zip_path, extract_folder)

    filecontent = {}
    for path in list(new_file_paths.keys()):# load content of extracted files 
        with open(new_file_paths[path], "r") as file:
            filecontent[path] = file.read()

    os.remove(zip_path)# cleanup
    os.rmdir(zip_folder)
    for file in new_file_paths:
        os.remove(new_file_paths[file])
    os.rmdir(extract_folder)

    assert filecontent["duck.py"] == "print(\"quack\")"
    assert filecontent["/home/users/me/goose.prof"] == "0x7"
    assert filecontent["C:\\users\\myself\\frog.jitlog"] == "0x17"