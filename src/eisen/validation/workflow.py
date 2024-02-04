from __future__ import annotations

import time
from dataclasses import dataclass

from alpaca.utils import Visitor
from eisen.common.exceptionshandler import ExceptionsHandler
from eisen.validation.modulevisitor import ModuleVisitor
from eisen.validation.typechecker import TypeChecker
from eisen.validation.functionvisitor import FunctionVisitor
from eisen.validation.declarationvisitor import DeclarationVisitor
from eisen.validation.finalizationvisitor import InterfaceFinalizationVisitor, StructFinalizationVisitor
from eisen.validation.fnconverter import FnConverter
from eisen.validation.initalizer import Initializer
from eisen.validation.nilcheck import NilCheck
from eisen.validation.instancevisitor import InstanceVisitor
from eisen.validation.recursionvisitor import RecursionVisitor
from eisen.validation.vectorvisitor import VectorVisitor
from eisen.trace.memoryvisitor import MemoryVisitor
from eisen.bindings.bindingparser import BindingParser
from eisen.bindings.bindingchecker import BindingChecker
from eisen.state.basestate import BaseState as State

# Notes:
# A module is a collection of structs/functions
# A context, properly, is a block with instances defined
# A context may have a parent as a module (as module level functions are available
# for use as instances)
# They are implemented the same.

# class used to debug
class PrintAst():
    def run(self, state: State):
        print(state.get_ast())
        return state

class Workflow():
    steps: list[Visitor] = [
        # Initialize the .data attribute for all asts with empty NodeData instances
        Initializer,

        # Create the module structure of the program.
        ModuleVisitor,

        # Parse and add declarations of structs/interfaces
        DeclarationVisitor,

        # TODO: for now, interfaces can only be implemented from the same module
        # in which they are defined.
        #
        # Finalizes the interfaces after parsing their definitions. This must occur
        # before we finalize structs as structs depend on interfaces
        InterfaceFinalizationVisitor,
        # Finalizes the structs after parsing their definitions.
        StructFinalizationVisitor,

        # Constructs and adds types for global functions. Here (def ...) and
        # (create ...) ASTS are also normalized to have the same structure,
        # meaning they can be parsed with shared code.
        FunctionVisitor,

        # Add builtin methods required to deal with vectors (e.g. append, etc)
        VectorVisitor,

        # Convert (ref ...) to (fn ...) ASTS if they refer to global functions,
        # allowing future visitors to distinguish between pure functions with 'fn'
        # and references to functions/curried function with 'ref'
        FnConverter,

        # Evaluate the flow of types through the program. Afterwards, the type
        # which flows through a node/AST can be accessed by state.get_returned_type()
        TypeChecker,

        # Create instances where applicable. Instances are pieces of information
        # packaged together (name, type, etc.) which is useful for transpilation
        InstanceVisitor,

        # Check the recursion structure of methods and structs with method pointers,
        # (incomplete). This is used to identify where special processing is
        # necessary later on, as some visitors must handle recursive methods uniquely.
        RecursionVisitor,

        # Parse the bindings associated with structs/functions as each of these have
        # attributes or parameters with bindings.
        BindingParser,

        # Check that reference bindings (var, mut, etc) are respected and consistent
        BindingChecker,

        # Verify that nil and nilable types are handled and inspected before use.
        # Disabled pending refactor.
        # NilCheck,

        # Verify that the code is memory safe.
        MemoryVisitor,

        # Print the current AST
        # PrintAst,

        # note: def, create, fn, ref, ilet, ::, . need instances!!
    ]

    @staticmethod
    def _choose_steps(supplied_steps: list[Visitor]=None):
        return supplied_steps if supplied_steps else Workflow.steps

    @staticmethod
    def _run_step_with_state(step: Visitor, state: State) -> State:
        return step().run(state)

    @staticmethod
    def execute(state: State, steps: list[Visitor]=None) -> tuple[bool, State]:
        for step in Workflow._choose_steps(steps):
            state = Workflow._run_step_with_state(step, state)
            ExceptionsHandler().apply(state)
            if Workflow.should_stop_execution(state):
                return False, state
        return True, state

    @staticmethod
    def _instrument_step_with_telemetry(step_times: list[int], step: Visitor) -> Visitor:
        class decorated_step():
            def run(self, state: State):
                start = time.perf_counter_ns()
                state = Workflow._run_step_with_state(step, state)
                end = time.perf_counter_ns()
                decorated_step.add_metric(start, end)
                return state

            @staticmethod
            def add_metric(start: int, end: int):
                step_times.append(PerformanceMetric(
                    step_name=step.__name__,
                    step_time=round((end-start)/1000000, 5)))

        return decorated_step

    @staticmethod
    def execute_with_benchmarks(state: State, steps: list[Visitor]=None) -> tuple[bool, State]:
        metrics: list[PerformanceMetric] = []
        steps_with_telemetry = [Workflow._instrument_step_with_telemetry(metrics, step)
            for step in Workflow._choose_steps(steps)]

        result, state = Workflow.execute(state, steps=steps_with_telemetry)
        PerformanceMetric.print_performance_metrics(metrics)
        return result, state

    @staticmethod
    def should_stop_execution(state: State) -> bool:
        return len(state.exceptions) > 0


@dataclass
class PerformanceMetric():
    step_name: str
    step_time: int

    @staticmethod
    def _print_performance_metric_line(metric: PerformanceMetric, block_size: int):
        print(" "*(block_size - len(metric.step_name)),
            metric.step_name, " ",
            metric.step_time)

    @staticmethod
    def print_performance_metrics(metrics: list[PerformanceMetric]):
        longest_name_size = max(len(metric.step_name) for metric in metrics)
        block_size = longest_name_size + 4
        for metric in metrics:
            PerformanceMetric._print_performance_metric_line(metric, block_size)

        print(" "*(block_size-len("Total")),
              "Total", " ",
              round(sum(metric.step_time for metric in metrics), 5))
