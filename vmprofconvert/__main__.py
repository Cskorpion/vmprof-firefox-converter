import sys
import json
import os
import webbrowser
import subprocess
import platform
import argparse
from vmprofconvert import convert_stats
from symbolserver import start_server 

def run_vmprof(path, argv, pypylog):
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
            
    cmd_args = ""
    if len(argv) > 3:
        for arg in argv[3:]:
            cmd_args += " " + arg

    command = sys.executable + " -m vmprof" + args + " " + path + cmd_args
    subprocess.run(command, shell=True)

    return (profpath, jitlogpath)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="vmprof-firefox-converter")
    parser.add_argument("-convert", metavar = "vmprof_file", dest = "vmprof_file", nargs = 1, help = "convert vmprof profile")
    parser.add_argument("-jitlog", metavar = "jitlog_file", dest = "jitlog_file", nargs = 1, help = "use jitlog data")
    parser.add_argument("-run", metavar = "python_file args", dest = "python_file", nargs = "+", help = "run vmprof and convert profile")
    parser.add_argument("--nobrowser", action = "store_false", dest = "browser", default = "true", help = "dont open firefox profiler")
    parser.add_argument("--pypylog",  action = "store_true", dest = "pypylog", default = "false", help = "use pypylog")

    args = parser.parse_args()

    if args.python_file:
        path, jitlogpath = run_vmprof(args.python_file[0], args.python_file[1:], args.pypylog)
        if jitlogpath is not None:
            jitlogpath = os.path.abspath(jitlogpath)
    elif args.vmprof_file:
        path = args.vmprof_file[0]
        jitlogpath = None
        if args.jitlog_file:
            jitlogpath = os.path.abspath(args.jitlog_file[0])
            
    abs_path = os.path.abspath(path)

    url = "https://profiler.firefox.com/from-url/http%3A%2F%2F127.0.0.1%3A5000%2Fprofile"
    url += "/?symbolServer=http%3A%2F%2F127.0.0.1%3A5000%2F"

    with open(abs_path + ".json", "w") as output_file:
        output_file.write(json.dumps(json.loads(convert_stats(abs_path)), indent=2))
    if args.browser:
        webbrowser.open(url, new=0, autoraise=True)
        start_server(abs_path + ".json", jitlogpath)