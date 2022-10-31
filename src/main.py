from __future__ import annotations

import time
import subprocess
import argparse

import alpaca
import seer
import lamb
import c

delim = "="*64

def run_lamb(filename : str):
    with open(filename, 'r') as f:
        txt = f.read()

    config = alpaca.config.parser.run("./src/lamb/grammar.gm")
    tokens = alpaca.lexer.run(txt, config, None)
    ast = alpaca.parser.run(config, tokens, lamb.LambBuilder())
    print(ast)

    # fun = lamb.LambRunner()
    # fun.run(ast)

def run_c(filename: str):
    # PARSE SEER CONFIG
    config = run_and_measure("config parsed",
        alpaca.config.parser.run,
        filename="./src/c/grammar.gm")

    # READ FILE TO STR
    with open(filename, 'r') as f:
        txt = f.read()
    
    # TOKENIZE
    tokens = run_and_measure("tokenizer",
        alpaca.lexer.run,
        text=txt, config=config, callback=seer.SeerCallback)

    # print("====================")
    # [print(t) for t in tokens]

    # PARSE TO AST
    asl = run_and_measure("parser",
        alpaca.parser.run,
        config=config, tokens=tokens, builder=c.Builder(), algo="cyk")

    asl_str = [">    " + line for line in  str(asl).split("\n")]
    print(*asl_str, sep="\n")
    parts = c.Writer().apply(asl)
    txt = "".join(parts)
    txt = alpaca.utils.formatter.indent(txt)
    print(txt)

def pretty_print_perf(perf: list[tuple[str, int]]):
    longest_name_size = max(len(x[0]) for x in perf)
    block_size = longest_name_size + 4
    for name, val in perf:
        print(" "*(block_size - len(name)), name, " ", val)

    print(" "*(block_size-len("Total")), "Total", " ", sum(x[1] for x in perf))

def run_seer(filename: str):
    perf = []
    # PARSE SEER CONFIG
    config = run_and_measure("config parsed",
        alpaca.config.parser.run,
        filename="./src/seer/grammar.gm")

    # READ FILE TO STR
    with open(filename, 'r') as f:
        txt = f.read()
    
    # TOKENIZE
    tokens = run_and_measure("tokenizer",
        alpaca.lexer.run,
        text=txt, config=config, callback=seer.SeerCallback)

    

    # print("====================")
    # [print(t) for t in tokens]

    # # CUSTOM PARSER
    # start = time.perf_counter_ns()
    # asl = run_and_measure("customparser2",
    #     seer.CustomParser2(config).parse,
    #     toks=tokens)
    # print(asl)
    # exit()
    # perf.append(("CustomParser", (end-start)/1000000))

    # PARSE TO AST
    asl = run_and_measure("parser",
        alpaca.parser.run,
        config=config, tokens=tokens, builder=seer.SeerBuilder(), algo="cyk")

    asl_str = [">    " + line for line in  str(asl).split("\n")]
    print(*asl_str, sep="\n")

    print("############ STANZA ###############")
    params = seer.Params.create_initial(config, asl, txt)

    for step in seer.Workflow.steps:
        print(step.__name__)
        start = time.perf_counter_ns()
        step().apply(params)
        end = time.perf_counter_ns()
        perf.append((step.__name__, (end-start)/1000000))

    print("========")
    for t in params.mod.typeclasses:
        print(t)
    print("========")
    pretty_print_perf(perf)

    exit()
    seer.ModuleWrangler(debug=False).apply(params)
    mod = params.mod
    try:
        seer.TypeFlowWrangler(debug=False).apply(params)
    except Exception as e:
        print(params.mod)
        raise e

    print("############ STANZA ###############")
    print(params.asl)

    c_config = run_and_measure("interpreter ran",
        seer.AstInterpreter().apply,
        params=params)
    exit()



    asl = seer.Flattener().run(params)
    print(asl)
    # exit()
    # seer.Inspector().apply(params)

    transmuted = seer.CTransmutation(debug=False).run(asl, params)
    print("############ TRANSMUATION ###############")

    c_config = run_and_measure("config parsed",
        alpaca.config.parser.run,
        filename="./src/c/grammar.gm")
    c_asl = alpaca.clr.CLRParser.run(c_config, transmuted)

    seer.DotDerefFilter().apply(c_asl)
    print(c_asl)
    # print("############ C_ASL ###############")
    # print(c_asl)

    print("############ C_OUTPUT ###############")
    code = c.Writer().run(c_asl)
    with open("build/test.c", 'w') as f:
        f.write(code)

    # run tests
    subprocess.run(["gcc", "./build/test.c", "-o", "./build/test"])
    x = subprocess.run(["./build/test"], capture_output=True)
    got = x.stdout.decode("utf-8") 

    print("############ PROGRAM OUTPUT ###############")
    print(got)
    exit()

    print("SUCCESS")
    bits = seer.CodeTransducer().apply(params)
    print("".join(bits))
    # end

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
    print(f"|  - {name} finished in {(endtime-starttime)/1000000} ms")
    return result;

def run_seer_tests(name: str):
    if name:
        status, msg = seer.TestRunner.run_test_by_name(name)
        if status:
            print(f"ran test '{name}' successfully")
        else:
            print(msg)
    else:
        seer.TestRunner.run_all_tests()
    # internal_run_tests("./src/seer/tests/validator_tests.rs", should_transpile=False)
    # input()
    # internal_run_tests("./src/seer/tests/test.rs")

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
    parser.add_argument("-t", "--test", action="store", type=str, nargs="?", const="")
    parser.add_argument("-b", "--build", action="store_true")
    parser.add_argument("-i", "--input", action="store", type=str)
    parser.add_argument("-l", "--lang", 
        action="store", 
        type=str, 
        choices=["seer", "lamb", "c", "types"],
        default="seer")

    args = parser.parse_args()

    print(args.test)
    if args.test is not None:
        run_seer_tests(args.test)
    elif args.input and args.lang:
        run(args.lang, args.input)
    elif args.build:
        seer.TestRunner.rebuild_cache()

    print(delim)
    