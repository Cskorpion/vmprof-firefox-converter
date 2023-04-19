import os
from vmprofconvert import convert

def test_example():
    path = os.path.join(os.path.dirname(__file__), "example.prof")
    result = convert(path)
    


