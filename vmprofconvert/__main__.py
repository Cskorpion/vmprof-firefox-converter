import sys
import json
from vmprofconvert import convert_vmprof

path = sys.argv[1]
c = convert_vmprof(path)
with open(path + ".json", "w") as output_file:
    output_file.write(json.dumps(json.loads(c.dumps()), indent=2))