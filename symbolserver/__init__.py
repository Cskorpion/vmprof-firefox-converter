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

def start_server():
    flaskapp.run()