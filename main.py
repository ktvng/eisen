from grammar import Grammar, CFGNormalizer, CYKAlgo, AstBuilder
from parser import Parser
import sandbox

tokens = []
with open("test.txt", 'r') as f:
    txt = f.read()
    tokens = Parser.tokenize(txt)
    for t in tokens:
        print(t.type + " " + t.value)

    print("====================")
    # Parser.lex(tokens)

Grammar.load()
normer = CFGNormalizer()
cnf = normer.run(Grammar.grammar_implementation)
print(f"CNF starting symbol is: {cnf.start}")
for rule in cnf.rules:
    print(rule.parent + " -> " + " ".join(rule.pattern))

print("====================")
algo = CYKAlgo(cnf)
algo.parse(tokens)

for entry in algo.dp_table[-1][0]:
    print(entry.name)

print("====================")
ab = AstBuilder(algo.asts, algo.dp_table)
x = ab.run()
print(len(x))
print("====================")
x[0].rsprint()


# sandbox.play()