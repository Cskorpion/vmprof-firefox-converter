import re

def parse_pypylog(path):
    raw_log = None
    if path:
        with open(path, "r") as ppl:
            raw_log = ppl.readlines()
    log = []
    if raw_log:
        # From gccauses.py
        depth = 0
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
                if starting:# not nice
                    log.append([timestamp, action, starting, depth])
                    depth += 1
                else:
                    depth -= 1
                    log.append([timestamp, action, starting, depth])
    return log

def cut_pypylog(pypylog, total_runtime_micros, vmprof_runtime_micros): 
    factor = vmprof_runtime_micros/total_runtime_micros
    limit = int(factor * len(pypylog))
    return pypylog[:limit]

def rescale_pypylog(pypylog, vmprof_runtime_micros):
    scaled_pypylog = []
    time = vmprof_runtime_micros / len(pypylog)
    for i in range(len(pypylog)):
        line = pypylog[i]
        log_time = int(time * i)# len(pypylog) > micros
        scaled_pypylog.append([log_time, line[1], line[2]])
    return scaled_pypylog

def filter_top_level_logs(pypylog):
    filtered_pypylog = list(filter(lambda e: e[3] == 0, pypylog))
    return filtered_pypylog