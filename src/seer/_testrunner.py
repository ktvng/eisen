from __future__ import annotations

from html.parser import HTMLParser
from os import walk
import time
from types import TracebackType

import alpaca

from seer._callback import SeerCallback
from seer._customparser import CustomParser
from seer._builder import SeerBuilder
from seer._params import Params
from seer._workflow import Workflow
from seer._ast_interpreter import AstInterpreter

class TestParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.current_data_context = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)

    def handle_endtag(self, tag: str) -> None:
        self.tags.pop()

    def handle_data(self, data: str) -> None:
        self.current_data_context[self.tags[-1]] = data

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.current_data_context[tag] = ""

    def feed(self, data: str) -> dict:
        self.current_data_context = {}
        super().feed(data)
        return self.current_data_context

class TestRunner():
    testdir = "./src/seer/tests2/"
    grammarfile = "./src/seer/grammar.gm"

    @classmethod
    def parse_asl(cls, test: dict) -> str:
        try:
            config = alpaca.config.parser.run(filename=TestRunner.grammarfile)
            tokens = alpaca.lexer.run(text=test["code"], config=config, callback=SeerCallback)
            asl = alpaca.parser.run(config, tokens, builder=SeerBuilder())
            return str(asl)
        except:
            return "error in parsing asl"

    @classmethod
    def run_test(cls, test: dict) -> tuple[bool, str]: 
        config = alpaca.config.parser.run(filename=TestRunner.grammarfile)
        tokens = alpaca.lexer.run(text=test["code"], config=config, callback=SeerCallback)
        asl = alpaca.parser.run(config, tokens, builder=SeerBuilder())
        # asl = CustomParser.run(config=config, toks=tokens, builder=SeerBuilder())
        params = Params.create_initial(config, asl, txt=test["code"])

        # Ignore the AstInterpreter
        for step in Workflow.steps[:-1]:
            step().apply(params)

        interpreter = AstInterpreter(redirect_output=True)
        interpreter.apply(params)
        if interpreter.stdout != test["expected"]:
            return False, f"expected, got:\n{test['expected']}\n-----\n{interpreter.stdout}"
        return True, "success"

    @classmethod
    def load_test(cls, filepath: str) -> dict:
        with open(TestRunner.testdir + filepath, 'r') as f:
            test_str = f.read()
        return TestParser().feed(test_str)

    @classmethod
    def run_all_tests(cls):
        start = time.perf_counter()
        successes = 0
        filenames = next(walk(TestRunner.testdir), (None, None, []))[2]
        for filename in filenames:
            test = cls.load_test(filepath=filename)
            try:
                status, msg = cls.run_test(test)
            except Exception as e:
                status, msg = False, f"unhandled exception: {e}\n"
                raise e
            if status:
                successes += 1
            else:
                msg += cls.parse_asl(test)
                print(f"test failed: {test['name']}")
                print("\n".join(["   " + l for l in msg.split("\n")]))

        end = time.perf_counter()
        total_tests= len(filenames)
        print(f"ran {total_tests} tests in {round(end-start, 4)}s, {successes}/{total_tests} ({round(100.0*successes/total_tests, 2)}%) succeeded")