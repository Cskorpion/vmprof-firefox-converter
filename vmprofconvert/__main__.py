import sys
import json
import os
import webbrowser
import urllib.parse
from vmprofconvert import convert_stats
from symbolserver import start_server 

path = sys.argv[1]
abs_path = os.path.abspath(path)

url = "https://profiler.firefox.com/from-url/http%3A%2F%2F127.0.0.1%3A5000%2Fprofile%2F"
url += urllib.parse.quote(abs_path + ".json")
url += "/?symbolServer=http%3A%2F%2F127.0.0.1%3A5000%2F"

with open(path + ".json", "w") as output_file:
    output_file.write(json.dumps(json.loads(convert_stats(path)), indent=2))
    webbrowser.open(url, new=0, autoraise=True)
    start_server()