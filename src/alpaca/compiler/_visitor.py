from error import Raise

def visitor(build_map, proc):
    if not proc.matches:
        Raise.code_error(f"{proc} requires matches field")
    for m in proc.matches:
        build_map[m] = proc

    return proc

