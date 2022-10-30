from __future__ import annotations

from os import walk
import time
import json
import traceback

import alpaca

from seer.parsing.callback import SeerCallback
from seer.parsing.customparser import CustomParser
from seer.parsing.builder import SeerBuilder
from seer.common.params import Params
from seer.validation.workflow import Workflow
from seer.ast_interpreter import AstInterpreter

class Test():
    testdir = "./src/seer/tests/"
    grammarfile = "./src/seer/grammar.gm"

    def __init__(self, name: str):
        self.name = name
        with open(Test.testdir + name + ".json", 'r') as f:
            self.metadata = json.loads(f.read())

        with open(Test.testdir + name + ".rs", 'r') as f:
            self.code = f.read()

    def parse_asl(self): 
        config = alpaca.config.parser.run(filename=Test.grammarfile)
        tokens = alpaca.lexer.run(text=self.code, config=config, callback=SeerCallback)
        return alpaca.parser.run(config, tokens, builder=SeerBuilder())

    def run(self) -> tuple[bool, str]:
        asl = self.parse_asl()
        config = alpaca.config.parser.run(filename=Test.grammarfile)
        params = Params.create_initial(config, asl, txt=self.code)
        for step in Workflow.steps[:-1]:
            step().apply(params)

        interpreter = AstInterpreter(redirect_output=True)
        interpreter.apply(params)
        if self.metadata["expected"]["success"]:
            expected_output = self.metadata["expected"]["output"]
            if interpreter.stdout != expected_output:
                return False, f"expected, got:\n{expected_output}\n-----\n{interpreter.stdout}\n-----\n"
        return True, "success"

class TestParser():
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
    testdir = "./src/seer/tests/"
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
    def run_test_by_name(cls, name: str):
        test = Test(name)
        try: 
            status, msg = test.run()
        except Exception as e:
            try: 
                status, msg = False, f"unhandled exception: {e} {traceback.format_exc()}\n" + str(test.parse_asl())
            except:
                status, msg = False, f"!! could not parse asl"
        return status, msg

    @classmethod
    def run_all_tests(cls):
        start = time.perf_counter()
        successes = 0
        filenames = next(walk(TestRunner.testdir), (None, None, []))[2]
        test_files = [f for f in filenames if f.endswith(".json")]
        for filename_and_ext in test_files:
            testname = filename_and_ext.split(".")[0]
            status, msg = cls.run_test_by_name(testname)
            
            if status:
                successes += 1
            else:
                print(f"test failed: {testname}")
                print("\n".join(["   " + l for l in msg.split("\n")]))

            # test = cls.load_test(filepath=filename)
            # try:
            #     status, msg = cls.run_test(test)
            # except Exception as e:
            #     status, msg = False, f"unhandled exception: {e}\n"
            #     raise e
            # if status:
            #     successes += 1
            # else:
            #     msg += cls.parse_asl(test)
            #     print(f"test failed: {test['name']}")
            #     print("\n".join(["   " + l for l in msg.split("\n")]))

        end = time.perf_counter()
        total_tests= len(test_files)
        print(f"ran {total_tests} tests in {round(end-start, 4)}s, {successes}/{total_tests} ({round(100.0*successes/total_tests, 2)}%) succeeded")
        