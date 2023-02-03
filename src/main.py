from __future__ import annotations

import time
import subprocess
import argparse

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

    # PARSE GRAMMAR
    config = run_and_measure("ConfigParsing",
        alpaca.config.parser.run,
        filename="./src/python/python.gm")

    # TOKENIZE
    tokens = run_and_measure("Tokenizing",
        alpaca.lexer.run,
        text=txt.strip(), config=config, callback=eisen.EisenCallback)
    for t in tokens: print(t)

    asl = run_and_measure("Parser",
        alpaca.parser.run,
        config=config, tokens=tokens, builder=python.Builder())

    print(asl)

def run_c(filename: str):
    config = alpaca.config.parser.run("./src/c/grammar.gm")
    with open(filename, 'r') as f:
        txt = f.read()
    tokens = alpaca.lexer.run(text=txt, config=config, callback=c.Callback)
    asl = alpaca.parser.run(config=config, tokens=tokens, builder=c.Builder())
    print(asl)
    recovered_txt = c.Writer().run(asl)
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

    asl = run_and_measure("Parser",
        parser.parse,
        tokens=tokens)

    # Keep this exit to only parse
    # print(asl)
    # exit()

    # asl_str = ["  " + line for line in  str(asl).split("\n")]
    # print(*asl_str, sep="\n")

    # print("############## EISEN ###############")
    state = eisen.BaseState.create_initial(config, asl, txt, print_to_watcher=True)
    eisen.Workflow.steps.append(eisen.AstInterpreter)
    state = eisen.Workflow.execute_with_benchmarks(state)

    global_end = time.perf_counter_ns()
    print(f"elapsed in {(global_end-global_start)/1000000}")
    print(delim)
    print(state.watcher.txt)

    # Leave this exit here to prevent transpilation
    exit()
    input()
    asl = eisen.Flattener().run(state)
    state.asl = asl
    # print(state.asl)
    transmuted = eisen.CTransmutation(debug=False).run(asl, state)
    print(transmuted)

    # generate c code
    c_config = alpaca.config.parser.run("./src/c/grammar.gm")
    c_asl = alpaca.clr.CLRParser.run(c_config, transmuted)
    c_asl = eisen.DotDerefFilter().apply(c_asl)
    code = c.Writer().run(c_asl)
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

    asl = alpaca.types.parser.run(txt)
    print(asl)

def run_and_measure(name: str, f, *args, **kwargs):
    starttime = time.perf_counter_ns()
    result = f(*args, **kwargs)
    endtime = time.perf_counter_ns()
    print(f"{' '*(24-len(name))}{name}   {round((endtime-starttime)/1000000, 5)}")
    return result;

def run_eisen_tests(name: str):
    if name:
        status, msg = eisen.TestRunner.run_test_by_name(name)
        if status:
            print(f"ran test '{name}' successfully")
        else:
            print(msg)
    else:
        eisen.TestRunner.run_all_tests()

def debug():
    config = run_and_measure("ConfigParsing",
        alpaca.config.parser.run,
        filename="./src/eisen/grammar.gm")

    # READ FILE TO STR
    with open("./parsetest.txt", 'r') as f:
        txt = f.read()

    # TOKENIZE
    tokens = run_and_measure("Tokenizing",
        alpaca.lexer.run,
        text=txt, config=config, callback=eisen.EisenCallback)
    result = alpaca.parser.run(config, tokens, eisen.EisenBuilder())
    print(result)


if __name__ == "__main__":
    print(delim)
    print("-"*10, "BEGINS", "-"*10)
    print(delim)
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument("-t", "--test", action="store", type=str, nargs="?", const="")
    parser.add_argument("-b", "--build", action="store_true")
    parser.add_argument("-i", "--input", action="store", type=str)
    parser.add_argument("-l", "--lang",
        action="store",
        type=str,
        choices=["eisen", "python", "c", "types"],
        default="eisen")

    args = parser.parse_args()
    if args.test is not None:
        run_eisen_tests(args.test)
    elif args.input and args.lang:
        run(args.lang, args.input)
    elif args.build:
        eisen.TestRunner.rebuild_cache()
    elif args.debug:
        debug()

    print(delim)
