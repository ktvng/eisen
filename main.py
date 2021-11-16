from grammar import Grammar, CFGNormalizer, CYKAlgo, AstBuilder
from parser import Parser
from compiler import Compiler
import sandbox

tokens = []
with open("test.txt", 'r') as f:
    txt = f.read()
    tokens = Parser.tokenize(txt)

    print("====================")
    for t in tokens:
        print(t.type + " " + t.value)

Grammar.load()
normer = CFGNormalizer()
cnf = normer.run(Grammar.grammar_implementation)

# print("====================")
# print(f"CNF starting symbol is: {cnf.start}")
# for rule in cnf.rules:
#     print(rule.parent + " -> " + " ".join(rule.pattern))

print("====================")
algo = CYKAlgo(cnf)
algo.parse(tokens)

print("PRODUCING RULES:")
for entry in algo.dp_table[-1][0]:
    print(entry.name)

print("====================")
ab = AstBuilder(algo.asts, algo.dp_table)
x = ab.run()
x.rsprint()

print("====================")
cp = Compiler(x)
code = cp.run()
print(code)

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

runnable = make_runnable(code)

with open("./build/test.ll", 'w') as f:
    f.write(runnable)



# sandbox.play()