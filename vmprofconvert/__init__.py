import vmprof
import json

def convert(path):
    stats = vmprof.read_profile(path)
    c = Converter()
    c.walk_samples(stats.profiles)
    return c# return converter instance for testing
    
def convert_vmprof(path):
    c = Converter()
    stats = vmprof.read_profile(path)
    c.walk_samples(stats.profiles)
    return c# return converter instance for testing

class Converter:
    def __init__(self):
        self.stringtable = []
        self.stringtable_positions = {}
        self.stacktable = [] # list of [frameindex, stacktableindex_or_None]
        self.stacktable_positions = {}
        self.frametable = []
        self.frametable_positions = {}# key is string
        self.samples = [] #list of [stackindex, time in ms, eventdely in ms], no need for sample_positions


    def add_string(self, string):
        if string in self.stringtable_positions:
            return self.stringtable_positions[string]
        else:
            result = len(self.stringtable)
            self.stringtable.append(string)
            self.stringtable_positions[string] = result
            return result
    
    def add_stack(self, stack):
        #stack is a list of frametable indexes
        if not stack:
            return None
        else:
            top = stack[-1]
            rest = stack[:-1]
            rest_index = self.add_stack(rest)
            key = (top, rest_index)
            if key in self.stacktable_positions:
                return self.stacktable_positions[key]
            else:
                result = len(self.stacktable)
                self.stacktable.append([top, rest_index])
                self.stacktable_positions[key] = result
                return result
            
    def add_frame(self, string):
        if string in self.frametable_positions:
            return self.frametable_positions[string]
        else:
            stringtable_index = self.add_string(string)
            frametable_index = len(self.frametable)
            self.frametable.append(stringtable_index)
            self.frametable_positions[string] = frametable_index
            return frametable_index
    
    def add_sample(self, stackindex, time, eventdelay):
        self.samples.append([stackindex, time, eventdelay]) # stackindex, ms since starttime, eventdelay in ms

    def walk_samples(self, samples):
        #samples is list of tuple ([stack], count, threadid, memory_in_kb)
        dummyeventdelay = 7
        for i, sample in enumerate(samples):
            frames = []
            stack_info, _, tid, memory = sample
            stack_height = int(len(stack_info)/2)
            for j in range(stack_height):
                frames.append(self.add_frame(stack_info[2 * j]))
            stackindex = self.add_stack(frames)
            self.add_sample(stackindex, i, dummyeventdelay)# dummy time = index of sample from vmprof
    
    def dumps(self):
        gecko_profile = {}
        gecko_profile["meta"] = self.dump_static_meta()
        gecko_profile["pages"] = []
        gecko_profile["libs"] = []
        gecko_profile["pausedRanges"] = []
        gecko_profile["threads"] = [self.dump_thread()]
        gecko_profile["processes"] = []
        return json.dumps(gecko_profile)
    
    def dump_static_meta(self):
        static_meta = {}
        static_meta["version"] = 5
        static_meta["intervall"] = 0.4
        static_meta["stackwalk"] = 1
        static_meta["debug"] = 1
        static_meta["startTime"] = 1477063882018.4387
        static_meta["shutdownTIme"] = None
        static_meta["processType"] = 0
        static_meta["platform"] = "Macintosh"
        static_meta["oscpu"] = "Intel Mac OS X 10.12"
        static_meta["abi"] = "x86_64-gcc3"
        return static_meta
    
    def dump_thread(self):
        thread = {}
        thread["name"] = "GeckoMain"
        thread["processType"] = "default"
        thread["processName"] = "Parent Process"
        thread["tid"] = 7442229 # get from vmprof samples later
        thread["pid"] = 51580
        thread["registerTime"] = 23.841461000000002
        thread["unregisterTime"] = None
        thread["markers"] = { 
            "schema": {
                  "name": 0,
                  "time": 1,
                  "data": 2
                },
            "data": []
        }
        thread["samples"] = self.dump_samples()
        thread["frameTable"] = self.dump_frametable()
        thread["stackTable"] = self.dump_stacktable()
        thread["stringTable"] = self.dump_stringtable()
        return thread

    def dump_samples(self):
        samples = {}
        samples["schema"] = {
            "stack": 0,
            "time": 1,
            "eventDelay": 2
        }
        samples["data"] = self.samples
        return samples
    
    def dump_frametable(self):
        frametable = {}
        frametable["schema"] = {
            "location": 0,
            "relevantForJS": 1,
            "innerWindowID": 2,
            "implementation": 3
        }
        frametable["data"] = [[index, False, 2, 1] for index in self.frametable]
        return frametable
    
    def dump_stacktable(self):
        stacktable = {}
        stacktable["schema"] = {
                "frame": 0,
                "prefix": 1
        }
        stacktable["data"] = self.stacktable
        return stacktable
    
    def dump_stringtable(self):
        return self.stringtable