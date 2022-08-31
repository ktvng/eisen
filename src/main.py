import re
import sys
import time
import subprocess

import alpaca
from seer import SeerCallback, SeerBuilder, SeerValidator, SeerIndexer, SeerTranspiler
import lamb

from seer._listir import ListIRParser

def run_lamb(filename : str):
    with open(filename, 'r') as f:
        txt = f.read()

    config = alpaca.config.ConfigParser.run("./src/lamb/grammar.gm")
    tokens = alpaca.lexer.run(txt, config, None)
    ast = alpaca.parser.run(config, tokens, lamb.Builder)
    # print(ast)

    fun = lamb.LambRunner()
    fun.run(ast)

def internal_run_tests(filename: str, should_transpile=True):
    delim = "="*64
    # PARSE SEER CONFIG
    starttime = time.perf_counter_ns()
    config = alpaca.config.ConfigParser.run("grammar.gm")
    endtime = time.perf_counter_ns()
    print(f"Parsed config in {(endtime-starttime)/1000000} ms")

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
        starttime = time.perf_counter_ns()
        tokens = alpaca.lexer.run(chunk, config, SeerCallback)
        endtime = time.perf_counter_ns()
        print(f"|  - Lexer finished in {(endtime-starttime)/1000000} ms")

        # print("====================")
        # [print(t) for t in tokens]

        # PARSE TO AST
        starttime = time.perf_counter_ns()
        ast = alpaca.parser.run(config, tokens, SeerBuilder(), algo="cyk")
        endtime = time.perf_counter_ns()
        print(f"|  - Parser finished in {(endtime-starttime)/1000000} ms")
        print(ast)
        # print(f"| Output:\n")
        # print(ast)
        # print()

        starttime = time.perf_counter_ns()
        params = SeerValidator.init_params(config, ast, txt)
        mod = alpaca.validator.run(SeerIndexer(), SeerValidator(), params)
        endtime = time.perf_counter_ns()
        print(f"|  - Validator finished in {(endtime-starttime)/1000000} ms")

        if mod is None:
            exit()

        if should_transpile:
            starttime = time.perf_counter_ns()
            txt = SeerTranspiler().run(config, ast, mod)
            endtime = time.perf_counter_ns()
            print(f"|  - Transpiler finished in {(endtime-starttime)/1000000} ms")
            with open("build/test.c", 'w') as f:
                f.write(txt)

            # run tests
            subprocess.run(["gcc", "./build/test.c", "-o", "./build/test"])
            x = subprocess.run(["./build/test"], capture_output=True)
            got = x.stdout.decode("utf-8") 
            is_expected = got == expected
            if is_expected:
                print(f"| Result: SUCCESS!")
            else:
                print(f"| Result: FAILED, expected {expected} but got {got}")
                failure_count += 1
        
        test_count +=1
        
    if failure_count == 0:
        print(delim, "\nSuccess! All tests passed\n")
    else:
        print(delim, f"\n{failure_count}/{test_count} test failed!")

def run_seer_tests():
    internal_run_tests("./src/seer/tests/validator_tests.rs", should_transpile=False)
    input()
    internal_run_tests("./src/seer/tests/test.rs")


def run(file_name : str):
    # print("="*80)
    # config = alpaca.config.ConfigParser.run("types.gm")
    # with open(file_name, 'r') as f:
    #     txt = f.read()
    # tokens = alpaca.lexer.run(txt, config, callback=None)
    # ast = alpaca.parser.run(config, tokens, builder=Builder)
    # # print(ast)
    # exit()

    run_seer_tests()
    exit()

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
    if len(sys.argv) != 2:
        print("Error: expected filename as argument")
        exit()
    
    filename = sys.argv[1]
    code = run(filename)
    # run_lamb(filename)
    runnable = make_runnable(code)

    with open("./build/test.ll", 'w') as f:
        f.write(runnable)
