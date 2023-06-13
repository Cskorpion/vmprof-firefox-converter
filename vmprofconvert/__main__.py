import sys
import json
import os
import webbrowser
import subprocess
import platform
import argparse
import time
from vmprofconvert import convert_stats_with_pypylog
from symbolserver import start_server 

def run_vmprof(path, argv):
    profpath = path.replace(".py", ".prof")
    impl = platform.python_implementation()
    system = platform.system()
    args = " -o " + profpath

    env = os.environ.copy()

    jitlogpath = None
    pypylogpath = None 
    if impl == "PyPy":
        args += " --jitlog"
        jitlogpath = profpath + ".jit"
        pypylogpath = path.replace(".py", ".pypylog")
        env["PYPYLOG"] = pypylogpath
    if impl == "CPython":
        args += " --lines"
        if system == "Linux" or system == "Darwin":
            args += " --mem"
            
    cmd_args = ""
    if len(argv) > 0:
        for arg in argv:
            cmd_args += " " + arg
    
    start_time = time.time()

    command = sys.executable + " -m vmprof" + args + " " + path + cmd_args
    subprocess.run(command, shell=True, env=env)

    end_time = time.time()
    
    return (profpath, jitlogpath, pypylogpath, (start_time, end_time))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="vmprof-firefox-converter")
    parser.add_argument("-convert", metavar = "vmprof_file", dest = "vmprof_file", nargs = 1, help = "convert vmprof profile")
    parser.add_argument("-jitlog", metavar = "jitlog_file", dest = "jitlog_file", nargs = 1, help = "use jitlog data")
    parser.add_argument("-run", metavar = "python_file args", dest = "python_file", nargs = "+", help = "run vmprof and convert profile")
    parser.add_argument("--nobrowser", action = "store_false", dest = "browser", default = "true", help = "dont open firefox profiler")

    args = parser.parse_args()

    if args.python_file:
        path, jitlogpath, pypylogpath, times = run_vmprof(args.python_file[0], args.python_file[1:])
        if jitlogpath is not None:
            jitlogpath = os.path.abspath(jitlogpath)
        if pypylogpath is not None:
            pypylogpath = os.path.abspath(pypylogpath)
    elif args.vmprof_file:
        path = args.vmprof_file[0]
        pypylogpath = None
        jitlogpath = None
        times = None
        if args.jitlog_file:
            jitlogpath = os.path.abspath(args.jitlog_file[0])
            
    abs_path = os.path.abspath(path)

    url = "https://profiler.firefox.com/from-url/http%3A%2F%2F127.0.0.1%3A5000%2Fprofile"
    url += "/?symbolServer=http%3A%2F%2F127.0.0.1%3A5000%2F"

    with open(abs_path + ".json", "w") as output_file:
        json_profile = convert_stats_with_pypylog(abs_path, pypylogpath, times)
        output_file.write(json.dumps(json.loads(json_profile), indent=2))
        if pypylogpath and os.path.exists(pypylogpath):
            os.remove(pypylogpath)
    if args.browser:
        webbrowser.open(url, new=0, autoraise=True)
        start_server(abs_path + ".json", jitlogpath)