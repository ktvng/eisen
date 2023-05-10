from __future__ import annotations

from os import walk
import time
import sys
import json
import traceback
import multiprocessing
import subprocess

import alpaca
import python
from alpaca.concepts import AbstractException
from alpaca.utils import VisitorException

from eisen.parsing.callback import EisenCallback
from eisen.parsing.builder import EisenBuilder
from eisen.parsing.superparser import SuperParser
from eisen.state.basestate import BaseState
from eisen.validation.workflow import Workflow
from eisen.interpretation.ast_interpreter import AstInterpreter
from eisen.conversion.to_python import ToPython

class StaticParser():
    grammarfile = "./src/eisen/grammar.gm"
    config = alpaca.config.parser.run(filename=grammarfile)
    parser = SuperParser(config)

# TODO: refactor this
class Test():
    testdir = "./src/eisen/tests/"
    cachedir = "./src/eisen/tests/cache/"
    grammarfile = "./src/eisen/grammar.gm"

    def __init__(self, name: str):
        self.name = name
        with open(Test.testdir + name + ".json", 'r') as f:
            self.metadata = json.loads(f.read())

        with open(Test.testdir + name + ".rs", 'r') as f:
            self.code = f.read()

    def parse_asl_with_cache(self):
        # config = alpaca.config.parser.run(filename=Test.grammarfile)
        # if os.path.exists(self.cachedir + self.name):
        #     with open(self.cachedir + self.name, "r") as f:
        #         asl_str = f.read()
        #         print(asl_str)
        #     return alpaca.clr.CLRParser.run(config, asl_str)
        return self.parse_asl()

    def parse_asl(self):
        config = alpaca.config.parser.run(filename=Test.grammarfile)
        tokens = alpaca.lexer.run(text=self.code.strip(), config=StaticParser.config, callback=EisenCallback)
        # asl = alpaca.parser.run(config, tokens, builder=EisenBuilder())
        asl = SuperParser(config).parse(tokens)
        # asl = StaticParser.parser.parse(tokens)
        return asl

    @classmethod
    def _make_exception_error_msg(cls, e, state: BaseState):
        exception_type = e["type"]
        contents = e["contains"]
        return f"expected to encounter exception '{exception_type}' containing:\n{contents}\nbut got:\n-----\n{state.watcher.txt}\n-----\n"

    def run(self) -> tuple[bool, str]:
        orignal_hook = sys.excepthook
        def exceptions_hook(e_type, e_value: Exception, tb):
            if e_type == VisitorException:
                orignal_hook(e_type, e_value.with_traceback(None), None)
            else:
                orignal_hook(e_type, e_value, tb)

        sys.excepthook = exceptions_hook

        asl = self.parse_asl_with_cache()
        config = alpaca.config.parser.run(filename=Test.grammarfile)
        state = BaseState.create_initial(config, asl, txt=self.code, print_to_watcher=True)
        succeeded, state = Workflow.execute(state)
        if self.metadata["expected"]["success"]:
            if not succeeded:
                print(state.watcher.txt)
                print(state.asl)
                return False, "test failed due to exception"

            asl = ToPython().run(state)
            proto_code = python.Writer().run(asl)
            proto_code = python.Writer().run(asl)
            code = python.PostProcessor.run(proto_code) + ToPython.lmda + "\n_main___Fd_void_I_void_b()"
            fname= f"./build/{self.name}.py"
            with open(fname, 'w') as f:
                f.write(code)
            bytes = subprocess.check_output(["python3", fname])
            gotten_output = bytes.decode()
            # interpreter = AstInterpreter()
            # interpreter.run(state)
            expected_output = self.metadata["expected"]["output"]
            if not self.metadata["expected"].get("match_case", True):
                gotten_output = gotten_output.lower()
                expected_output = expected_output.lower()
            if gotten_output != expected_output:
                return False, f"expected, got:\n{expected_output}\n-----\n{gotten_output}\n-----\n"
            # if state.watcher.txt != expected_output:
                # return False, f"expected, got:\n{expected_output}\n-----\n{interpreter.stdout}\n-----\n"
        else:
            expected_exceptions = self.metadata["expected"]["exceptions"]
            got_number_of_exceptions = state.watcher.txt.count(AbstractException.delineator)
            if len(expected_exceptions) != got_number_of_exceptions:
                return False, f"expected ({len(expected_exceptions)}) exceptions but got ({got_number_of_exceptions}) in: \n{state.watcher.txt}"
            txt = state.watcher.txt
            for e in expected_exceptions:
                if e["type"] not in txt or e["contains"] not in txt:
                    return False, Test._make_exception_error_msg(e, state)
                txt = txt.replace(e["type"], "", 1)
                txt = txt.replace(e["contains"], "", 1)

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
    testdir = "./src/eisen/tests/"
    cachedir = "./src/eisen/tests/cache/"
    grammarfile = "./src/eisen/grammar.gm"

    @classmethod
    def parse_asl(cls, test: dict) -> str:
        try:
            config = alpaca.config.parser.run(filename=TestRunner.grammarfile)
            tokens = alpaca.lexer.run(text=test["code"], config=config, callback=EisenCallback)
            asl = alpaca.parser.run(config, tokens, builder=EisenBuilder())
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
    def get_all_test_names(cls) -> list[str]:
        filenames = next(walk(TestRunner.testdir), (None, None, []))[2]
        test_files = [f for f in filenames if f.endswith(".json")]
        return [t.split(".")[0] for t in test_files]

    @classmethod
    def run_all_tests_threadpooled(cls):
        start = time.perf_counter()
        tests = cls.get_all_test_names()
        with multiprocessing.Pool(8) as p:
            data: list[str] = p.map(cls.run_test_in_thread, tests)

        successes = data.count("success!")
        msg = "\n".join([m for m in data if m != "success!"])
        print(msg)
        end = time.perf_counter()
        total_tests= len(tests)
        print(f"finished in {round(end-start, 4)}s\n{successes}/{total_tests} ({round(100.0*successes/total_tests, 2)}%) succeeded")

    @classmethod
    def run_test_in_thread(cls, testname: str) -> tuple[bool, str]:
        status, msg = cls.run_test_by_name(testname)
        msg_to_sender = "success!"
        if not status:
            msg_to_sender = f"test failed: {testname}\n" + "\n".join(["   " + l for l in msg.split("\n")])

        return msg_to_sender

    @classmethod
    def run_all_tests(cls):
        cls.run_all_tests_threadpooled()
        return
        start = time.perf_counter()
        successes = 0
        tests = cls.get_all_test_names()
        for testname in tests:
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
        total_tests= len(tests)
        print(f"ran {total_tests} tests in {round(end-start, 4)}s, {successes}/{total_tests} ({round(100.0*successes/total_tests, 2)}%) succeeded")

    @classmethod
    def rebuild_cache(cls):
        for testname in cls.get_all_test_names():
            test = Test(testname)
            asl_str = str(test.parse_asl())
            with open(cls.cachedir + testname, 'w') as f:
                f.write(asl_str)
