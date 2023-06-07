import re

def parse_pypylog(path):
    raw_log = None
    if path is not None:
        with open(path, "r") as ppl:
            raw_log = ppl.readlines()
    log = []
    if raw_log:
        #From gccauses.py
        start = re.compile(r"\[([0-9a-fA-F]+)\] \{([\w-]+)")
        stop  = re.compile(r"\[([0-9a-fA-F]+)\] ([\w-]+)\}")
        for line in raw_log:
            match = start.match(line)
            starting = True
            if not match:
                match = stop.match(line)
                starting = False
            if match:
                timestamp = int(match.group(1), base=16)
                action = match.group(2)
                log.append([timestamp, action, starting])           
    return log

def cut_pypylog(pypylog, total_runtime_micros, vmprof_runtime_micros): 
    factor = vmprof_runtime_micros/total_runtime_micros
    limit = int(factor * len(pypylog))
    return pypylog[:limit]