from __future__ import annotations

import os
from os import walk
import time
import sys
import pathlib
import multiprocessing
import subprocess
import tomllib
from dataclasses import dataclass
from typing import Any

import alpaca
import python
from alpaca.concepts import AbstractException
from alpaca.utils import VisitorException

from eisen.parsing.callback import EisenCallback
from eisen.parsing.superparser import SuperParser
from eisen.state.basestate import BaseState as State
from eisen.validation.workflow import Workflow
from eisen.conversion.to_python import ToPython

class StaticParser():
    grammarfile = "./src/eisen/grammar.gm"
    config = alpaca.config.parser.run(filename=grammarfile)
    parser = SuperParser(config)

@dataclass
class CompilerException:
    type: str
    contains: str

@dataclass
class TestExpectation:
    success: bool
    output: str = None
    match_case: bool = True
    Exceptions: Any = None
    compiler_exceptions: list[CompilerException] = None

    def __post_init__(self):
        if self.Exceptions:
            self.compiler_exceptions = [CompilerException(**ex) for ex in self.Exceptions]

class Test:
    test_dir = "./src/eisen/tests/"
    grammarfile = "./src/eisen/grammar.gm"
    shared_config = alpaca.config.parser.run(filename=grammarfile)

    def __init__(self, test_path: str) -> None:
        with open(Test.test_dir + test_path + ".en", 'r') as f:
            self.data = f.read()

        self.code = self.data
        metadata = "\n".join([l[3:].strip() for l in self.data.splitlines() if l.startswith("///")])
        self.metadata = tomllib.loads(metadata)
        self.name = self.metadata["Test"]["name"]
        self.info = self.metadata["Test"]["info"]
        self.expects = TestExpectation(**self.metadata["Expects"])

    def parse_asl(self):
        config = alpaca.config.parser.run(filename=Test.grammarfile)
        tokens = alpaca.lexer.run(text=self.code, config=Test.shared_config, callback=EisenCallback)
        asl = SuperParser(config).parse(tokens)
        return asl

    @staticmethod
    def _make_exception_error_msg(e, state: State):
        exception_type = e.type
        contents = e.contains
        return f"expected to encounter exception '{exception_type}' containing:\n{contents}\nbut got:\n-----\n{state.watcher.txt}\n-----\n"

    def _handle_unexpected_failure(self, state: State):
        print(state.watcher.txt)
        print(state.asl)
        return False, "test failed due to exception"

    def _get_build_file_name(self) -> str:
        return f"./build/{self.name}.py"

    def _save_python_target(self, state: State) -> None:
        asl = ToPython().run(state)
        proto_code = python.Writer().run(asl)
        code = ToPython.builtins + python.PostProcessor.run(proto_code) + ToPython.lmda + "\n_main___Fd_void_I_void_b()"
        pathlib.Path(self._get_build_file_name()).parent.mkdir(parents=True, exist_ok=True)
        with open(self._get_build_file_name(), 'w') as f:
            f.write(code)

    def _run_python_target(self) -> str:
        bytes = subprocess.check_output(["python", self._get_build_file_name()])
        return bytes.decode()

    def _check_output(self, output: str):
        if not self.expects.output:
            return True, "success"
        expected_output = self.expects.output
        if not self.expects.match_case:
            expected_output = expected_output.lower()
            output = output.lower()

        if output != expected_output:
            return False, f"expected, got:\n{expected_output}\n-----\n{output}\n-----\n"
        return True, "success"

    def _handle_expected_success(self, state: State):
        print(state.watcher.txt)
        return False, "failed"


    def _evaluate_result(self, succeeded: bool, state: State):
        if self.expects.success:
            if not succeeded:
                return self._handle_expected_success(state)

            self._save_python_target(state)
            output = self._run_python_target()
            return self._check_output(output)
        else:
            return self._check_exceptions(state)

    def _check_exceptions(self, state: State):
        num_expected_exceptions = len(self.expects.compiler_exceptions)
        got_number_of_exceptions = state.watcher.txt.count(AbstractException.delineator)
        if num_expected_exceptions != got_number_of_exceptions:
            return False, f"expected ({num_expected_exceptions}) exceptions but got ({got_number_of_exceptions}) in: \n{state.watcher.txt}"

        txt = state.watcher.txt
        for e in self.expects.compiler_exceptions:
            if e.type not in txt or e.contains not in txt:
                return False, Test._make_exception_error_msg(e, state)

            # remove the strings from the output to avoid double lookup
            txt = txt.replace(e.type, "", 1)
            txt = txt.replace(e.contains, "", 1)
        return True, "success"

    def run(self) -> tuple[bool, str]:
        orignal_hook = sys.excepthook
        def exceptions_hook(e_type, e_value: Exception, tb):
            if e_type == VisitorException:
                orignal_hook(e_type, e_value.with_traceback(None), None)
            else:
                orignal_hook(e_type, e_value, tb)

        sys.excepthook = exceptions_hook

        asl = self.parse_asl()
        state = State.create_initial(Test.shared_config, asl, txt=self.code, print_to_watcher=True)
        return self._evaluate_result(*Workflow.execute(state))

class TestRunner():
    disabled_tests = ["objects", "recursion", "e_funcarg", "unwrap", "funcarg", "vector/append2", "vector/append", "function_args"]
    @staticmethod
    def run_test_by_name(name: str):
        return Test(name).run()

    @staticmethod
    def get_all_test_names() -> list[str]:
        filenames = []
        for root, _, files in walk(Test.test_dir):
            for file in files:
                filenames.append(root + os.sep + file)
        # TODO: fix this to remove the prefix ./src/eisen/tests
        test_files = [f[18:] for f in filenames if f.endswith(".en")]
        all_tests = [t.split(".")[0] for t in test_files]
        all_tests = [t[1:] if t[0] == "/" else t for t in all_tests]
        tests_to_run = [t for t in all_tests if t not in TestRunner.disabled_tests]
        return tests_to_run

    @staticmethod
    def run_all_tests_threadpooled():
        start = time.perf_counter()
        tests = TestRunner.get_all_test_names()
        with multiprocessing.Pool(8) as p:
            data: list[str] = p.map(TestRunner.run_test_in_thread, tests)

        successes = data.count("success!")
        msg = "\n".join([m for m in data if m != "success!"])
        print(msg)
        end = time.perf_counter()
        total_tests= len(tests)
        print(f"finished in {round(end-start, 4)}s\n{successes}/{total_tests} ({round(100.0*successes/total_tests, 2)}%) succeeded")

    @staticmethod
    def run_test_in_thread(testname: str) -> str:
        try:
            status, msg = TestRunner.run_test_by_name(testname)
            msg_to_sender = "success!"
            if not status:
                msg_to_sender = f"test failed: {testname}\n" + "\n".join(["   " + l for l in msg.split("\n")])

            return msg_to_sender
        except Exception as e:
            return f"test failed: {testname}\n: {e}"


    @staticmethod
    def run_tests_sequentially():
        successes = 0
        tests = TestRunner.get_all_test_names()

        start = time.perf_counter()
        for testname in tests:
            print(testname)
            status, msg = TestRunner.run_test_by_name(testname)

            if status:
                successes += 1
            else:
                print(f"test failed: {testname}")
                print("\n".join(["   " + l for l in msg.split("\n")]))

        end = time.perf_counter()
        total_tests= len(tests)
        print(f"finished in {round(end-start, 4)}s\n{successes}/{total_tests} ({round(100.0*successes/total_tests, 2)}%) succeeded")

    @staticmethod
    def run_all_tests(verbose: bool):
        if not verbose:
            TestRunner.run_all_tests_threadpooled()
            return
        else:
            TestRunner.run_tests_sequentially()
