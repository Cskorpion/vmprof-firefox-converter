import os 
import json
import dis
from jitlog.parser import parse_jitlog
from flask import Flask
from flask import request
from flask_cors import CORS, cross_origin

flaskapp = Flask(__name__)
cors = CORS(flaskapp)
flaskapp.config["CORS_HEADERS"] = "Content-Type"   

@flaskapp.get("/profile")
def getprofile():
    if os.path.exists(profilepath):
        return json.dumps(open(profilepath, "r").read())
    else:
        return ""
    
@flaskapp.post("/source/v1")
def source():
    response = {
        "symbolsLastModified": None,
        "sourceLastModified": None,
        "file": "",
        "source": "" 
    }   
    if request.data is not None:
        jsonobj = json.loads(request.data)
        response["file"] = jsonobj["file"]
        if response["file"] is not None:
            if os.path.exists(response["file"]):
                with open(response["file"], "r") as file:
                    response["source"] = file.read()
                return json.dumps(response)
    return ""

@flaskapp.post("/asm/v1")
def asm():
    response = {
        "startAddress": "0x7",
        "size": "0x17",
        "arch": "arch", 
        "syntax": "jitlog",
        "instructions": []
    }
    if request.data is not None:
        jsonobj = json.loads(request.data)
        addr = jsonobj["startAddress"]
        if isinstance(addr, str) and addr != "0x-1":
            addr = int(addr ,16)
        response["startAddress"] = "0x0"
        code = get_jitlog_ir(jitlogpath, addr)
        if len(code) != 0:
            response["instructions"] = code
            response["size"] = len(code)
    return json.dumps(response)

def get_jitlog_ir(jitpath, addr):
    asm = []
    if jitpath is None or not os.path.exists(jitpath):
        return asm
    forest = parse_jitlog(jitpath)
    trace = forest.get_trace_by_addr(addr)
    if trace is not None:
        if "opt" in trace.stages:
            for i, op in enumerate(trace.stages["opt"].get_ops()):
                asm.append([i, str(op)])
    return asm

def get_mp_data(trace):
    offsets = []
    if trace is not None:
        if "opt" in trace.stages:
            mergepoints = trace.stages["opt"].get_merge_points()
            for mp in mergepoints:
                ofs = (mp.values[1], mp.values[2], mp.values[8], mp.values[4])# file, lineno, func, bc_offset
                offsets.append(ofs)
    return offsets

def get_all_bytecodes_rec(code):
    yield code
    for const in code.co_consts:
        if type(const) is not type(code):
            continue
        yield from get_all_bytecodes_rec(const)

def search_bytecode(module_code, funcname, linenumber):
    for code in get_all_bytecodes_rec(module_code):
        if code.co_name == funcname and code.co_firstlineno == linenumber:
            yield code

def get_instruction(codeobject, funcname, linenumber, offset):
    l = list(search_bytecode(codeobject, funcname, linenumber))
    if len(l) != 1:
        return None
    bc = dis.Bytecode(l[0])
    for inst in bc:
        if inst.offset == offset:
            return inst
    
def get_sourceline(path, line):
    if path is None or not os.path.exists(path):
        return None
    sourcelines = []
    with open(path, "r") as file:
        sourcelines = file.readlines()
    if len(sourcelines) > line:
        return sourcelines[line]
    return None

def start_server(jsonpath, jitlog):
    global profilepath , jitlogpath
    profilepath = jsonpath
    jitlogpath = jitlog
    flaskapp.run() 