import sys
import time

import alpaca
from seer import Visitor, Builder

class LexerCallback():
    @classmethod
    def string(cls, string : str):
        return string.replace('\\n', '\n')[1 : -1]

def run(file_name : str):
    starttime = time.perf_counter_ns()
    config = alpaca.config.ConfigParser.run("grammar.gm")
    endtime = time.perf_counter_ns()

    print(f"Parsed config in {(endtime-starttime)/1000000} ms")

    with open(file_name, 'r') as f:
        txt = f.read()

        starttime = time.perf_counter_ns()
        tokens = alpaca.lexer.Lexer.run(txt, config, LexerCallback)
        endtime = time.perf_counter_ns()

        print(f"Lexer finished in {(endtime-starttime)/1000000} ms")

        # print("====================")
        # [print(t) for t in tokens]

    starttime = time.perf_counter_ns()
    ast = alpaca.parser.Parser.run(config, tokens, Builder, algo="cyk")
    endtime = time.perf_counter_ns()

    print(f"Parser finished in {(endtime-starttime)/1000000} ms")

    # print("====================") 
    # print(ast)

    starttime = time.perf_counter_ns()
    code = alpaca.compiler.Compiler.run(ast, txt, Visitor)
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
    runnable = make_runnable(code)

    with open("./build/test.ll", 'w') as f:
        f.write(runnable)
