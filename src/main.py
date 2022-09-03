import re
import sys
import time
import subprocess
import argparse

import alpaca
from seer import SeerCallback, SeerBuilder, SeerValidator, SeerIndexer, SeerTranspiler
import lamb
import seer

from seer._listir import ListIRParser

delim = "="*64

def run_lamb(filename : str):
    with open(filename, 'r') as f:
        txt = f.read()

    config = alpaca.config.ConfigParser.run("./src/lamb/grammar.gm")
    tokens = alpaca.lexer.run(txt, config, None)
    ast = alpaca.parser.run(config, tokens, lamb.LambBuilder())
    print(ast)

    # fun = lamb.LambRunner()
    # fun.run(ast)

def run_seer(filename: str):
    # PARSE SEER CONFIG
    config = run_and_measure("config parsed",
        alpaca.config.ConfigParser.run,
        filename="./src/seer/grammar.gm")

    # READ FILE TO STR
    with open(filename, 'r') as f:
        txt = f.read()
    
    # TOKENIZE
    tokens = run_and_measure("tokenizer",
        alpaca.lexer.run,
        text=txt, config=config, callback=SeerCallback)

    # print("====================")
    # [print(t) for t in tokens]

    # PARSE TO AST
    asl = run_and_measure("parser",
        alpaca.parser.run,
        config=config, tokens=tokens, builder=SeerBuilder(), algo="cyk")

    asl_str = [">    " + line for line in  str(asl).split("\n")]
    print(*asl_str, sep="\n")

    # KXT testing
    params = seer.ModuleTransducer.init_params(config, asl, txt)
    seer.ModuleTransducer().apply(params)
    mod = params.mod
    try:
        seer.TypeFlowTransducer().apply(params)
    except Exception as e:
        print(params.mod)
        raise e

    print("SUCCESS")
    bits = seer.CodeTransducer().apply(params)
    print("".join(bits))

    params = SeerValidator.init_params(config, asl, txt)
    mod = run_and_measure("validator",
        alpaca.validator.run,
        indexer_function=SeerIndexer(), validation_function=SeerValidator(), params=params)

    if mod is None:
        raise Exception("Failed to validate and produce a module.")

    code = run_and_measure("transpiler",
        SeerTranspiler().run,
        config=config, asl=asl, mod=mod)

    with open("build/test.c", 'w') as f:
        f.write(code)

    # run tests
    subprocess.run(["gcc", "./build/test.c", "-o", "./build/test"])
    x = subprocess.run(["./build/test"], capture_output=True)
    got = x.stdout.decode("utf-8") 

    got_str = [">    " + line for line in got.split("\n")]
    print(*got_str, sep="\n")

def run(lang: str, filename: str):
    if lang == "lamb":
        run_lamb(filename)
    elif lang == "seer":
        run_seer(filename)

def internal_run_tests(filename: str, should_transpile=True):
    # PARSE SEER CONFIG
    config = run_and_measure("config parsed",
        alpaca.config.ConfigParser.run,
        filename="./src/seer/grammar.gm")

    # READ FILE TO STR
    with open(filename, 'r') as f:
        txt = f.read()
    
    failure_count = 0
    test_count = 0
    txt_chunks = re.split(r"\/\/ *#\d+ *([\w ]+ *\n)", txt)
    for i in range(1, len(txt_chunks), 2):
        expected = txt_chunks[i+1].split('\n')[0][2:].strip()
        print(delim)
        print(f"| Testing: #{i//2} {txt_chunks[i]}", end="")
        chunk = txt_chunks[i+1]

        # TOKENIZE
        tokens = run_and_measure("tokenizer",
            alpaca.lexer.run,
            text=chunk, config=config, callback=SeerCallback)

        # print("====================")
        # [print(t) for t in tokens]

        # PARSE TO AST
        asl = run_and_measure("parser",
            alpaca.parser.run,
            config=config, tokens=tokens, builder=SeerBuilder(), algo="cyk")

        asl_str = ["|    " + line for line in  str(asl).split("\n")]
        print(*asl_str, sep="\n")

        params = SeerValidator.init_params(config, asl, txt)
        mod = run_and_measure("validator",
            alpaca.validator.run,
            indexer_function=SeerIndexer(), validation_function=SeerValidator(), params=params)

        if mod is None:
            raise Exception("Failed to validate and produce a module.")

        if should_transpile:
            code = run_and_measure("transpiler",
                SeerTranspiler().run,
                config=config, asl=asl, mod=mod)

            with open("build/test.c", 'w') as f:
                f.write(code)

            # run tests
            subprocess.run(["gcc", "./build/test.c", "-o", "./build/test"])
            x = subprocess.run(["./build/test"], capture_output=True)
            got = x.stdout.decode("utf-8") 
            is_expected = got == expected
            if is_expected:
                print(f"| SUCCESS")
            else:
                print(f"| FAILED, expected {expected} but got {got}")
                failure_count += 1

        test_count +=1
        
    if failure_count == 0:
        print(delim, f"\nSuccess! All tests passed ({test_count}/{test_count})")
    else:
        print(delim, f"\n{failure_count}/{test_count} test failed!")

def run_and_measure(name: str, f, *args, **kwargs):
    starttime = time.perf_counter_ns()
    result = f(*args, **kwargs)
    endtime = time.perf_counter_ns()
    print(f"|  - {name} finished in {(endtime-starttime)/1000000} ms")
    return result;

def run_seer_tests():
    internal_run_tests("./src/seer/tests/validator_tests.rs", should_transpile=False)
    input()
    internal_run_tests("./src/seer/tests/test.rs")

def make_runnable(txt : str):
    lines = txt.split("\n")
    readable = ""
    for line in lines:
        if "target triple" in line:
            readable += 'target triple = "x86_64-pc-linux-gnu"\n'
            continue
        elif "target datalayout" in line:
            readable += 'target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"\n'
            continue
        readable += line + "\n"
    return readable


if __name__ == "__main__":
    print(delim)
    print("-"*28, "BEGINS", "-"*28)
    print(delim)
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--test", action="store_true")
    parser.add_argument("-i", "--input", action="store", type=str)
    parser.add_argument("-l", "--lang", 
        action="store", 
        type=str, 
        choices=["seer", "lamb"],
        default="seer")

    args = parser.parse_args()

    if args.test:
        run_seer_tests()
    elif args.input and args.lang:
        run(args.lang, args.input)

    print(delim)
    