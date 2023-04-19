import vmprof

def convert(path):
    stats = vmprof.read_profile(path)
    return stats
