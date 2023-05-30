import os
from jitlog.parser import parse_jitlog
from symbolserver import get_jitlog_ir 
from symbolserver import get_bytecode_offsets, get_bytecode, get_sourceline
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

def test_get_bytecode_offset():
    path = os.path.join(os.path.dirname(__file__), "profiles/pypy-pystone.prof.jit")
    forest = parse_jitlog(path)
    trace = forest.get_trace_by_addr(140682485974400)
    offsets = get_bytecode_offsets(trace)
    assert len(offsets) == 18

def test_get_bytecode():
    path = os.path.join(os.path.dirname(__file__), "profiles/bctest.py")
    module = SourceFileLoader("x", path).load_module()
    with StringIO() as bcfile:
        get_bytecode(module, bcfile)
        #print(bcfile.getvalue())
    assert True

def test_get_source_line():
    path = os.path.join(os.path.dirname(__file__), "profiles/bctest.py")
    line = get_sourceline(path, 3)
    assert line.strip() == "self.name = \"Floppa\""
