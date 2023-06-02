import os
from jitlog.parser import parse_jitlog
from symbolserver import get_jitlog_ir 
from symbolserver import get_mp_data, get_sourceline, get_bc_instruction, insert_code, code_dict_to_list, get_ir_code

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
    key = "example key"
    py_line0 = "example py_line"
    bc_instr0 = "example bytecode"
    ir_instr0 = ["example ir code"]
    py_line1 = "example py_line"
    bc_instr1 = "other example bytecode"
    ir_instr1 = ["other example ir code"]

    insert_code(code, key, py_line0, bc_instr0, ir_instr0)
    insert_code(code, key, py_line1, bc_instr1, ir_instr1)

    expected_code = {
        "py_line": "example py_line",
        "bc": [
            {
                "bc_line": "example bytecode",
                "ir_code": ["example ir code"]
            }, 
            {
                "bc_line": "other example bytecode",
                "ir_code": ["other example ir code"]
            }
        ]
    }

    assert code[key] == expected_code

def test_code_dict_to_list():
    codedict = {
        "first key": {
            "py_line":  "first python line",
            "bc": [
                {
                    "bc_line": "first bytecode line",
                    "ir_code": ["first ir line"]
                }
            ]
        },
        "second key": {
            "py_line": "second python line",
            "bc": [
                {
                    "bc_line": "second bytecode line",
                    "ir_code": []
                },
                {
                    "bc_line": "third bytecode line",
                    "ir_code": []
                }
            ]
        }
    }
    expected_code_list = [[0, "first python line"],
                          [1, "  first bytecode line"],
                          [2, "    first ir line"],
                          [3, "second python line"],
                          [4, "  second bytecode line"],
                          [5, "  third bytecode line"]]
    
    codelist = code_dict_to_list(codedict)
    
    assert codelist == expected_code_list

def test_get_ir_code():
    path = os.path.join(os.path.dirname(__file__), "profiles/pypy-pystone.prof.jit")
    forest = parse_jitlog(path)
    trace = forest.get_trace_by_addr(140682485974400)
    ir_code = get_ir_code(trace.stages["opt"])
    assert len(ir_code) == 18
