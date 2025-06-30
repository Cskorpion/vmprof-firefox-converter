import vmprof
import json
import os
import sys
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
CATEGORY_GC_MINOR_TENURED = 9
CATEGORY_GC_MINOR_DIED = 10

# Copied from vmprof/reader.py
VMPROF_VERSION_BASE = 0
VMPROF_VERSION_THREAD_ID = 1
VMPROF_VERSION_TAG = 2
VMPROF_VERSION_MEMORY = 3
VMPROF_VERSION_MODE_AWARE = 4
VMPROF_VERSION_DURATION = 5
VMPROF_VERSION_TIMESTAMP = 6
VMPROF_VERSION_SAMPLE_TIMEOFFSET = 7

PPL_TIME = 0
PPL_ACTION = 1
PPL_STARTING = 2
PPL_DEPTH = 3

PYPY_GC_STATE_SCANNING = 'SCANNING'
PYPY_GC_STATE_MARKING = 'MARKING'
PYPY_GC_STATE_SWEEPING = 'SWEEPING'
PYPY_GC_STATE_FINALIZING = 'FINALIZING'
# from pypy/.../incminimark.py
PYPY_GC_STATES = ['SCANNING', 'MARKING', 'SWEEPING', 'FINALIZING']
PYPY_GC_STATE_DICT = {v:k for k, v in enumerate(PYPY_GC_STATES)}

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
    if pypylog_path:
        pypylog = parse_pypylog(pypylog_path)
        if times is not None:
            total_runtime_micros = (times[1] - times[0]) * 1000000
            pypylog = cut_pypylog(pypylog, total_runtime_micros, stats.get_runtime_in_microseconds())
        pypylog = rescale_pypylog(pypylog, stats.get_runtime_in_microseconds())
        c.walk_pypylog(pypylog)
    return c.dumps_vmprof(stats), c.create_path_dict()# json_profile, file path dict

def convert_gc_stats_with_pypylog(vmprof_path, pypylog_path=None, times=None):
    #times for cutting of logs after sampling ended
    c = Converter()
    stats = vmprof.read_profile(vmprof_path)
    c.walk_samples(stats)
    #c.walk_gc_samples(stats)
    #c.walk_gc_obj_info(stats)
    c.get_type_of_gc_stats(stats)
    c.walk_gc_samples_w_obj_info(stats)
    c.create_gc_thread_minor_marker(stats)
    c.create_gc_major_marker(stats)
    #c.create_gc_minor_marker(stats)
    if pypylog_path:
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
        self.gc_sampled_threads = {}
        self.gc_stat_types = [] # Type of gc stats the current profile contains: e.g. ["vmRSS", "total_size_of_arensas",...]
        self.gc_stat_types_dict = {} # Type of gc stats the current profile contains: e.g. ["vmRSS", "total_size_of_arensas",...]
        self.counters = {} # contains different memory information: type: [[timestamp, memory in Byte], ...]
        self.libs = []# list of [name, debugname]
        self.libs_positions = {}# key is string
        self.walked_vmrss = False# to only convert vmrss only the first time samples are converted
    
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
    
    def add_counter(self, ctype, data):
        if not ctype in self.counters:
            self.counters[ctype] = []
        self.counters[ctype].append(data)

    def create_gc_minor_marker(self, stats):
        first_timestamp = stats.start_time.timestamp()

        thread = self.gc_sampled_threads[0]

        gc_minor_str_id = thread.add_string("GC Minor")

        for sample in stats.gc_obj_info:
            _, timestamp = sample
            start = (timestamp - first_timestamp) * 1000
            thread.add_marker(start, start + 1, gc_minor_str_id) # TODO need real minor time
    
    def walk_pypylog(self, pypylog):
        tid = self.get_unused_tid()
        plthread = None
        if tid not in self.threads:
            plthread = self.threads[tid] = Thread()
            plthread.name = "PyPyLog"
            plthread.tid = tid
            plthread.marker_schema = "PyPyLog"
        if plthread and pypylog:
            ppl_stack = []
            last_log = None
            last_close_time = -1
            mdiff = pypylog[1][PPL_TIME] - pypylog[0][PPL_TIME]# minimal time interval to squeeze an interpreter sample in between 
            for i in range(len(pypylog)):
                log = pypylog[i]
                if log[PPL_STARTING]:
                    ppl_stack.append(log)
                else:
                    ppl_stack.append(log)
                    if last_log[PPL_ACTION] == log[PPL_ACTION]: # Only top level actions wanted e.g. A[ B[ B]A] => Sample: A->B not A->B, A
                        if len(plthread.samples) >= 2 and ppl_stack[-2][PPL_TIME] - last_close_time >= mdiff:# dont add interp sample at start
                            self.add_pypylog_interp_sample(plthread, last_close_time + 1, ppl_stack[-2][PPL_TIME] - 1)
                            plthread.create_single_pypylog_interpreter_marker(last_close_time + 1, ppl_stack[-2][PPL_TIME] - 1)
                        self.add_pypylog_sample_from_stack(plthread, ppl_stack)
                        plthread.create_single_pypylog_marker(ppl_stack[-2], ppl_stack[-1])
                    last_close_time = log[PPL_TIME]
                    ppl_stack.pop()
                    ppl_stack.pop()
                last_log = log
            
    def add_pypylog_sample_from_stack(self, thread, stack_list):
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

    def get_sample_time(self,stats):
        if "start_time_offset" in stats.meta: # No version in stats TODO: Replace with version check if vmprof supports it
            return float(stats.getmeta("start_time_offset", "0")) * 1000
        else:
            sampletime = stats.end_time.timestamp() * 1000 - stats.start_time.timestamp() * 1000
            return sampletime / len(stats.gc_profiles)
        
    def get_thread_gc_sampled(self, tid):
        """ Get or create the gc_thread for a given tid. 
            Doesnt interfere with 'normal' threads """
        if tid in self.gc_sampled_threads:
            thread = self.gc_sampled_threads[tid]
        else:
            thread = self.gc_sampled_threads[tid] = Thread() 
            thread.tid = tid
            thread.name = "(GC-Sampled) Thread " + str(len(self.gc_sampled_threads) - 1)# Threads seem to need different names
            thread.marker_schema = "Garbage Collection"
        return thread
    
    def walk_samples(self, stats):
        """ Convert all time samples"""
        if not stats.profiles:
            return
        sampletime = self.get_sample_time(stats)

        print("time", sampletime)

        category_dict = {}
        category_dict["py"] = CATEGORY_PYTHON
        category_dict["n"] = CATEGORY_NATIVE
        for i, sample in enumerate(stats.profiles):
            frames = []
            categories = []
            stack_info, _, tid, memory = sample
            if tid in self.threads:
                thread = self.threads[tid]
            else:
                thread = self.threads[tid] = Thread() 
                thread.tid = tid
                thread.name = "(Time-Sampled) Thread " + str(len(self.threads) - 1)# Threads seem to need different names
            if stats.profile_lines:
                indexes = range(0, len(stack_info), 2)
            else:
                indexes = range(len(stack_info))

            for j in indexes:
                addr_info = stats.get_addr_info(stack_info[j])
                #remove jit frames # quick fix 
                if len(categories) != 0:
                    if not isinstance(stack_info[j], AssemblerCode) and categories[-1] == CATEGORY_JIT:
                        frames.pop()
                        categories.pop()
                if isinstance(stack_info[j], JittedCode):
                    frames.append(self.add_jit_frame(thread, categories, addr_info, frames))
                elif isinstance(stack_info[j], AssemblerCode):
                    self.check_asm_frame(categories, stack_info[j], thread, frames[-1])
                elif addr_info is None: # Class NativeCode isnt used
                    #pass
                    categories.append(CATEGORY_NATIVE)
                    frames.append(self.add_native_frame(thread, stack_info[j]))                   
                elif isinstance(stack_info[j], int): 
                    categories.append(category_dict[addr_info[0]]) 
                    frames.append(self.add_vmprof_frame(addr_info, thread, stack_info, stats.profile_lines, categories[-1], j))
                   
            stackindex = thread.add_stack(frames, categories)
            timestamp = i * sampletime
            if "start_time_offset" in stats.meta: 
                timestamp = 1000 * stats.profiles[i][1] - sampletime# timestamp field in new version  
            thread.add_sample(stackindex, timestamp)
            if stats.profile_memory == True and not self.walked_vmrss:
                self.add_counter("vmRSS", [timestamp, memory * 1000])

        self.walked_vmrss = True



    def walk_gc_samples(self, stats):
        """ Convert all gc samples"""
        if not hasattr(stats, "gc_profiles") or len(stats.gc_profiles) == 0: return

        sampletime = self.get_sample_time(stats)
        sample_allocated_bytes = int(stats.getmeta("sample_allocated_bytes", "0"))

        category_dict = {}
        category_dict["py"] = CATEGORY_PYTHON
        category_dict["n"] = CATEGORY_NATIVE
        for i, sample in enumerate(stats.gc_profiles):
            frames = []
            categories = []
            stack_info, _, tid, memory = sample
            if tid in self.gc_sampled_threads:
                thread = self.gc_sampled_threads[tid]
            else:
                thread = self.gc_sampled_threads[tid] = Thread() 
                thread.tid = tid
                thread.name = "(GC-Sampled) Thread " + str(len(self.gc_sampled_threads) - 1)# Threads seem to need different names
            if stats.profile_lines:
                indexes = range(0, len(stack_info), 2)
            else:
                indexes = range(len(stack_info))

            for j in indexes:
                addr_info = stats.get_addr_info(stack_info[j])
                #remove jit frames # quick fix 
                if len(categories) != 0:
                    if not isinstance(stack_info[j], AssemblerCode) and categories[-1] == CATEGORY_JIT:
                        frames.pop()
                        categories.pop()
                if isinstance(stack_info[j], JittedCode):
                    frames.append(self.add_jit_frame(thread, categories, addr_info, frames))
                elif isinstance(stack_info[j], AssemblerCode):
                    self.check_asm_frame(categories, stack_info[j], thread, frames[-1])
                elif addr_info is None: # Class NativeCode isnt used
                    #pass
                    categories.append(CATEGORY_NATIVE)
                    frames.append(self.add_native_frame(thread, stack_info[j]))                   
                elif isinstance(stack_info[j], int): 
                    categories.append(category_dict[addr_info[0]])  
                    frames.append(self.add_vmprof_frame(addr_info, thread, stack_info, stats.profile_lines,categories[-1], j))
                   

            stackindex = thread.add_stack(frames, categories)
            if "start_time_offset" in stats.meta: 
                timestamp = 1000 * stats.gc_profiles[i][1] - sampletime# timestamp field in new version  
            else:
                timestamp = i * sampletime

            thread.add_sample(stackindex, timestamp)
            thread.add_allocation(stackindex, timestamp, sample_allocated_bytes)
            
            if stats.profile_memory == True and not self.walked_vmrss:
                self.add_counter("vmRSS", [timestamp, memory * 1000])
        self.walked_vmrss = True

    def get_next_sampled_object(self, stats):
        """ Iterate thorugh the obj info stacks and return next sampled obj with timestamp and previous timestamp """
        for obj_info_stack in stats.gc_obj_info:
            stack, timestamp = obj_info_stack
            split = len(self.gc_stat_types)
            stack, gc_stats = stack[split:], stack[:split]
            for sampled_object in stack:
                yield (sampled_object, timestamp, gc_stats[::-1])# order of stats is inverted

    def get_type_of_gc_stats(self, stats):
        """ read what type of stats we recorded from PyPy's gc on a minor collection"""
        i = 0
        gc_stat = stats.getmeta("gc_stats__" + str(i), None)
        self.gc_stat_types = []
        self.gc_stat_types_dict = {}
        while gc_stat != None:
            self.gc_stat_types.append(gc_stat)
            self.gc_stat_types_dict[gc_stat] = i
            i += 1
            gc_stat = stats.getmeta("gc_stats__" + str(i), None)
        
    def walk_gc_samples_w_obj_info(self, stats):
        # New function for gc_samples and obj info.
        # Idea: have one extra top frame that tells what kind of object triggerred the sample
        if not hasattr(stats, "gc_profiles") or len(stats.gc_profiles) == 0: return

        obj_count = 0
        for obj_info_stack in stats.gc_obj_info:
            stack, timestamp = obj_info_stack
            obj_count += len(stack) - len(self.gc_stat_types)

        print( f"gc-samples: {len(stats.gc_profiles)}, objects {obj_count}")
        #assert len(stats.gc_profiles) == obj_count, f"gc-samples: {len(stats.gc_profiles)}, objects {obj_count}"

        sampletime = self.get_sample_time(stats)# start 'timestamp' when sampling started
        sample_allocated_bytes = int(stats.getmeta("sample_allocated_bytes", "0"))

        category_dict = {"py": CATEGORY_PYTHON,
                         "n":  CATEGORY_NATIVE}
        
        obj_info_getter = self.get_next_sampled_object(stats)

        last_sample_timestamp = -7 
        for i, sample in enumerate(stats.gc_profiles):
            frames, categories = [], []
            stack_info, sample_timestamp, tid, memory = sample

            # correctness check: assert that vmprof delivers samples in correct order
            assert last_sample_timestamp <= sample_timestamp, f"order of sample {i-1} and sample {i} is wrong"
            last_sample_timestamp = sample_timestamp

            thread = self.get_thread_gc_sampled(tid)

            if stats.profile_lines:
                indexes = range(0, len(stack_info), 2)
            else:
                indexes = range(len(stack_info))

            for j in indexes:
                addr_info = stats.get_addr_info(stack_info[j])
                #remove jit frames # quick fix 
                if len(categories) != 0:
                    if not isinstance(stack_info[j], AssemblerCode) and categories[-1] == CATEGORY_JIT:
                        frames.pop()
                        categories.pop()
                if isinstance(stack_info[j], JittedCode):
                    frames.append(self.add_jit_frame(thread, categories, addr_info, frames))
                elif isinstance(stack_info[j], AssemblerCode):
                    self.check_asm_frame(categories, stack_info[j], thread, frames[-1])
                elif addr_info is None: # Class NativeCode isnt used
                    #pass
                    categories.append(CATEGORY_NATIVE)
                    frames.append(self.add_native_frame(thread, stack_info[j]))                   
                elif isinstance(stack_info[j], int): 
                    categories.append(category_dict[addr_info[0]])  
                    frames.append(self.add_vmprof_frame(addr_info, thread, stack_info, stats.profile_lines,categories[-1], j))

                   
            if "start_time_offset" in stats.meta: 
                timestamp = 1000 * sample_timestamp - sampletime# stats.gc_profiles[i][1] = seconds => * 1000 for milis
            else:
                timestamp = i * sampletime

            obj_info = next(obj_info_getter, None)
            # If there is obj info add that recorded type as top level frame onto sample stack
            if obj_info:
                obj_info, obj_timestamp, _ = obj_info
                # correctness check: obj info must be recorded at a minor collect AFTER the sample was recorded
                assert sample_timestamp <= obj_timestamp

                survived_minor_gc = bool(obj_info & 1)
                external_malloced = bool(obj_info & 2)

                rpy_type_id = obj_info >> 2
                rpy_type = stats.getmeta("__rtype_" + str(rpy_type_id), "")

                categories.append(CATEGORY_GC_MINOR_TENURED if survived_minor_gc else CATEGORY_GC_MINOR_DIED)
                frames.append(self.add_gc_obj_frame(thread, rpy_type, None, categories[-1]))

            elif len(stats.gc_obj_info) != 0:# sanity: print if we have less obj than samples
                assert False, "ran out of objects"
                #print("no more object info :(")

            stackindex = thread.add_stack(frames, categories)
            thread.add_sample(stackindex, timestamp)
            thread.add_allocation(stackindex, timestamp, sample_allocated_bytes)
            
            #print(stats.profile_memory)
            if stats.profile_memory == True and not self.walked_vmrss:
                self.add_counter("vmRSS", [timestamp, memory * 1000])
        self.walked_vmrss = True

    def create_gc_major_marker(self, stats):
        if not hasattr(stats, "gc_obj_info") or len(stats.gc_obj_info) == 0: return
        if not "gc_state" in self.gc_stat_types_dict: return

        thread = self.get_thread_gc_sampled(0)# TODO:handle gc threads better
        st_id = thread.add_string("Major Collection")
        obj_info_getter = self.get_next_sampled_object(stats)
        first_gc_time = stats.gc_obj_info[0][1] 

        gc_state_index = self.gc_stat_types_dict["gc_state"]

        _, gc_time_start, gc_stats_start = next(obj_info_getter, (None, None, None))
        while gc_time_start:

            # find first state marking
            if gc_stats_start[gc_state_index] != PYPY_GC_STATE_DICT[PYPY_GC_STATE_MARKING]:
                _, gc_time_start, gc_stats_start = next(obj_info_getter, (None, None, None))
                continue

            new_gc_time, gc_stats_next = gc_time_start, gc_stats_start

            # run over stats until we find finalizing
            while gc_stats_next and gc_stats_next[gc_state_index] != PYPY_GC_STATE_DICT[PYPY_GC_STATE_FINALIZING]: 
                _, new_gc_time, gc_stats_next = next(obj_info_getter, (None, None, None))
            
            # run up to last finalizing
            while gc_stats_next and gc_stats_next[gc_state_index] == PYPY_GC_STATE_DICT[PYPY_GC_STATE_FINALIZING]: 
                last_finalizing_time = new_gc_time
                _, new_gc_time, gc_stats_next = next(obj_info_getter, (None, None, None))

            if not gc_stats_next:
                print("no finalizing!")
                return
            
            marker_start = (gc_time_start - first_gc_time) * 1000
            marker_end = (last_finalizing_time - first_gc_time) * 1000
            print("major marker")
            thread.add_marker(marker_start, marker_end, st_id, {"type": "Garbage Collection"})

            gc_time_start, gc_stats_start = gc_stats_next, gc_stats_next


    def create_gc_thread_minor_marker(self, stats):
        if not hasattr(stats, "gc_obj_info") or len(stats.gc_obj_info) == 0: return
        thread = self.get_thread_gc_sampled(0)# TODO:handle gc threads better
        st_id = thread.add_string("Minor Collection")
        obj_info_getter = self.get_next_sampled_object(stats)
        first_gc_time = stats.gc_obj_info[0][1] 

        _, gc_time, gc_stats = next(obj_info_getter, (None, None, None))
        while gc_time:
            marker_time = (gc_time - first_gc_time) * 1000
            data = {"type": "Garbage Collection"}
            for i in range(len(self.gc_stat_types)):
                if self.gc_stat_types[i] == "gc_state":
                    data["gc_state"] = PYPY_GC_STATES[int(gc_stats[i])]  
                elif self.gc_stat_types[i] in ("total_memory_used", "total_size_of_arenas", "VmRSS"):
                    data[self.gc_stat_types[i]] = str(gc_stats[i]) + "B"
                    self.add_counter(self.gc_stat_types[i], [marker_time, gc_stats[i]])

            thread.add_marker(marker_time, marker_time + 0.02, st_id, data)
            _, new_gc_time, gc_stats = next(obj_info_getter, (None, None, None))
            while new_gc_time == gc_time: 
                # we dont want the same minor collection marked multiple times
                _, new_gc_time, gc_stats = next(obj_info_getter, (None, None, None))
            gc_time = new_gc_time

    
    def walk_gc_obj_info(self, stats):
        # New function for gc obj_info.
        # After a minor gc, vmprof will gather information about which objects died and survived 
        # between the last abnd current minor collection.
        if not hasattr(stats, "gc_obj_info") or len(stats.gc_obj_info) == 0: return

        tid = -1

        first_timestamp = stats.start_time.timestamp()

        if tid in self.gc_sampled_threads:
            thread = self.gc_sampled_threads[tid]
        else:
            thread = self.gc_sampled_threads[tid] = Thread() 
            thread.tid = tid
            thread.name = "Minor GC"

        for sample in stats.gc_obj_info:
            frames = []
            categories = []
            stack_info, timestamp = sample

            for j in range(len(stack_info)):
                survived_minor_gc = bool(stack_info[j] & 1)
                rtype_id = stack_info[j] >> 1
                if "__rtype_" + str(rtype_id) in stats.meta:
                    rtype_str = stats.meta["__rtype_" + str(rtype_id)]
                else:
                    rtype_str = ""
                categories.append(CATEGORY_GC_MINOR_TENURED if survived_minor_gc else CATEGORY_GC_MINOR_DIED)
                frames.append(self.add_gc_obj_frame(thread, rtype_str, None, categories[-1]))# Add PyPy type descr here
            stackindex = thread.add_stack(frames, categories)
            thread.add_sample(stackindex, (timestamp - first_timestamp) * 1000)

    def add_gc_obj_frame(self, thread, rpy_name, pypy_name_hint, category):
        lib_index = self.add_lib("rpython", rpy_name)
        return thread.add_frame(rpy_name, -1, "rpython" if pypy_name_hint == None else "pypy", category, lib_index, -1)


    def add_vmprof_frame(self, addr_info, thread, stack_info, lineprof, category, j):# native or python frame
        funcname = addr_info[1]
        funcline = addr_info[2]
        filename = addr_info[3]
        lib_index = self.add_lib(filename, funcname)
        if lineprof:
            return thread.add_frame(funcname, int(-1 * stack_info[j + 1]), filename, category, lib_index, -1)# vmprof python line indexes are negative
        else:
            return thread.add_frame(funcname, funcline, filename, category, lib_index, -1)

    def add_jit_frame(self, thread, categories, addr_info, frames):
        funcname = addr_info[1]
        filename = addr_info[3]
        last_funcname, last_filename = self.get_last_func_file(thread, frames) 
        
        if len(categories) > 0 and categories[-1] == 0 and last_filename == filename and last_funcname == funcname:# if last frame is py and current is jit and both have the same function => replace with mixed frame
            frames.pop()
            categories.pop()
            categories.append(CATEGORY_MIXED)
        else:
            categories.append(CATEGORY_JIT)
        if addr_info is not None and int(addr_info[2]) >= 0:
            lib_index = self.add_lib(filename, funcname)
            return thread.add_frame(funcname, int(addr_info[2]), filename, categories[-1], lib_index, -1)# vmprof jit line indexes are positive
        else:
            return thread.add_frame(funcname, -1, filename, categories[-1], -1, -1)

    def add_native_frame(self, thread, stack_info):
        funcname = stack_info
        filename = ""
        frameindex = thread.add_frame(funcname, -1, filename, CATEGORY_NATIVE, -1, -1)
        return frameindex
    
    def check_asm_frame(self, categories, stack_info, thread, last_frame):
        if len(categories) > 0 and categories[-1] == 3:# if last frame is jit and current is asm => replace with inline jit frame
            categories.pop()
            categories.append(CATEGORY_JIT_INLINED)
            last_nativesymbol_index = thread.frametable[last_frame][1]
            thread.nativesymbols[last_nativesymbol_index][2] = stack_info
        else:# asm disabled
            pass
            #categories.append(CATEGORY_ASM)#asm
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
        processed_profile["counters"] = self.dump_counters()
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
        threads = []
        for thread in list(self.threads.values()):
            threads.append(thread.dump_thread())
        for thread in list(self.gc_sampled_threads.values()):
            threads.append(thread.dump_thread())
        return threads
    
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
        static_meta["categories"] = self.dump_categories()
        static_meta["preprocessedProfileVersion"] = 47
        static_meta["symbolicated"] = True
        static_meta["markerSchema"] = []
        return static_meta

    def dump_vmprof_meta(self, stats):
        vmprof_meta = {}
        ms_for_sample = 0
        if "period" in stats.meta:
            ms_for_sample = 1000 * float(stats.getmeta("period", "0.1"))# firefox profiler doesnt like a zero as interval
        
        if ms_for_sample == 0 and hasattr(stats, "gc_profiles") and len(stats.gc_profiles) != 0:
            ms_for_sample = int(stats.get_runtime_in_microseconds() / len(stats.gc_profiles)) * 0.001
        else:
            ms_for_sample = int(stats.get_runtime_in_microseconds() / len(stats.profiles)) * 0.000001
        
        vmprof_meta["interval"] = ms_for_sample #seconds
        vmprof_meta["startTime"] = 1681890179831.0
        vmprof_meta["shutdownTime"] = 1681890180325.0
        vmprof_meta["abi"] = stats.interp # interpreter

        os = stats.getmeta("os","default os")
        bits = stats.getmeta("bits","64")
        osdict = {"linux": "x11", "win64": "Windows", "win32": "Windows", "mac": "Macintosh"}# vmprof key for mac may be wrong
        
        vmprof_meta["oscpu"] = f"{osdict[os]} {bits}bit"
        vmprof_meta["platform"] = osdict[os]
        vmprof_meta["processType"] = 0
        vmprof_meta["stackwalk"] = 1
        vmprof_meta["debug"] = False
        vmprof_meta["version"] = 27
        vmprof_meta["importedFrom"] = "VMProf"
        vmprof_meta["categories"] = self.dump_categories()
        vmprof_meta["preprocessedProfileVersion"] = 47
        vmprof_meta["symbolicated"] = True
        vmprof_meta["markerSchema"] = self.dump_marker_schema()
        
        return vmprof_meta
    
    def dump_marker_schema(self):
        schema = []

        schema.append(
            {
                "type": "PyPyLog",
                "name": "PyPyLog",
                "tableLabel": "{marker.name}",
                "display": ["marker-chart", "marker-table", "timeline-overview"],
                "data": []
            }
        )

        schema.append(
            {
                "type": "Garbage Collection",
                "name": "Garbage Collection",
                "tableLabel": "{marker.name}",
                "description": "Garbage Collection Activities",
                "display": ["marker-chart", "marker-table", "timeline-memory", "timeline-overview"],
                "data": [
                    {
                        "key": stat,
                        "format": "string",
                        "searchable": True
                    } for stat in self.gc_stat_types 
                ]
            }
        )

        return schema

    
    def dump_categories(self):
        categories = []
        categories.append(
            {
                "name": "Python",
                "color": "yellow",
                "subcategories": [
                    "Other"
                ]
            }
        )
        categories.append(
            {
                "name": "Memory",
                "color": "red",
                "subcategories": [
                    "Other"
                ]
            }
        )    
        categories.append(
            {
                "name": "Native",
                "color": "lightblue",
                "subcategories": [
                    "Other"
                ]
            }
        )    
        categories.append(
            {
                "name": "JIT",
                "color": "purple",
                "subcategories": [
                    "Other"
                ]
            }
        )    
        categories.append(
            {
                "name": "ASM",
                "color": "blue",
                "subcategories": [
                    "Other"
                ]
            }
        )
        categories.append(
            {
                "name": "JIT(Inlined)",
                "color": "purple",
                "subcategories": [
                    "Other"
                ]
            }
        )   
        categories.append(
            {
                "name": "Mixed",
                "color": "orange",
                "subcategories": [
                    "Other"
                ]
            }
        )
        categories.append(
            {
                "name": "Garbage Collection",
                "color": "green",
                "subcategories": [
                    "Other"
                ]
            }
        )
        categories.append(
            {
                "name": "Interpreter",
                "color": "yellow",
                "subcategories": [
                    "Other"
                ]
            }
        )

        categories.append(
            {
                "name": "GC Minor Tenured",
                "color": "red",
                "subcategories": [
                    "Other"
                ]
            }
        )
        categories.append(
            {
                "name": "GC Minor Collected",
                "color": "green",
                "subcategories": [
                    "Other"
                ]
            }
        )
        return categories

    def dump_counters(self):
        counters = []
        for ctype in self.counters.keys():
            #if ctype == "vmRSS":
            #    counters.append(self.dump_vmrss_counter())    
            if ctype in ("vmRSS", "total_memory_used", "total_size_of_arenas"):
                color = "orange" if ctype == "vmRSS" else "red"
                counters.append(self.dump_counter(ctype, ctype, color))  
        return counters
    
    def dump_counter(self, ctype, descr, color="orange"):
        counter = {}
        counter["name"] = ctype
        counter["category"] = "Memory"
        counter["description"] = descr
        counter["color"] = color
        counter["pid"] = "51580"
        counter["mainThreadIndex"] = 0
        memory_in_alloc_form =  self.get_mem_allocations(ctype)
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


    def get_mem_allocations(self, ctype):
        # Firefox Profiler seems to need two non zero samples
        counter = self.counters[ctype]
        mem_diff = [counter[0], counter[0]]
        current_mem = mem_diff[0][1]
        for ctr in counter[1:len(counter) - 1]:
            mem_diff.append([ctr[0], (ctr[1] - current_mem)])
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
        self.allocations = [] # list of [stackindex, time in ms, memory allocated]

    def create_pypylog_marker(self, pypylog):
        interperter_string_id = self.add_string("interpreter")
        for i in range(int(len(pypylog)/2)):
            start_log = pypylog[2*i]
            stop_log = pypylog[2*i+1]
            starttime = start_log[0]
            endtime = stop_log[0]
            name = start_log[1]
            st_id = self.add_string(name)
            self.add_marker(starttime, endtime, st_id, {"type": "PyPyLog"})
            if i < ((len(pypylog)/2) - 2):
                next_log = pypylog[2 * i + 2]
                next_logtime_start = next_log[0]
                if abs(endtime - next_logtime_start) > 2:
                    self.add_marker(endtime + 1, next_logtime_start - 1, interperter_string_id, {"type": "PyPyLog"})

    def create_single_pypylog_marker(self, start_log, stop_log):
        starttime = start_log[PPL_TIME]
        endtime = stop_log[PPL_TIME]
        name = start_log[PPL_ACTION]
        st_id = self.add_string(name)
        self.add_marker(starttime, endtime, st_id, {"type": "PyPyLog"})

    def create_single_pypylog_interpreter_marker(self, starttime, endtime):
        st_id = self.add_string("interpreter")## move out
        self.add_marker(starttime, endtime, st_id, {"type": "PyPyLog"})
            
    def add_marker(self, starttime, endtime, stringtable_index, data):
        self.markers.append([starttime, endtime, stringtable_index, data])


    def add_string(self, string):
        if string in self.stringarray_positions:
            return self.stringarray_positions[string]
        else:
            result = len(self.stringarray)
            self.stringarray.append(string)
            self.stringarray_positions[string] = result
            return result
        
    def add_stack(self, stack, categories):
        #stack is a list of frametable indexes
        if not stack:
            return None
        else:
            top = stack[-1]
            rest = stack[:-1]
            top_category = categories[-1]
            rest_categories = categories[:-1]
            rest_index = self.add_stack(rest, rest_categories)
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
            is_python = category in (CATEGORY_PYTHON, CATEGORY_MIXED, CATEGORY_JIT, CATEGORY_JIT_INLINED)
            self.functable.append([stringtable_index_func, stringtable_index_file, line, resource_index, is_python])
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
            self.frametable.append([functable_index, nativesymbol_index, line, category])
            self.frametable_positions[key] = frametable_index
            return frametable_index
        
    def add_sample(self, stackindex, time):
        self.samples.append([stackindex, time]) # stackindex, ms since starttime
    
    def add_allocation(self, stackindex, time, n_bytes_allocated):
        self.allocations.append([stackindex, time, n_bytes_allocated]) # stackindex, ms since starttime, bytes allocated
    
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
        thread["registerTime"] = 0#23.841461000000002
        thread["unregisterTime"] = None
        thread["tid"] = self.tid
        thread["pid"] = "51580"
        thread["showMarkersInTimeline"] = True
        thread["markers"] = self.dump_markers()
        thread["nativeSymbols"] = self.dump_nativesymbols()
        thread["frameTable"] = self.dump_frametable()
        thread["funcTable"] = self.dump_functable()
        thread["resourceTable"] = self.dump_resourcetable()
        thread["stackTable"] = self.dump_stacktable()
        thread["samples"] = self.dump_samples()
        thread["stringArray"] = self.dump_stringarray()
        if self.allocations != []:
            thread["jsAllocations"] = self.dump_allocations()
        return thread
    
    def dump_allocations(self):
        allocations = {}
        allocations["time"] = [a[1] for a in self.allocations]
        allocations["className"] = ["Call" for _ in range(len(self.allocations))]
        allocations["typeName"] = ["PyObj" for _ in range(len(self.allocations))] # TODO: replace with real value, as soon as we know type of allocated obj
        allocations["coarseType"] = ["Object" for _ in range(len(self.allocations))]
        allocations["weight"] = [a[2] for a in self.allocations]
        allocations["weightType"] = "bytes"
        allocations["inNursery"] = [True for _ in self.allocations] # TODO: replace with real value, as soon as we know if it was nursery alloc or ex_malloc
        allocations["stack"] = [a[0] for a in self.allocations]
        allocations["length"] = len(self.allocations)
        return allocations
    
    """def dump_markers(self):
        if self.marker_schema == "PyPyLog": return self.dump_pypylog_markers()
        if self.marker_schema == "Garbage Collection": return self.dump_gc_markers()
        return self.dump_empty_markers()
        #"cause": {
        #    "tid": 18149,
        #    "time": 7031375.131204297,
        #    "stack": 88
        #}"""
    
    def dump_empty_markers(self):
        markers = {}
        markers["data"] = []
        markers["name"] = []
        markers["startTime"] = []
        markers["endTime"] = []
        markers["phase"] = []
        markers["category"] = []
        markers["length"] = 0
        return markers
    
    def dump_markers(self):
        markers = {}
        markers["data"] = [m[3] for m in self.markers]
        markers["name"] = [m[2] for m in self.markers]
        markers["startTime"] = [m[0] for m in self.markers]
        markers["endTime"] = [m[1] for m in self.markers]
        markers["phase"] = [1 for _ in self.markers]
        markers["category"] = [CATEGORY_GC for _ in self.markers]
        markers["length"] = len(self.markers)
        return markers

    """def dump_pypylog_markers(self):
        markers = {}
        markers["data"] = [m[3] for m in self.markers]
        markers["name"] = [m[2] for m in self.markers]
        markers["startTime"] = [m[0] for m in self.markers]
        markers["endTime"] = [m[1] for m in self.markers]
        markers["phase"] = [1 for _ in self.markers]
        markers["category"] = [CATEGORY_GC for _ in self.markers]
        markers["length"] = len(self.markers)
        return markers"""
 
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
        ftable["category"] = [frame[3] for frame in self.frametable]
        ftable["subcategory"] = [None for _ in self.frametable]
        ftable["func"] = [frame[0] for frame in self.frametable]
        ftable["innerWindowID"] = [0 for _ in self.frametable]
        ftable["implementation"] = [None for frame in self.frametable]
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
        ftable["isJS"] = [func[4] for func in self.functable]
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
