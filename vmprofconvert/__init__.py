import vmprof
import json
import os
from vmprof.reader import AssemblerCode, JittedCode
from vmprofconvert.processedformat import check_processed_profile
from vmprofconvert.pypylog import parse_pypylog, cut_pypylog, rescale_pypylog, filter_top_level_logs

CATEGORY_PYTHON = 0
CATEGORY_MEMORY = 1
CATEGORY_NATIVE = 2
CATEGORY_JIT = 3
CATEGORY_ASM = 4
CATEGORY_JIT_INLINED = 5
CATEGORY_MIXED = 6
CATEGORY_GC = 7
CATEGORY_INTERPRETER = 8

PPL_TIME = 0
PPL_ACTION = 1
PPL_STARTING = 2
PPL_DEPTH = 3

def convert(path):
    stats = vmprof.read_profile(path)
    c = Converter()
    c.walk_samples(stats)
    return c# return converter instance for testing
    
def convert_vmprof(path):
    c = Converter()
    stats = vmprof.read_profile(path)
    c.walk_samples(stats)
    return c# return converter instance for testing

def convert_stats(path):
    # new function because dumps_vmprof needs stats
    c = Converter()
    stats = vmprof.read_profile(path)
    c.walk_samples(stats)
    return c.dumps_vmprof(stats)

def convert_stats_with_pypylog(vmprof_path, pypylog_path, times):
    #times for cutting of logs after sampling ended
    c = Converter()
    stats = vmprof.read_profile(vmprof_path)
    c.walk_samples(stats)
    if pypylog_path  :
        pypylog = parse_pypylog(pypylog_path)
        if times is not None:
            total_runtime_micros = (times[1] - times[0]) * 1000000
            pypylog = cut_pypylog(pypylog, total_runtime_micros, stats.get_runtime_in_microseconds())
        pypylog = rescale_pypylog(pypylog, stats.get_runtime_in_microseconds())
        c.walk_pypylog(pypylog)
    return c.dumps_vmprof(stats), c.create_path_dict()# json_profile, file path dict

class Converter:
    def __init__(self):
        self.threads = {}
        self.counters = []
        self.libs = []# list of [name, debugname]
        self.libs_positions = {}# key is string
    
    def add_lib(self, name, debugname):
        if name == "-":
            return -1
        key = (name, debugname)
        if key in self.libs_positions:
            return self.libs_positions[key]
        else:
            libs_index = len(self.libs)
            self.libs.append([name, debugname])
            self.libs_positions[key] = libs_index
            return libs_index
        
    def create_path_dict(self):
        path_dict = {}
        for lib in self.libs:
            name, _ = lib
            if os.path.exists(name):
                path_dict[name] = os.path.abspath(name)
        return path_dict
    
    def create_pypylog_marker(self, pypylog, tid):
        self.threads[tid].create_pypylog_marker(pypylog)

    def get_unused_tid(self):
        if len(self.threads) == 0:
            return 7
        lowest_tid = min(list(self.threads.keys())) - 1
        return lowest_tid
    
    def walk_pypylog(self, pypylog):# Problem: tracing[ backend[ backend] backend[ backend] backend[ backend] ....] 
        tid = self.get_unused_tid()
        plthread = None
        if tid not in self.threads:
            plthread = self.threads[tid] = Thread()
            plthread.name = "PyPyLog"
            plthread.tid = tid
        if plthread and pypylog:
            ppl_stack = []
            last_log = None
            last_close_time = -1
            mdiff = pypylog[1][PPL_TIME] - pypylog[0][PPL_TIME]# minimal time intervall to squeeze an interpreter sample in between 
            for i in range(len(pypylog)):
                log = pypylog[i]
                if log[PPL_STARTING]:
                    ppl_stack.append(log)
                else:
                    ppl_stack.append(log)
                    if last_log[PPL_ACTION] == log[PPL_ACTION]: # Only top level actions wanted e.g. A[ B[ B]A] => Sample: A->B not A->B, A
                        self.add_pypylog_sample_from_stack(plthread, ppl_stack)
                        plthread.create_single_pypylog_marker(ppl_stack[-2], ppl_stack[-1])
                        if len(plthread.samples) >= 4:# dont add interp sample at start
                            if ppl_stack[-2][PPL_TIME] - last_close_time >= mdiff:
                                self.add_pypylog_interp_sample(plthread, last_close_time + 1, ppl_stack[-2][PPL_TIME] - 1)
                                # TODO: Add interpreter marker
                    assert log[PPL_ACTION] == ppl_stack[-1][PPL_ACTION] ### TODO: Remove later
                    last_close_time = log[PPL_TIME]
                    ppl_stack.pop()
                    ppl_stack.pop()
                last_log = log
            
    def add_pypylog_sample_from_stack(self, thread, stack_list):
        assert stack_list[-2][PPL_ACTION] == stack_list[-1][PPL_ACTION] ### TODO: Remove later
        frames = []
        categories = []
        for log in stack_list[:-1]:# last frame is double (open + closed)
            if "gc" in log[PPL_ACTION]:
                categories.append(CATEGORY_GC)
            elif "jit" in log[PPL_ACTION]:
                categories.append(CATEGORY_JIT)
            frames.append(thread.add_frame(log[PPL_ACTION], -1, "", categories[-1], -1, -1))
        stackindex = thread.add_stack(frames, categories)
        start_time = stack_list[-2][PPL_TIME]
        end_time =  stack_list[-1][PPL_TIME]
        thread.add_sample(stackindex, start_time)
        thread.add_sample(stackindex, end_time) 

    def add_pypylog_sample(self, thread, logname, logtime_start, logtime_end):
        if "gc" in logname:
            category = CATEGORY_GC
        elif "jit" in logname:
            category = CATEGORY_JIT
        frameindex = thread.add_frame(logname, -1, "", category, -1, -1)
        stackindex = thread.add_stack([frameindex], [category])
        thread.add_sample(stackindex, logtime_start)
        thread.add_sample(stackindex, logtime_end)

    def add_pypylog_interp_sample(self, thread, logtime_start, logtime_end):
        frameindex = thread.add_frame("interp", -1, "", CATEGORY_INTERPRETER, -1, -1)
        stackindex = thread.add_stack([frameindex], [CATEGORY_INTERPRETER])
        thread.add_sample(stackindex, logtime_start)
        thread.add_sample(stackindex, logtime_end)

    
    def walk_samples(self, stats):
        sampletime = stats.end_time.timestamp() * 1000 - stats.start_time.timestamp() * 1000
        sampletime /= len(stats.profiles)
        category_dict = {}
        category_dict["py"] = CATEGORY_PYTHON
        category_dict["n"] = CATEGORY_NATIVE
        for i, sample in enumerate(stats.profiles):# 604 readmbox 601-604 stats.profiles[601:604] [stats.profiles[601],stats.profiles[603]]
            frames = []
            categorys = []
            stack_info, _, tid, memory = sample
            if tid in self.threads:
                thread = self.threads[tid]
            else:
                thread = self.threads[tid] = Thread() 
                thread.tid = tid
                thread.name = "Thread " + str(len(self.threads) - 1)# Threads seem to need different names
            if stats.profile_lines:
                indexes = range(0, len(stack_info), 2)
            else:
                indexes = range(len(stack_info))
            #indexes = indexes[:22] # 22
            #print()
            for j in indexes:
                addr_info = stats.get_addr_info(stack_info[j])
                #print(addr_info, stack_info[j].__class__)
                #remove jit frames # quick fix 
                if len(categorys) != 0:
                    if not isinstance(stack_info[j], AssemblerCode) and categorys[-1] == CATEGORY_JIT:
                        frames.pop()
                        categorys.pop()
                if isinstance(stack_info[j], JittedCode):
                    frames.append(self.add_jit_frame(thread, categorys, addr_info, frames))
                elif isinstance(stack_info[j], AssemblerCode):
                    self.check_asm_frame(categorys, stack_info[j], thread, frames[-1])
                elif addr_info is None: # Class NativeCode isnt used
                    #pass
                    categorys.append(CATEGORY_NATIVE)
                    frames.append(self.add_native_frame(thread, stack_info[j]))                   
                elif isinstance(stack_info[j], int): 
                    categorys.append(category_dict[addr_info[0]])  
                    frames.append(self.add_vmprof_frame(addr_info, thread, stack_info, stats.profile_lines,categorys[-1], j))
                   
            stackindex = thread.add_stack(frames, categorys)
            thread.add_sample(stackindex, i * sampletime)
            if stats.profile_memory == True:
                self.counters.append([i * sampletime, memory * 1000])

    def add_vmprof_frame(self, addr_info, thread, stack_info, lineprof, category, j):# native or python frame
        funcname = addr_info[1]
        funcline = addr_info[2]
        filename = addr_info[3]
        lib_index = self.add_lib(filename, funcname)
        if lineprof:
            return thread.add_frame(funcname, int(-1 * stack_info[j + 1]), filename, category, lib_index, -1)# vmprof python line indexes are negative
        else:
            return thread.add_frame(funcname, funcline, filename, category, lib_index, -1)

    def add_jit_frame(self, thread, categorys, addr_info, frames):
        funcname = addr_info[1]
        filename = addr_info[3]
        last_funcname, last_filename = self.get_last_func_file(thread, frames) 
        
        if len(categorys) > 0 and categorys[-1] == 0 and last_filename == filename and last_funcname == funcname:# if last frame is py and current is jit and both have the same function => replace with mixed frame
            frames.pop()
            categorys.pop()
            categorys.append(CATEGORY_MIXED)
        else:
            categorys.append(CATEGORY_JIT)
        if addr_info is not None and int(addr_info[2]) >= 0:
            lib_index = self.add_lib(filename, funcname)
            return thread.add_frame(funcname, int(addr_info[2]), filename, categorys[-1], lib_index, -1)# vmprof jit line indexes are positive
        else:
            return thread.add_frame(funcname, -1, filename, categorys[-1], -1, -1)

    def add_native_frame(self, thread, stack_info):
        funcname = stack_info
        filename = ""
        frameindex = thread.add_frame(funcname, -1, filename, CATEGORY_NATIVE, -1, -1)
        return frameindex
    
    def check_asm_frame(self, categorys, stack_info, thread, last_frame):
        if len(categorys) > 0 and categorys[-1] == 3:# if last frame is jit and current is asm => replace with inline jit frame
            categorys.pop()
            categorys.append(CATEGORY_JIT_INLINED)
            last_nativesymbol_index = thread.frametable[last_frame][1]
            thread.nativesymbols[last_nativesymbol_index][2] = stack_info
        else:# asm disabled
            pass
            #categorys.append(CATEGORY_ASM)#asm
            #frames.append(thread.add_frame(stack_info[j], -1, ""))

    def get_last_func_file(self, thread, frames):
        if len(frames) == 0:
            return "", ""
        last_func_index = thread.frametable[frames[-1]][0]
        last_funcname_index = thread.functable[last_func_index][0]
        last_filename_index = thread.functable[last_func_index][1]
        last_funcname = thread.stringarray[last_funcname_index]
        last_filename = thread.stringarray[last_filename_index]
        return last_funcname, last_filename

    def dumps_static(self):
        processed_profile = {}
        processed_profile["meta"] = self.dump_static_meta()
        processed_profile["libs"] = []
        processed_profile["pages"] = []
        processed_profile["counters"] = []
        processed_profile["threads"] = self.dump_threads()
        check_processed_profile(processed_profile)
        return json.dumps(processed_profile)
    
    def dumps_vmprof(self, stats):
        processed_profile = {}
        processed_profile["meta"] = self.dump_vmprof_meta(stats)
        processed_profile["libs"] = self.dump_libs()
        processed_profile["pages"] = []
        if(stats.profile_memory):
            processed_profile["counters"] = [self.dump_counters()]
        else:
            processed_profile["counters"] = []
        processed_profile["threads"] = self.dump_threads()
        check_processed_profile(processed_profile)
        return json.dumps(processed_profile)
    
    def dump_libs(self):
        liblist = []
        for lib in self.libs:
            name, debugname = lib
            liblist.append(
                {
                    "name": name,
                    "path": name,
                    "debugName": debugname,
                    "debugPath": name,
                    "arch": ""
                }
            )
        return liblist
    
    def dump_threads(self):
        return [thread.dump_thread()for thread in list(self.threads.values())] 
    
    def dump_static_meta(self):
        static_meta = {}
        static_meta["interval"] = 0.4
        static_meta["startTime"] = 1477063882018.4387
        static_meta["abi"] = "x86_64-gcc3"
        static_meta["oscpu"] = "Intel Mac OS X 10.12"
        static_meta["platform"] = "Macintosh"
        static_meta["processType"] = 0
        static_meta["stackwalk"] = 1
        static_meta["debug"] = False
        static_meta["version"] = 27
        static_meta["importedFrom"] = "VMProf"
        static_meta["categories"] = self.dump_categorys()
        static_meta["preprocessedProfileVersion"] = 47
        static_meta["symbolicated"] = True
        static_meta["markerSchema"] = []
        return static_meta

    def dump_vmprof_meta(self, stats):
        vmprof_meta = {}
        ms_for_sample = int(stats.get_runtime_in_microseconds() / len(stats.profiles))
        
        vmprof_meta["interval"] = ms_for_sample * 0.000001# seconds
        vmprof_meta["startTime"] = stats.start_time.timestamp() * 1000
        vmprof_meta["shutdownTime"] = stats.end_time.timestamp() * 1000
        vmprof_meta["abi"] = stats.interp # interpreter

        os   = stats.getmeta("os","default os")
        bits = stats.getmeta("bits","64")
        osdict = {"linux": "x11", "win64": "Windows", "win32": "Windows", "mac": "Macintosh"}# vmprof key for mac may be wrong
        
        vmprof_meta["oscpu"] = f"{osdict[os]} {bits}bit"
        vmprof_meta["platform"] = osdict[os]
        vmprof_meta["processType"] = 0
        vmprof_meta["stackwalk"] = 1
        vmprof_meta["debug"] = False
        vmprof_meta["version"] = 27
        vmprof_meta["importedFrom"] = "VMProf"
        vmprof_meta["categories"] = self.dump_categorys()
        vmprof_meta["preprocessedProfileVersion"] = 47
        vmprof_meta["symbolicated"] = True
        vmprof_meta["markerSchema"] = []
        
        return vmprof_meta
    
    def dump_categorys(self):
        categorys = []
        categorys.append(
            {
                "name": "Python",
                "color": "yellow",
                "subcategories": [
                    "Other"
                ]
            }
        )
        categorys.append(
            {
                "name": "Memory",
                "color": "red",
                "subcategories": [
                    "Other"
                ]
            }
        )    
        categorys.append(
            {
                "name": "Native",
                "color": "lightblue",
                "subcategories": [
                    "Other"
                ]
            }
        )    
        categorys.append(
            {
                "name": "JIT",
                "color": "purple",
                "subcategories": [
                    "Other"
                ]
            }
        )    
        categorys.append(
            {
                "name": "ASM",
                "color": "blue",
                "subcategories": [
                    "Other"
                ]
            }
        )
        categorys.append(
            {
                "name": "JIT(Inlined)",
                "color": "purple",
                "subcategories": [
                    "Other"
                ]
            }
        )   
        categorys.append(
            {
                "name": "Mixed",
                "color": "orange",
                "subcategories": [
                    "Other"
                ]
            }
        )
        categorys.append(
            {
                "name": "Garbage Collection",
                "color": "green",
                "subcategories": [
                    "Other"
                ]
            }
        )
        categorys.append(
            {
                "name": "Interpreter",
                "color": "yellow",
                "subcategories": [
                    "Other"
                ]
            }
        )
        return categorys
           
    def dump_counters(self):
        counter = {}
        counter["name"] = "Memory"
        counter["category"] = "Memory"
        counter["description"] = "Amount of allocated memory"
        counter["pid"] = "51580"
        counter["mainThreadIndex"] = 0
        memory_in_alloc_form =  self.get_mem_allocations()
        counter["sampleGroups"] = [
            {
                "id": 0,
                "samples": {
                     "length": len(memory_in_alloc_form),
                     "time": [mem[0] for mem in memory_in_alloc_form],
                     "count": [mem[1] for mem in memory_in_alloc_form]
                }
            }
        ]
        return counter
    
    def get_mem_allocations(self):
        mem_diff = [self.counters[0],self.counters[0]]# memory wont show up without two non zero samples
        current_mem = mem_diff[0][1]
        for ctr in self.counters[1:len(self.counters) - 1 ]:
            mem_diff.append([ctr[0], (current_mem - ctr[1])])
            current_mem = ctr[1]
        return mem_diff


class Thread:
    def __init__(self):
        self.stringarray = []
        self.stringarray_positions = {}
        self.stacktable = []# list of [frameindex, stacktableindex_or_None, category] cat{0 = py, 1 = mem, 2 = native, 3 = jit, 4 = asm, 5 =  jit_inline, 6 = mixed}
        self.stacktable_positions = {}
        self.functable = []# list of [stringtable_index, stringtable_index, int, resource_index] funcname, filename, line  line == -1 if profile_lines == False, resource_index
        self.funtable_positions = {}
        self.frametable = []# list of [functable_index, nativesymbol_index, line]   
        self.frametable_positions = {}# key is string
        self.samples = []# list of [stackindex, time in ms], no need for sample_positions
        self.nativesymbols = []# list of [libindex, stringindex, addr]
        self.nativesymbols_positions = {}# key is (libindex, string)
        self.resourcetable = []# list of [libindex, stringindex]
        self.resourcetable_positions = {}# key is (libindex, stringindex)
        self.markers = []# list of [startime, endtime, stringindex]

    def create_pypylog_marker(self, pypylog):
        interperter_string_id = self.add_string("interpreter")
        for i in range(int(len(pypylog)/2)):
            start_log = pypylog[2*i]
            stop_log = pypylog[2*i+1]
            starttime = start_log[0]
            endtime = stop_log[0]
            name = start_log[1]
            st_id = self.add_string(name)
            self.add_marker(starttime, endtime, st_id)
            if i < ((len(pypylog)/2) - 2):
                next_log = pypylog[2 * i + 2]
                next_logtime_start = next_log[0]
                if abs(endtime - next_logtime_start) > 2:
                    self.add_marker(endtime + 1, next_logtime_start - 1, interperter_string_id)

    def create_single_pypylog_marker(self, start_log, stop_log):
        starttime = start_log[PPL_TIME]
        endtime = stop_log[PPL_TIME]
        name = start_log[PPL_ACTION]
        st_id = self.add_string(name)
        self.add_marker(starttime, endtime, st_id)
            
    def add_marker(self, starttime, endtime, stringtable_index):
        self.markers.append([starttime, endtime, stringtable_index])

    def add_string(self, string):
        if string in self.stringarray_positions:
            return self.stringarray_positions[string]
        else:
            result = len(self.stringarray)
            self.stringarray.append(string)
            self.stringarray_positions[string] = result
            return result
        
    def add_stack(self, stack, categorys):
        #stack is a list of frametable indexes
        if not stack:
            return None
        else:
            top = stack[-1]
            rest = stack[:-1]
            top_category = categorys[-1]
            rest_categorys = categorys[:-1]
            rest_index = self.add_stack(rest, rest_categorys)
            key = (top, rest_index, top_category)
            if key in self.stacktable_positions:
                return self.stacktable_positions[key]
            else:
                result = len(self.stacktable)
                self.stacktable.append([top, rest_index, top_category])
                self.stacktable_positions[key] = result
                return result
            
    def add_func(self, func, file, line, category, libindex):
        key = (func, file, line, category)
        if key in self.funtable_positions:
            return self.funtable_positions[key]
        else:
            stringtable_index_func = self.add_string(func)
            stringtable_index_file = self.add_string(file)
            resource_index = self.add_resource(libindex, stringtable_index_func)
            result = len(self.functable)
            self.functable.append([stringtable_index_func, stringtable_index_file, line, resource_index])
            self.funtable_positions[key] = result
            return result
            
    def add_frame(self, funcname, line, file, category, libindex, addr):
        key = (funcname, line, category)
        if key in self.frametable_positions:
            return self.frametable_positions[key]
        else:
            functable_index = self.add_func(funcname, file, line, category, libindex)
            frametable_index = len(self.frametable)
            nativesymbol_index = self.add_nativesymbol(libindex, funcname, addr)
            self.frametable.append([functable_index, nativesymbol_index, line])
            self.frametable_positions[key] = frametable_index
            return frametable_index
        
    def add_sample(self, stackindex, time):
        self.samples.append([stackindex, time]) # stackindex, ms since starttime
    
    def add_nativesymbol(self, libindex, funcname, addr):
        if libindex == -1:
            return -1
        key = (libindex, funcname, addr)
        if key in self.nativesymbols_positions:
            return self.nativesymbols_positions[key]
        else:
            funcname_index = self.add_string(funcname)
            nativesymbol_index = len(self.nativesymbols)
            self.nativesymbols.append([libindex, funcname_index, addr])
            self.nativesymbols_positions[key] = nativesymbol_index
            return nativesymbol_index
    
    def add_resource(self, libindex, stringindex):
        if libindex == -1:
            return -1
        key = (libindex, stringindex)
        if key in self.resourcetable_positions:
            return self.resourcetable_positions[key]
        else:
            resource_index = len(self.resourcetable)
            self.resourcetable.append([libindex, stringindex])
            self.resourcetable_positions[key] = resource_index
            return resource_index
    
    def dump_thread(self):
        thread = {}
        thread["name"] = self.name
        thread["isMainThread"] = False
        thread["processType"] = "default"
        thread["processName"] = "Parent Process"
        thread["processStartupTime"] = 0
        thread["processShutdownTime"] = None
        thread["registerTime"] = 23.841461000000002
        thread["unregisterTime"] = None
        thread["tid"] = self.tid
        thread["pid"] = "51580"
        thread["markers"] = self.dump_markers()
        thread["nativeSymbols"] = self.dump_nativesymbols()
        thread["frameTable"] = self.dump_frametable()
        thread["funcTable"] = self.dump_functable()
        thread["resourceTable"] = self.dump_resourcetable()
        thread["stackTable"] = self.dump_stacktable()
        thread["samples"] = self.dump_samples()
        thread["stringArray"] = self.dump_stringarray()
        return thread
    
    def dump_markers(self):
        markers = {}
        markers["data"] = [{"type": "PyPyLog"} for _ in self.markers]
        markers["name"] = [m[2] for m in self.markers]
        markers["startTime"] = [m[0] for m in self.markers]
        markers["endTime"] = [m[1] for m in self.markers]
        markers["phase"] = [1 for _ in self.markers]
        markers["category"] = [7 for _ in self.markers]
        markers["length"] = len(self.markers)
        return markers
 
    def dump_resourcetable(self):
        resourcetable = {}
        resourcetable["lib"] = [nsym[0] for nsym in self.resourcetable]
        resourcetable["name"] = [nsym[1] for nsym in self.resourcetable]
        resourcetable["host"] = [None for _ in self.resourcetable]
        resourcetable["type"] = [1 for _ in self.resourcetable]
        resourcetable["length"] = len(self.resourcetable)
        return resourcetable
    
    def dump_nativesymbols(self):
        nativesymbols = {}
        nativesymbols["libIndex"] = [nsym[0]for nsym in self.nativesymbols]
        nativesymbols["address"] = [nsym[2] for nsym in self.nativesymbols]
        nativesymbols["name"] = [nsym[1]for nsym in self.nativesymbols]
        nativesymbols["functionSize"] = [None for _ in self.nativesymbols]
        nativesymbols["length"] = len(self.nativesymbols)
        return nativesymbols

    def dump_frametable(self):
        ftable = {}
        ftable["address"] = [-1 for _ in self.frametable]
        ftable["inlineDepth"] = [0 for _ in self.frametable]
        ftable["category"] = [0 for _ in self.frametable]
        ftable["subcategory"] = [None for _ in self.frametable]
        ftable["func"] = [frame[0] for frame in self.frametable]
        ftable["innerWindowID"] = [0 for _ in self.frametable]
        ftable["nativeSymbol"] = [frame[1] for frame in self.frametable]
        ftable["line"] = self.get_frametable_lines()
        ftable["length"] = len(self.frametable)
        return ftable
    
    def get_frametable_lines(self):
        lines = []
        for frame in self.frametable:
            if frame[2] == -1:
                lines.append(None)
            else:
                lines.append(int(frame[2]))
        return lines
    
    def dump_functable(self):
        ftable = {}
        ftable["isJS"] = [False for _ in self.functable]
        ftable["relevantForJS"] = [False for _ in self.functable]
        ftable["name"] = [func[0] for func in self.functable]
        ftable["resource"] = [func[3] for func in self.functable]
        linenumbers, filenames = self.get_processed_filelines()
        ftable["fileName"] = filenames
        ftable["lineNumber"] = linenumbers
        ftable["columnNumber"] = [None for _ in self.functable]
        ftable["length"] = len(self.functable)
        return ftable

    def dump_stacktable(self):
        stable = {}
        stable["frame"] = [stack[0] for stack in self.stacktable]
        stable["category"] = [stack[2] for stack in self.stacktable]
        stable["subcategory"] = [None for _ in self.stacktable]
        stable["prefix"] = [stack[1] for stack in self.stacktable]
        stable["length"] = len(self.stacktable)
        return stable
    
    def dump_samples(self):
        samples = {}
        samples["stack"] = [sample[0] for sample in self.samples]
        samples["time"] = [sample[1] for sample in self.samples]
        samples["eventDelay"] = [7 for _ in self.samples]
        samples["weightType"] = "samples"
        samples["weight"] = None
        samples["length"] = len(self.samples)
        return samples
    
    def dump_stringarray(self):
        return [str(string) for string in self.stringarray]
    
    def get_processed_filelines(self):
        linenumbers = []
        filenames = []
        for func in self.functable:
            if self.stringarray[func[1]] == "-":
                linenumbers.append(None)
            elif func[2] == -1:
                linenumbers.append(None)
            else:
                linenumbers.append(int(func[2]))

        for func in self.functable:
            if self.stringarray[func[1]] == "-":
                filenames.append(None)
            else:
                filenames.append(func[1])
        
        return linenumbers, filenames
