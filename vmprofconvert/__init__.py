import vmprof
import json

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

class Converter:
    def __init__(self):
        self.threads = {}
        self.counters = []#
    
    def walk_samples(self, stats):
        dummyeventdelay = 7
        sampletime = stats.end_time.timestamp() * 1000 - stats.start_time.timestamp() * 1000
        sampletime /= len(stats.profiles)
        category_dict = {}
        category_dict["py"] = 0
        category_dict["n"] = 2
        for i, sample in enumerate(stats.profiles):
            frames = []
            categorys = []
            stack_info, _, tid, memory = sample
            if tid in self.threads:
                thread = self.threads[tid]
            else:
                thread = self.threads[tid] = Thread() 
                thread.tid = tid
                thread.name = "Thread " + str(len(self.threads))# Threads seem to need different names
            if stats.profile_lines:
                indexes = range(0, len(stack_info), 2)
            else:
                indexes = range(len(stack_info))
            for j in indexes:
                addr_info = stats.get_addr_info(stack_info[j])
                if addr_info is None:
                    categorys.append(0)
                    funcname = stack_info[j]
                    filename = ""
                else:
                    funcname = addr_info[1]
                    filename = addr_info[3]
                    categorys.append(category_dict[addr_info[0]]) 
                if stats.profile_lines:
                    frames.append(thread.add_frame(funcname, -1 * stack_info[j + 1], filename))# vmprof line indexes are negative
                else:
                    frames.append(thread.add_frame(funcname, -1, filename))
            stackindex = thread.add_stack(frames, categorys)
            thread.add_sample(stackindex, i * sampletime, dummyeventdelay)
            if stats.profile_memory == True:
                self.counters.append([i * sampletime, memory * 1000])

    def dumps_static(self):
        processed_profile = {}
        processed_profile["meta"] = self.dump_static_meta()
        processed_profile["libs"] = []
        processed_profile["pages"] = []
        processed_profile["counters"] = []
        processed_profile["threads"] = self.dump_threads()
        return json.dumps(processed_profile)
    
    def dumps_vmprof(self, stats):
        processed_profile = {}
        processed_profile["meta"] = self.dump_vmprof_meta(stats)
        processed_profile["libs"] = []
        processed_profile["pages"] = []
        if(stats.profile_memory):
            processed_profile["counters"] = [self.dump_counters()]
        else:
            processed_profile["counters"] = []
        processed_profile["threads"] = self.dump_threads()
        return json.dumps(processed_profile)
    
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
        static_meta["categories"] = [
            {
                "name": "Python",
                "color": "yellow",
                "subcategories": [
                    "Other"
                ]
            },
            {
                "name": "Memory",
                "color": "red",
                "subcategories": [
                    "Other"
                ]
            },
            {
                "name": "Native",
                "color": "blue",
                "subcategories": [
                    "Other"
                ]
            }
        ]
        static_meta["preprocessedProfileVersion"] = 47
        static_meta["symbolicated"] = True
        static_meta["markerSchema"] = []
        return static_meta

    def dump_vmprof_meta(self, stats):
        vmprof_meta = {}
        ms_for_sample = int(stats.get_runtime_in_microseconds() / len(stats.profiles))# wrong if there are multiple threads
        
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
        vmprof_meta["categories"] = [
            {
                "name": "Python",
                "color": "yellow",
                "subcategories": [
                    "Other"
                ]
            },
            {
                "name": "Memory",
                "color": "red",
                "subcategories": [
                    "Other"
                ]
            },
            {
                "name": "Native",
                "color": "blue",
                "subcategories": [
                    "Other"
                ]
            }
        ]
        vmprof_meta["preprocessedProfileVersion"] = 47
        vmprof_meta["symbolicated"] = True
        vmprof_meta["markerSchema"] = []
        
        return vmprof_meta
    
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
        self.stacktable = []# list of [frameindex, stacktableindex_or_None]
        self.stacktable_positions = {}
        self.functable = []# list of [stringtable_index, stringtable_index, int] funcname, filename, line  line == -1 if profile_lines == False
        self.funtable_positions = {}
        self.frametable = []# list of [functable_index, category]   cat{0 = py, 1 = mem, 2 = native}
        self.frametable_positions = {}# key is string
        self.samples = [] #list of [stackindex, time in ms, eventdely in ms], no need for sample_positions

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
            
    def add_func(self, func, file, line):
        key = (func, file, line)
        if key in self.funtable_positions:
            return self.funtable_positions[key]
        else:
            stringtable_index_func = self.add_string(func)
            stringtable_index_file = self.add_string(file)
            result = len(self.functable)
            self.functable.append([stringtable_index_func, stringtable_index_file, line])
            self.funtable_positions[key] = result
            return result
            
    def add_frame(self, string, line, file):
        key = (string, line)
        if key in self.frametable_positions:
            return self.frametable_positions[key]
        else:
            functable_index = self.add_func(string, file, line)
            #stringtable_index = self.add_string(string)
            frametable_index = len(self.frametable)
            self.frametable.append([functable_index])
            self.frametable_positions[key] = frametable_index
            return frametable_index
        
    def add_sample(self, stackindex, time, eventdelay):
        self.samples.append([stackindex, time, eventdelay]) # stackindex, ms since starttime, eventdelay in ms
    
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

        thread["markers"] = { 
            "data": [],
            "length": 0
        }

        thread["frameTable"] = self.dump_frametable()
        thread["funcTable"] = self.dump_functable()
       
        thread["resourceTable"] = { 
            "type": [],
            "length": 0
        }
       
        thread["stackTable"] = self.dump_stacktable()
        thread["samples"] = self.dump_samples()
        thread["stringArray"] = self.dump_stringarray()

        return thread
    
    def dump_frametable(self):
        ftable = {}
        ftable["address"] = [-1 for _ in self.frametable]
        ftable["inlineDepth"] = [0 for _ in self.frametable]
        ftable["category"] = [0 for _ in self.frametable]
        ftable["subcategory"] = [None for _ in self.frametable]
        ftable["func"] = [frame[0] for frame in self.frametable]
        ftable["innerWindowID"] = [0 for _ in self.frametable]
        ftable["length"] = len(self.frametable)
        return ftable

    def dump_functable(self):
        ftable = {}
        ftable["isJS"] = [False for _ in self.functable]
        ftable["relevantForJS"] = [False for _ in self.functable]
        ftable["name"] = [func[0] for func in self.functable]
        ftable["resource"] = [-1 for _ in self.functable]
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
        samples["eventDelay"] = [sample[2] for sample in self.samples]
        samples["weightType"] = "samples"
        samples["weight"] = None
        samples["length"] = len(self.samples)
        return samples
    
    def dump_stringarray(self):
        return [str(string) for string in self.stringarray]
    
    def get_processed_filelines(self):
        linenumbers = []
        filenames = []
        if self.functable[0][2] != -1:
            for func in self.functable:
                if self.stringarray[func[1]] is "-":
                    linenumbers.append(None)
                else:
                    linenumbers.append(func[2])
        else:
            linenumbers = [None for _ in self.functable]
        for func in self.functable:
            if self.stringarray[func[1]] is "-":
                filenames.append(None)
            else:
                filenames.append(func[1])
        
        return linenumbers, filenames