import sys
import json
import os
import webbrowser
import subprocess
import platform
import argparse
import time
from zipfile import ZipFile
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

def write_file_dict(file_dict, sharezip):
    #dump dict with real paths to new filenames mapping
    os.mkdir("tmp")
    with open("tmp/dict.json", "w") as dict_file:
        dict_file.write(json.dumps(file_dict, indent = 2))
    sharezip.write("tmp/dict.json", "dict.json")
    os.remove("tmp/dict.json")
    os.rmdir("tmp")
    pass

def save_zip(zip_path, path_dict):
    file_dict = {}
    with ZipFile(zip_path, "w") as sharezip:
        ctr = 0
        for path in list(path_dict.keys()):
            new_filename = str(ctr) + "_" + os.path.basename(path_dict[path])
            sharezip.write(path_dict[path], new_filename)# new filename to prevent duplicate names
            file_dict[path] = new_filename
            ctr += 1
        write_file_dict(file_dict, sharezip)
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="vmprof-firefox-converter")
    parser.add_argument("-convert", metavar = "vmprof_file", dest = "vmprof_file", nargs = 1, help = "convert vmprof profile")
    parser.add_argument("-jitlog", metavar = "jitlog_file", dest = "jitlog_file", nargs = 1, help = "use jitlog data")
    parser.add_argument("-run", metavar = "python_file args", dest = "python_file", nargs = "+", help = "run vmprof and convert profile")
    parser.add_argument("--nobrowser", action = "store_false", dest = "browser", default = "true", help = "dont open firefox profiler")
    parser.add_argument("--zip", action = "store_true", dest = "zip", default = "false", help = "save profile as sharable zip file")

    args = parser.parse_args()

    zip_path = None

    if args.python_file:
        path, jitlogpath, pypylogpath, times = run_vmprof(args.python_file[0], args.python_file[1:])
        if jitlogpath is not None:
            jitlogpath = os.path.abspath(jitlogpath)
        if pypylogpath is not None:
            pypylogpath = os.path.abspath(pypylogpath)
        if args.zip:
            zip_path = path.replace(".prof", ".zip")
    elif args.vmprof_file:
        path = args.vmprof_file[0]
        if args.zip:
            zip_path = path.replace(".prof", ".zip")
        pypylogpath = None
        jitlogpath = None
        times = None
        if args.jitlog_file:
            jitlogpath = os.path.abspath(args.jitlog_file[0])
            
    abspath = os.path.abspath(path)

    url = "https://profiler.firefox.com/from-url/http%3A%2F%2F127.0.0.1%3A5000%2Fprofile"
    url += "/?symbolServer=http%3A%2F%2F127.0.0.1%3A5000%2F"

    with open(abspath + ".json", "w") as output_file:
        json_profile, path_dict = convert_stats_with_pypylog(abspath, pypylogpath, times)
        output_file.write(json.dumps(json.loads(json_profile), indent=2))
        if args.zip:
            path_dict["prof"] = abspath
            if jitlogpath:
                path_dict["jitlog"] = jitlogpath
            if pypylogpath:
                path_dict["pypylog"] = pypylogpath
            save_zip(zip_path, path_dict)
        if pypylogpath and os.path.exists(pypylogpath):
            os.remove(pypylogpath)
    if args.browser:
        webbrowser.open(url, new=0, autoraise=True)
        start_server(abspath + ".json", jitlogpath)