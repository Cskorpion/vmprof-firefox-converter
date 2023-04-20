import vmprof

def convert(path):
    stats = vmprof.read_profile(path)
    c = Converter()
    for sample in stats.profiles:
        pass
    return stats

class Converter:
    def __init__(self):
        self.stringtable = []
        self.stringtable_positions = {}
        self.stacktable = [] #list of [frameindex, stacktableindex_or_None]
        self.stacktable_positions = {}

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
    