import sys
import json
import os
import webbrowser
import subprocess
import platform
import argparse
import time
import atexit
from zipfile import ZipFile
from vmprofconvert import convert_stats_with_pypylog
from symbolserver import start_server 

def run_vmprof(path, argv, native, lines):
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
        if lines:
            args += " --lines"
        if system == "Linux" or system == "Darwin":
            args += " --mem"
    if not native:
        args += " --no-native"
            
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
    if "times" in path_dict:
        file_dict["times"] = path_dict["times"]
        path_dict.pop("times")
    with ZipFile(zip_path, "w") as sharezip:
        ctr = 0
        for path in list(path_dict.keys()):
            new_filename = str(ctr) + "_" + os.path.basename(path_dict[path])
            sharezip.write(path_dict[path], new_filename)# new filename to prevent duplicate names
            file_dict[path] = new_filename
            ctr += 1
        write_file_dict(file_dict, sharezip)

def load_zip_dict(zip_path, folder):
    zip_dict = None
    dict_path = None
    with ZipFile(zip_path, "r") as inputzip:# open zip extract dict
        dict_path = inputzip.extract("dict.json", folder)
    if dict_path:
        with open(dict_path, "r") as file_dict:# read zip_dict
            zip_dict = json.loads(file_dict.read())
    os.remove(dict_path)
    return zip_dict

def extract_files(zip_dict, zip_path, folder):
    new_file_paths = {}
    with ZipFile(zip_path, "r") as inputzip:# open zip, extract files listed in zip_dict
        for path in list(zip_dict.keys()):
            filename = zip_dict[path]
            new_file_paths[path] = inputzip.extract(filename, folder)
    return new_file_paths
            
def cleanup(folder, path_dict):
    path_dict["json"] = path_dict["prof"] + ".json"# json is created, not loaded
    for path in path_dict:
        os.remove(path_dict[path])
    os.rmdir(folder)

def get_paths(path_dict):
    path = None
    jitlogpath = None
    pypylogpath = None
    if "prof" in path_dict:
        path = path_dict["prof"]
    if "jitlog" in path_dict:
        jitlogpath = path_dict["jitlog"]
    if "pypylog" in path_dict:
        pypylogpath = path_dict["pypylog"]
    return path, jitlogpath, pypylogpath

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="vmprof-firefox-converter", description="convert vmprof profiles or run vmprof directly")
    parser.add_argument("-convert", metavar = "convert_file", dest = "convert_file", nargs = 1, help = "convert vmprof profile or zip")
    parser.add_argument("-jitlog", metavar = "jitlog_file", dest = "jitlog_file", nargs = 1, help = "use jitlog data")
    parser.add_argument("-pypylog", metavar = "pypylog_file", dest = "pypylog_file", nargs = 1, help = "use pypylog data")
    parser.add_argument("-run", metavar = "python_file args", dest = "python_file", nargs = "+", help = "run vmprof and convert profile")
    parser.add_argument("--nobrowser", action = "store_false", dest = "browser", default = True, help = "dont open firefox profiler")
    parser.add_argument("--zip", action = "store_true", dest = "zip", default = False, help = "save profile as sharable zip file")
    parser.add_argument("--nonative", action = "store_false", dest = "native", default = True, help = "disable native profiling")
    parser.add_argument("--nolines", action = "store_false", dest = "lines", default = True, help = "disable line profiling")

    args = parser.parse_args()

    zip_path = None
    pypylogpath = None
    jitlogpath = None
    times = None
    path_dict = None

    if args.python_file:
        path, jitlogpath, pypylogpath, times = run_vmprof(args.python_file[0], args.python_file[1:], args.native, args.lines)
        if jitlogpath is not None:
            jitlogpath = os.path.abspath(jitlogpath)
        if pypylogpath is not None:
            pypylogpath = os.path.abspath(pypylogpath)
        if args.zip:
            zip_path = path.replace(".prof", ".zip")
    elif args.convert_file:
        if ".zip" in args.convert_file[0]:
            extracted_folder = "tmp"
            zip_dict = load_zip_dict(args.convert_file[0], extracted_folder)
            if "times" in zip_dict:
                times = zip_dict["times"]
                zip_dict.pop("times")
            path_dict = extract_files(zip_dict, args.convert_file[0],  extracted_folder)
            path, jitlogpath, pypylogpath = get_paths(path_dict)
            atexit.register(cleanup, extracted_folder, path_dict)
        else:
            path = args.convert_file[0]
            if args.zip:
                zip_path = path.replace(".prof", ".zip")
            if args.jitlog_file:
                jitlogpath = os.path.abspath(args.jitlog_file[0])
            if args.pypylog_file:
                pypylogpath = os.path.abspath(args.pypylog_file[0])
            
    abspath = os.path.abspath(path)

    url = "https://profiler.firefox.com/from-url/http%3A%2F%2F127.0.0.1%3A5000%2Fprofile"
    url += "/?symbolServer=http%3A%2F%2F127.0.0.1%3A5000%2F"

    with open(abspath + ".json", "w") as output_file:
        json_profile, new_path_dict = convert_stats_with_pypylog(abspath, pypylogpath, times)
        output_file.write(json.dumps(json.loads(json_profile), indent=2))
        if args.zip:
            new_path_dict["prof"] = abspath
            if jitlogpath:
                new_path_dict["jitlog"] = jitlogpath
            if pypylogpath:
                new_path_dict["pypylog"] = pypylogpath
                new_path_dict["times"] = list(times)
            save_zip(zip_path, new_path_dict)
        if pypylogpath and os.path.exists(pypylogpath) and not args.convert_file:
            os.remove(pypylogpath)
    if args.browser:
        webbrowser.open(url, new=0, autoraise=True)
        start_server(abspath + ".json", jitlogpath, path_dict)
