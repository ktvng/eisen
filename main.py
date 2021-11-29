from grammar import Grammar, CFGNormalizer, CYKAlgo, AstBuilder
from parser import Parser
from compiler import Compiler

def run(file_name : str):
    Grammar.load()
    cfg = Grammar.implementation

    # print("====================")
    # print(f"CNF starting symbol is: {cfg.start}")
    # for rule in cfg.rules:
    #     print(rule.production_symbol + " -> " + " ".join(rule.pattern))

    with open(file_name, 'r') as f:
        txt = f.read()
        tokens = Parser.tokenize(txt)

        # print("====================")
        # for t in tokens:
        #     print(t.type + " " + t.value)

    algo = CYKAlgo(cfg)
    algo.parse(tokens)

    # print("====================") 
    # print("PRODUCING RULES:")
    # for entry in algo.dp_table[-1][0]:
    #     print(entry.name)

    ab = AstBuilder(algo.asts, algo.dp_table)
    asthead = ab.run()

    print("====================") 
    asthead.print()

    cp = Compiler(asthead, txt)
    code = cp.run()

    print("====================")
    print(code)
    
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

code = run("test.rs")
runnable = make_runnable(code)

with open("./build/test.ll", 'w') as f:
    f.write(runnable)
