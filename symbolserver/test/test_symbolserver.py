import os
from jitlog.parser import parse_jitlog
from symbolserver import get_jitlog_ir 
from symbolserver import get_mp_data, get_sourceline, get_instruction
from importlib.machinery import SourceFileLoader
from io import StringIO

def test_get_jitlog_ir():
    path = os.path.join(os.path.dirname(__file__), "profiles/pypy-pystone.prof.jit")
    asm = get_jitlog_ir(path, 140682485974400)
    assert len(asm) == 44

def test_get_empty_jitlog_ir():
    path = os.path.join(os.path.dirname(__file__), "profiles/pypy-pystone.prof.jit")
    asm = get_jitlog_ir(path, 115)# no ir for addr 115
    assert asm == []

def test_get_mp_data():
    path = os.path.join(os.path.dirname(__file__), "profiles/pypy-pystone.prof.jit")
    forest = parse_jitlog(path)
    trace = forest.get_trace_by_addr(140682485974400)
    mp_data = get_mp_data(trace)
    assert len(mp_data) == 18

def test_get_bytecode():
    path = os.path.join(os.path.dirname(__file__), "profiles/bctest.py")
    with open(path, "rb") as file:
        content = file.read()
    code = compile(content, path, "exec")
    instr = get_instruction(code, "get_name", 6, 0)
    assert instr.offset == 0
    assert instr.argval == "self"

def test_get_source_line():
    path = os.path.join(os.path.dirname(__file__), "profiles/bctest.py")
    line = get_sourceline(path, 3)
    assert line.strip() == "self.name = \"Floppa\""
