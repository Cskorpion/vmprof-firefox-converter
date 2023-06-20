import os
from jitlog.parser import parse_jitlog
from symbolserver import get_jitlog_ir , bc_to_str
from symbolserver import get_mp_data, get_sourceline, get_bc_instruction, insert_code, code_dict_to_list, get_ir_code, ir_to_str, get_code_object

class Dummyinstruction:
    def __init__(self, str):
        self.__str__ = str
    
    def _disassemble(self):
        return self.__str__

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
    assert instr.opname == "LOAD_FAST"

def test_get_source_line():
    path = os.path.join(os.path.dirname(__file__), "profiles/bctest.py")
    line = get_sourceline(path, 4)# merge_point line starts at 1

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

    assert len(ir_code) == 19

def test_ir_to_str():
    path = os.path.join(os.path.dirname(__file__), "profiles/pypy-pystone.prof.jit")
    forest = parse_jitlog(path)
    trace = forest.get_trace_by_addr(140682485974400)
    ir_code = get_ir_code(trace.stages["opt"])
    ir_instr = ir_code[1][0]
    ir_string = ir_to_str(ir_instr)
    expected_ir_str = "guard_value(i4, 4, @<ResumeGuardDescr object at 0x177f580>)"

    assert ir_string == expected_ir_str

def test_bc_to_str():
    bc0 = Dummyinstruction("55 LOAD_FAST         2 (float)")
    bc1 = Dummyinstruction("55   >>>>>   CALL_FUNCTION         4 (started)")
    pretty_bc0 = bc_to_str(bc0)
    pretty_bc1 = bc_to_str(bc1)

    assert pretty_bc0 == "LOAD_FAST 2 (float)"
    assert pretty_bc1 == "CALL_FUNCTION 4 (started)"

def test_get_example_bytecode():
    jitpath = os.path.join(os.path.dirname(__file__), "profiles/example.jitlog")
    pypath = os.path.join(os.path.dirname(__file__), "profiles/example.py")
    forest = parse_jitlog(jitpath)
    trace = forest.get_trace_by_addr(140249103068976)
    mp_data = get_mp_data(trace)
    codeobject = get_code_object(pypath)
    bc_instr = get_bc_instruction(codeobject, mp_data[2][2], mp_data[2][1], mp_data[2][3])    

    assert mp_data[2] == ("example.py", 3, "function_a", 12)
    assert bc_instr.offset == 12
    assert bc_instr.starts_line == 3
    assert bc_instr.opname == "JUMP_ABSOLUTE"

def test_get_example_ir_code():
    jitpath = os.path.join(os.path.dirname(__file__), "profiles/example.jitlog")
    forest = parse_jitlog(jitpath)
    trace = forest.get_trace_by_addr(140249103068976)
    ir_code = get_ir_code(trace.stages["opt"])
    expected_ir_code_7 = ["? = setfield_gc(p11, i44, @<FieldS pypy.module.__builtin__.functional.W_IntRangeIterator.inst_current 8>)",
                        "? = guard_not_invalidated(, @<ResumeGuardDescr object at 0x7f8e48c949e0>)",
                        "i48 = getfield_raw_i(140249191372576, @<FieldS pypysig_long_struct.c_value 0>)",
                        "i50 = int_sub(i48, 1)",
                        "? = setfield_raw(140249191372576, i50, @<FieldS pypysig_long_struct.c_value 0>)",
                        "i54 = int_lt(i50, 0)",
                        "? = guard_false(i54, @<ResumeGuardDescr object at 0x7f8e48c94a40>)"]
    
    assert len(ir_code) == 9
    for i, ir in enumerate(ir_code[7]):
        assert str(ir) == expected_ir_code_7[i]

