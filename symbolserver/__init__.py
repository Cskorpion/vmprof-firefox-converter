import os 
import json
from jitlog.parser import parse_jitlog
from flask import Flask
from flask import request
from flask_cors import CORS, cross_origin

flaskapp = Flask(__name__)
cors = CORS(flaskapp)
flaskapp.config["CORS_HEADERS"] = "Content-Type"   

@flaskapp.get("/profile/<path:filepath>")
def getprofile(filepath):
    if os.path.exists(filepath):
        return json.dumps(open(filepath, "r").read())
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
                response["source"] = open(response["file"], "r").read()
                return json.dumps(response)
    return ""

@flaskapp.post("/asm/v1")
def asm():# dummy for now
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
            print(addr)
        response["startAddress"] = addr
        asm = get_jitlog_asm(addr)
        if len(asm) != 0:
            response["instructions"] = asm
            response["size"] = len(asm)
    return json.dumps(response)

def get_jitlog_asm(addr):
    asm = []
    forest = parse_jitlog(flaskapp.__dict__["jitlog"])
    trace = forest.get_trace_by_addr(addr)
    if trace is not None:
        if "opt" in trace.stages:
            for i, op in enumerate(trace.stages["opt"].get_ops()):
                asm.append([i, str(op)])
    return asm


def start_server(path):
    flaskapp.__dict__["jitlog"] = path# is this ok?
    flaskapp.run() 