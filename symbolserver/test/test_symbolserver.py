import os
from symbolserver import get_jitlog_ir 

def test_get_jitlog_ir():
    path = os.path.join(os.path.dirname(__file__), "profiles/pypy-pystone.prof.jit")
    asm = get_jitlog_ir(path, 140682485974400)
    assert len(asm) == 44

def test_get_empty_jitlog_ir():
    path = os.path.join(os.path.dirname(__file__), "profiles/pypy-pystone.prof.jit")
    asm = get_jitlog_ir(path, 115)# no ir for addr 115
    assert asm == []