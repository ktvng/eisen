from re import A
import sys
import time

import alpaca
from seer import Visitor, Builder, Callback, Builder2
import lamb

def run_lamb(filename : str):
    with open(filename, 'r') as f:
        txt = f.read()

    config = alpaca.config.ConfigParser.run("./src/lamb/grammar.gm")
    tokens = alpaca.lexer.run(txt, config, None)
    ast = alpaca.parser.run(config, tokens, lamb.Builder)
    # print(ast)

    fun = lamb.LambRunner()
    fun.run(ast)


def run(file_name : str):
    # print("="*80)
    # config = alpaca.config.ConfigParser.run("types.gm")
    # with open(file_name, 'r') as f:
    #     txt = f.read()
    # tokens = alpaca.lexer.run(txt, config, callback=None)
    # ast = alpaca.parser.run(config, tokens, builder=Builder)
    # # print(ast)
    # exit()
    

    # PARSE SEER CONFIG
    starttime = time.perf_counter_ns()
    config = alpaca.config.ConfigParser.run("grammar.gm")
    endtime = time.perf_counter_ns()
    print(f"Parsed config in {(endtime-starttime)/1000000} ms")

    # READ FILE TO STR
    with open(file_name, 'r') as f:
        txt = f.read()

    # TOKENIZE
    starttime = time.perf_counter_ns()
    tokens = alpaca.lexer.run(txt, config, Callback)
    endtime = time.perf_counter_ns()
    print(f"Lexer finished in {(endtime-starttime)/1000000} ms")

    # print("====================")
    # [print(t) for t in tokens]

    # PARSE TO AST
    starttime = time.perf_counter_ns()
    ast = alpaca.parser.run(config, tokens, Builder2, algo="cyk")
    endtime = time.perf_counter_ns()
    print(f"Parser finished in {(endtime-starttime)/1000000} ms")
    print(ast)

    exit()

    # print("====================") 
    # print(ast)

    # COMPILE TO IR
    starttime = time.perf_counter_ns()
    code = alpaca.compiler.run(ast, txt, Visitor)
    endtime = time.perf_counter_ns()
    print(f"Compiler finished in {(endtime-starttime)/1000000} ms")

    # print("====================")
    # print(code)
    
    return code

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
