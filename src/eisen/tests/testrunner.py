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
from alpaca.clr import AST

from eisen.parsing.callback import EisenCallback
from eisen.parsing.superparser import SuperParser
from eisen.state.basestate import BaseState as State
from eisen.validation.workflow import Workflow
from eisen.conversion.to_python import ToPython

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

class TestRunnerConfiguration:
    # The number of workers in a threadpool.
    n_workers = 16

    # The relative path to the Eisen grammar file
    grammar_file_path = "./src/eisen/grammar.gm"

    # The relative path to the directory containing Eisen test files (.en)
    test_dir = "./src/eisen/tests/"

    # The shared instance of the Alpaca config
    alpaca_config: alpaca.config.Config = None

    # The shared SuperParser instance
    parser: SuperParser = None

    deprecated = ["legacy/interface1"]
    vectors = ["vector/append", "vector/creation", "vector/append2"]

    # The list of tests which should not be run
    disabled_tests = ["legacy/objects"] + vectors + deprecated

    @classmethod
    def initialize(cls):
        cls.alpaca_config = alpaca.config.parser.run(filename=TestRunnerConfiguration.grammar_file_path)
        cls.parser = SuperParser(cls.alpaca_config)

class Test:
    def __init__(self, test_path: str) -> None:
        with open(TestRunnerConfiguration.test_dir + test_path + ".en", 'r') as f:
            self.data = f.read()

        self.code = self.data
        metadata = "\n".join([l[3:].strip() for l in self.data.splitlines() if l.startswith("///")])
        self.metadata = tomllib.loads(metadata)
        self.name = self.metadata["Test"]["name"]
        self.path = test_path
        self.info = self.metadata["Test"]["info"]
        self.expectation = TestExpectation(**self.metadata["Expects"])

    def parse_ast(self) -> AST:
        tokens = alpaca.lexer.run(text=self.code, config=TestRunnerConfiguration.alpaca_config, callback=EisenCallback)
        return TestRunnerConfiguration.parser.parse(tokens)

    @staticmethod
    def _make_exception_error_msg(e, state: State):
        exception_type = e.type
        contents = e.contains
        return f"expected to encounter exception '{exception_type}' containing:\n{contents}\nbut got:\n-----\n{state.watcher.txt}\n-----\n"

    def _get_build_file_name(self) -> str:
        return f"./build/{self.path}.py"

    def _save_python_target(self, state: State) -> None:
        ast = ToPython().run(state)
        proto_code = python.Writer().run(ast)
        code = ToPython.builtins + python.PostProcessor.run(proto_code) + ToPython.lmda + "\nmain___Fd_void_I_void_b()"
        pathlib.Path(self._get_build_file_name()).parent.mkdir(parents=True, exist_ok=True)
        with open(self._get_build_file_name(), 'w') as f:
            f.write(code)

    def _run_python_target(self) -> str:
        bytes = subprocess.check_output(["python", self._get_build_file_name()])
        return bytes.decode()

    def _check_output(self, output: str):
        if not self.expectation.output:
            return True, "success"
        expected_output = self.expectation.output
        if not self.expectation.match_case:
            expected_output = expected_output.lower()
            output = output.lower()

        if output != expected_output:
            return False, f"expected, got:\n{expected_output}\n-----\n{output}\n-----\n"
        return True, "success"

    def _evaluate_result(self, succeeded: bool, state: State) -> tuple[bool, str]:
        match self.expectation.success, succeeded:
            case True, True:
                self._save_python_target(state)
                output = self._run_python_target()
                return self._check_output(output)
            case True, False:
                print(state.watcher.txt)
                return False, "test failed unexpectedly"
            case False, True:
                return False, "test expected to fail, but succeeded"
            case False, False:
                return self._check_exceptions(state)

    def _check_exceptions(self, state: State) -> tuple[bool, str]:
        num_expected_exceptions = len(self.expectation.compiler_exceptions)
        got_number_of_exceptions = state.watcher.txt.count(AbstractException.delineator)
        if num_expected_exceptions != got_number_of_exceptions:
            return False, f"expected ({num_expected_exceptions}) exceptions but got ({got_number_of_exceptions}) in: \n{state.watcher.txt}"

        txt = state.watcher.txt
        for e in self.expectation.compiler_exceptions:
            if e.type not in txt or e.contains not in txt:
                return False, Test._make_exception_error_msg(e, state)

            # remove the strings from the output to avoid double lookup
            txt = txt.replace(e.type, "", 1)
            txt = txt.replace(e.contains, "", 1)
        return True, "success"

    def run(self) -> tuple[bool, str]:
        original_hook = sys.excepthook
        def exceptions_hook(e_type, e_value: Exception, tb):
            if e_type == VisitorException:
                original_hook(e_type, e_value.with_traceback(None), None)
            else:
                original_hook(e_type, e_value, tb)

        sys.excepthook = exceptions_hook

        ast = self.parse_ast()
        state = State.create_initial(TestRunnerConfiguration.alpaca_config, ast, txt=self.code, print_to_watcher=True)
        return self._evaluate_result(*Workflow.execute(state))

class TestRunner():
    @staticmethod
    def run_test_by_name(name: str):
        return Test(name).run()

    @staticmethod
    def get_all_test_names() -> list[str]:
        filenames: list[str] = []
        for root, _, files in walk(TestRunnerConfiguration.test_dir):
            for file in files:
                filenames.append(root + os.sep + file)

        # TODO: fix this to remove the prefix ./src/eisen/tests which has len 18
        test_files = [f[18:] for f in filenames if f.endswith(".en")]
        all_tests = [t.split(".")[0] for t in test_files]
        all_tests = [t[1:] if t[0] == "/" else t for t in all_tests]

        individually_disabled_tests = [t for t in TestRunnerConfiguration.disabled_tests if t[-1] != "/"]
        tests_to_run = [t for t in all_tests if t not in individually_disabled_tests]

        prefix_disabled_tests = [t for t in TestRunnerConfiguration.disabled_tests if t[-1] == "/"]
        tests_to_run = [t for t in tests_to_run
                        if not any(t.startswith(prefix) for prefix in prefix_disabled_tests)]
        return tests_to_run

    @staticmethod
    def run_all_tests_threadpooled():
        start = time.perf_counter()
        tests = TestRunner.get_all_test_names()
        with multiprocessing.Pool(TestRunnerConfiguration.n_workers) as p:
            data: list[str] = p.map(TestRunner.run_test_in_thread, tests)

        successes = data.count("success!")
        msg = "\n".join([m for m in data if m != "success!"])
        print(msg)
        end = time.perf_counter()
        total_tests= len(tests)
        print(f"finished in {round(end-start, 4)}s\n{successes}/{total_tests} ({round(100.0*successes/total_tests, 2)}%) succeeded")

    @staticmethod
    def run_test_in_thread(test_name: str) -> str:
        try:
            status, msg = TestRunner.run_test_by_name(test_name)
            msg_to_sender = "success!"
            if not status:
                msg_to_sender = f"test failed: {test_name}\n" + "\n".join(["   " + l for l in msg.split("\n")])

            return msg_to_sender
        except Exception as e:
            return f"test failed: {test_name}\n: {e}"

    @staticmethod
    def run_tests_sequentially():
        successes = 0
        tests = TestRunner.get_all_test_names()

        start = time.perf_counter()
        for test_name in tests:
            print(test_name, end=" ")
            test_start = time.perf_counter()
            status, msg = TestRunner.run_test_by_name(test_name)
            test_end = time.perf_counter()
            print(f"{round(test_end-test_start, 4)}")

            if status:
                successes += 1
            else:
                print(f"test failed: {test_name}")
                print("\n".join(["   " + l for l in msg.split("\n")]))

        end = time.perf_counter()
        total_tests= len(tests)
        print(f"finished in {round(end-start, 4)}s\n{successes}/{total_tests} ({round(100.0*successes/total_tests, 2)}%) succeeded")

    @staticmethod
    def run_all_tests(verbose: bool):
        TestRunnerConfiguration.initialize()
        if not verbose:
            TestRunner.run_all_tests_threadpooled()
            return
        else:
            TestRunner.run_tests_sequentially()
