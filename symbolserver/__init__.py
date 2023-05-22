import os 
import json
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
    if request.data is not None:
        jsonobj = json.loads(request.data)
    response = {
        "startAddress": "0x7",
        "size": "0x17",
        "arch": "aarch64", 
        "syntax": "ARM",
        "instructions": [[0, "duck"],
                         [1, "goose"]]
    }
    return json.dumps(response)

def start_server():
    flaskapp.run()