from __future__ import annotations

import time
import subprocess
import argparse
import pathlib
import os

import alpaca
import eisen
import c
import python

delim = "="*28

def run_python(filename: str):
    # READ FILE TO STR
    with open(filename, 'r') as f:
        txt = f.read()
    txt = python.Preprocessor.run(txt)
    # print(txt)

    # PARSE GRAMMAR
    config = run_and_measure("ConfigParsing",
        alpaca.config.parser.run,
        filename="./src/python/python.gm")

    # TOKENIZE
    tokens = run_and_measure("Tokenizing",
        alpaca.lexer.run,
        text=txt.strip(), config=config, callback=eisen.EisenCallback)
    # for t in tokens: print(t)

    ast = run_and_measure("Parser",
        alpaca.parser.run,
        config=config, tokens=tokens, builder=python.Builder())

    print(ast)
    proto_code = python.Writer().run(ast)
    code = python.PostProcessor.run(proto_code)
    print(code)

def run_c(filename: str):
    config = alpaca.config.parser.run("./src/c/grammar.gm")
    with open(filename, 'r') as f:
        txt = f.read()
    tokens = alpaca.lexer.run(text=txt, config=config, callback=c.Callback)
    ast = alpaca.parser.run(config=config, tokens=tokens, builder=c.Builder())
    print(ast)
    recovered_txt = c.Writer().run(ast)
    print()
    print(recovered_txt)

def run_eisen(filename: str):
    global_start = time.perf_counter_ns()
    config = run_and_measure("ConfigParsing",
        alpaca.config.parser.run,
        filename="./src/eisen/grammar.gm")

    # READ FILE TO STR
    with open(filename, 'r') as f:
        txt = f.read()

    # TOKENIZE
    tokens = run_and_measure("Tokenizing",
        alpaca.lexer.run,
        text=txt.strip(), config=config, callback=eisen.EisenCallback)
    # for t in tokens: print(t)

    parser = run_and_measure("InitParser",
        eisen.SuperParser,
        config=config)

    ast = run_and_measure("Parser",
        parser.parse,
        tokens=tokens)

    # Keep this exit to only parse
    print(ast)
    # exit()

    state = eisen.BaseState.create_initial(config, ast, txt, print_to_watcher=True)
    _, state = eisen.Workflow.execute_with_benchmarks(state)

    global_end = time.perf_counter_ns()
    print(f"elapsed in {(global_end-global_start)/1000000}")
    print(delim)
    print(state.watcher.txt)


    if state.watcher.txt:
        exit()

    ast = eisen.ToPython().run(state)
    # print(ast)

    proto_code = python.Writer().run(ast)
    code = eisen.ToPython.builtins + python.PostProcessor.run(proto_code) + eisen.ToPython.lmda + "\n_main___Fd_void_I_void_b()"
    with open("./build/test.py", 'w') as f:
        f.write(code)

    # Leave this exit here to prevent transpilation
    subprocess.run(["python", "./build/test.py"])

    print()
    print("done")
    exit()
    ast = eisen.Flattener().run(state)
    state.ast = ast
    # print(state.get_ast())
    transmuted = eisen.CTransmutation(debug=False).run(ast, state)
    print(transmuted)

    # generate c code
    c_config = alpaca.config.parser.run("./src/c/grammar.gm")
    c_ast = alpaca.clr.CLRParser.run(c_config, transmuted)
    c_ast = eisen.DotDerefFilter().apply(c_ast)
    code = c.Writer().run(c_ast)
    code = "#include <stdio.h> \n" + code
    # print(code)
    with open("./build/test.c", 'w') as f:
        f.write(code)

    # run c code
    subprocess.run(["gcc", "./build/test.c", "-o", "./build/test"])
    x = subprocess.run(["./build/test"], capture_output=True)
    got = x.stdout.decode("utf-8")
    print(got)


def run(lang: str, filename: str):
    if lang == "python":
        run_python(filename)
    elif lang == "eisen":
        run_eisen(filename)
    elif lang == "c":
        run_c(filename)
    elif lang == "types":
        run_types(filename)

def run_types(filename: str):
    with open(filename, 'r') as f:
        txt = f.read()

    ast = alpaca.types.parser.run(txt)
    print(ast)

def run_and_measure(name: str, f, *args, **kwargs):
    starttime = time.perf_counter_ns()
    result = f(*args, **kwargs)
    endtime = time.perf_counter_ns()
    print(f"{' '*(24-len(name))}{name}   {round((endtime-starttime)/1000000, 5)}")
    return result;

def run_eisen_tests(name: str, verbose: bool):
    if name:
        status, msg = eisen.TestRunner.run_test_by_name(name)
        if status:
            print(f"ran test '{name}' successfully")
        else:
            print(msg)
    else:
        eisen.TestRunner.run_all_tests(verbose)

def debug():
    run_eisen("test.txt")

def add_test(name: str):
    tomlheader = """
/// [Test]
/// name = "{0}"
/// info = \"\"\"\\
///     _description_
/// \"\"\"

/// [Expects]
/// success = _
/// output = ""

/// [[Expects.Exceptions]]
/// type = ""
/// contains = ""
"""
    testpath = "./src/eisen/tests/"
    full_path = testpath + name + ".en"
    path = pathlib.Path(full_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        print("INFO: test already exists, not creating it again.")
        return

    with open(full_path, 'w') as f:
        f.write(tomlheader.format(name))
    subprocess.run(["code", "-r", full_path])



if __name__ == "__main__":
    print(delim)
    print("-"*10, "BEGINS", "-"*10)
    print(delim)
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument("-t", "--test", action="store", type=str, nargs="?", const="")
    parser.add_argument("-v", "--verbose", action="store_true", default=False)
    parser.add_argument("-b", "--build", action="store_true")
    parser.add_argument("-i", "--input", action="store", type=str)
    parser.add_argument("-a", "--add-test", action="store_true")
    parser.add_argument("-l", "--lang",
        action="store",
        type=str,
        choices=["eisen", "python", "c", "types"],
        default="eisen")

    args = parser.parse_args()
    if args.add_test:
        add_test(args.test)
    elif args.test is not None:
        run_eisen_tests(args.test, args.verbose)
    elif args.input and args.lang:
        run(args.lang, args.input)
    elif args.build:
        eisen.TestRunner.rebuild_cache()
    elif args.debug:
        debug()

    print(delim)
