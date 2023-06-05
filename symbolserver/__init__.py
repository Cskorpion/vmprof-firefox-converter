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

codeobj_dict = {}

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
    return response

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
        #code = get_jitlog_ir(jitlogpath, addr)
        code = get_advanced_code(jitlogpath, addr)
        if len(code) != 0:
            response["instructions"] = code
            response["size"] = len(code)
    return json.dumps(response)

def get_code_object(path):
    if path in codeobj_dict:
        return codeobj_dict[path]
    else:
        #maybe add limit
        with open(path, "rb") as file:
            content = file.read()
        codeobj_dict[path] = compile(content, path, "exec")
        return codeobj_dict[path]

def get_advanced_code(jitpath, addr):
    code = {}
    if jitpath is None or not os.path.exists(jitpath):
        return []
    forest = parse_jitlog(jitpath)
    trace = forest.get_trace_by_addr(addr)
    if trace is None:
        return []
    mp_data = get_mp_data(trace)
    ir_code = get_ir_code(trace.stages["opt"])
    code["pre"] = ir_code[0] # ir code from before first py line 
    for i, ir in enumerate(mp_data):
        key = ir[0] + str(ir[1])
        py_line = get_sourceline(ir[0], ir[1])
        if py_line is not None:
            codeobject = get_code_object(ir[0])
            bc_instr = get_bc_instruction(codeobject, ir[2], ir[1], ir[3])
            insert_code(code, key, py_line, bc_instr, ir_code[i + 1])
    return code_dict_to_list(code)

def get_ir_code(stage_opt):
    ir_code = []
    indexes = [0]
    [indexes.append(mp.index) for mp in stage_opt.get_merge_points()]
    indexes.append(len(stage_opt.get_ops()))
    for i in range(len(indexes) - 1):
        ir_code.append(stage_opt.get_ops()[indexes[i]:indexes[i + 1]])
    return ir_code
   
def insert_code(code, key, py_line, bc_instr, ir_instr):
    if bc_instr is not None:
        if key not in code:
            code[key] = {
                "py_line": py_line.strip(),
                "bc": [{
                    "bc_line": str(bc_instr).strip(),
                    "ir_code": ir_instr 
                    }
                ]
            }
        else:
            nd = {
                "bc_line": str(bc_instr).strip(),
                "ir_code": ir_instr 
            }
            code[key]["bc"].append(nd)

def code_dict_to_list(code):
    index = 0
    lcode = []
    if "pre" in code:
        for ir_line in code["pre"]:
            lcode.append([index, "    " + ir_to_str(ir_line)])
            index += 1
        code.pop("pre")
    for v in code.keys():
        tmp = code[v]
        lcode.append([index, tmp["py_line"]])
        index += 1
        for bc in tmp["bc"]:
          lcode.append([index, "  " + bc["bc_line"]])
          index += 1
          for ir in bc["ir_code"]:
              lcode.append([index, "    " + ir_to_str(ir)])
              index += 1
    return lcode

def ir_to_str(ir):
    return str(ir).removeprefix("? = ")

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
        if code.co_name == funcname:# and code.co_firstlineno == linenumber:
            yield code

def get_bc_instruction(codeobject, funcname, linenumber, offset):
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
    line -= 1# line in debug_merge_points starts with 1
    with open(path, "r") as file:
        sourcelines = file.readlines()
    if len(sourcelines) > line:
        if sourcelines[line].strip() == "":
            return None
        return sourcelines[line]
    return None

def start_server(jsonpath, jitlog):
    global profilepath , jitlogpath
    profilepath = jsonpath
    jitlogpath = jitlog
    flaskapp.run() 