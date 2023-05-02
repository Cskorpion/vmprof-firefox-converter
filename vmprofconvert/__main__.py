import sys
import json
from vmprofconvert import convert_stats

path = sys.argv[1]
with open(path + ".json", "w") as output_file:
    output_file.write(json.dumps(json.loads(convert_stats(path)), indent=2))