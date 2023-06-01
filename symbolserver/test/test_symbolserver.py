import os
from jitlog.parser import parse_jitlog
from symbolserver import get_jitlog_ir 
from symbolserver import get_mp_data, get_sourceline, get_bc_instruction, insert_code, code_dict_to_list

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
    instr = get_bc_instruction(code, "get_name", 6, 0)
    assert instr.offset == 0
    assert instr.argval == "self"

def test_get_source_line():
    path = os.path.join(os.path.dirname(__file__), "profiles/bctest.py")
    line = get_sourceline(path, 3)
    assert line.strip() == "self.name = \"Floppa\""

def test_insert_code():
    code = {}
    index = 0
    key = "example key"
    py_line0 = "example py_line"
    bc_instr0 = "example bytecode"
    ir_instr0 = "example ir code"# maybe this is going to be a list
    py_line1 = "example py_line"
    bc_instr1 = "other example bytecode"
    ir_instr1 = "other example ir code"

    index = insert_code(code, index, key, py_line0, bc_instr0, ir_instr0)# ir not implemented yet
    index = insert_code(code, index, key, py_line1, bc_instr1, ir_instr1)

    assert code[key] == {
        "py": [0, "example py_line"],
        "bc": [[1, " example bytecode"], [2, " other example bytecode"]],
        "ir": [] # ir not implemented yet
    }

def test_code_dict_to_list():
    codedict = {
        "first key": {
            "py": [0, "nice python line"],
            "bc": [[1, "first bytecode line"],[2, "second bytecode line"]],
            "ir": []
        },
        "second key": {
            "py": [3, "weird python line"],
            "bc": [[4, "third bytecode line"]],
            "ir": []
        }
    }
    expected_code_list = [[0, "nice python line"],
                          [1, "first bytecode line"],
                          [2, "second bytecode line"],
                          [3, "weird python line"],
                          [4, "third bytecode line"]]
    
    codelist = code_dict_to_list(codedict)
    
    assert codelist == expected_code_list