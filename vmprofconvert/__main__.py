import sys
import json
import os
import webbrowser
import subprocess
import platform
from vmprofconvert import convert_stats
from symbolserver import start_server 

def run_vmprof(path):
    profpath = path.replace(".py", ".prof")
    impl = platform.python_implementation()
    os = platform.system()
    args = " -o " + profpath

    jitlogpath = None 
    if impl == "PyPy":
        args += " --jitlog"
        jitlogpath = profpath + ".jit"
    if impl == "CPython":
        args += " --lines"
        if os == "Linux" or os == "Darwin":
            args += " --mem"
        
    command = sys.executable + " -m vmprof" + args + " " + path
    subprocess.run(command, shell=True)

    return (profpath, jitlogpath)

if __name__ == "__main__":
    if sys.argv[1] == "run":# todo: use argparse
        if len(sys.argv) > 2:
            path, jitlogpath = run_vmprof(sys.argv[2])
            if jitlogpath is not None:
                jitlogpath = os.path.abspath(jitlogpath)
    else:
        path = sys.argv[1]
        jitlogpath = None
        if len(sys.argv) > 2 and sys.argv[2] is not None:
            print(sys.argv[2])
            jitlogpath = os.path.abspath(sys.argv[2])
            
    abs_path = os.path.abspath(path)

    url = "https://profiler.firefox.com/from-url/http%3A%2F%2F127.0.0.1%3A5000%2Fprofile"
    url += "/?symbolServer=http%3A%2F%2F127.0.0.1%3A5000%2F"

    with open(abs_path + ".json", "w") as output_file:
        output_file.write(json.dumps(json.loads(convert_stats(abs_path)), indent=2))
        webbrowser.open(url, new=0, autoraise=True)
        start_server(abs_path + ".json", jitlogpath)