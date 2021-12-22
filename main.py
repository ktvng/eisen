import sys

from grammar import Grammar, CFGNormalizer, CYKAlgo, AstBuilder
from parser import Parser
from compiler.compiler import Compiler
from config import ConfigParser, Config
from lexer import Lexer

class LexerCallback():
    @classmethod
    def symbol(cls, symbol : str):
        return symbol

    @classmethod
    def keyword(cls, keyword : str):
        return keyword

    @classmethod
    def operator(cls, operator : str):
        return operator

    @classmethod
    def var(cls, var : str):
        return var

    @classmethod
    def string(cls, string : str):
        return string.replace('\\n', '\n')[1 : -1]


def run(file_name : str):
    config = ConfigParser.run("grammar.gm")

    # Grammar.load()
    # cfg = Grammar.implementation

    with open(file_name, 'r') as f:
        txt = f.read()
        tokens = Lexer.run(txt, config, LexerCallback)

        # print("====================")
        # for t in tokens:
        #     print(t.type + " " + t.value)

    normer = CFGNormalizer()
    cfg = normer.run(config.cfg)

    algo = CYKAlgo(cfg)
    algo.parse(tokens)

    # print("====================") 
    # print("PRODUCING RULES:")
    # for entry in algo.dp_table[-1][0]:
    #     print(entry.name)

    ab = AstBuilder(algo.asts, algo.dp_table)
    asthead = ab.run()

    # print("====================") 
    # asthead.print()

    cp = Compiler(asthead, txt)
    code = cp.run()

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
