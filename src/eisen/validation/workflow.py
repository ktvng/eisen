from __future__ import annotations

import time
from dataclasses import dataclass

from alpaca.utils import Visitor
from eisen.common.exceptionshandler import ExceptionsHandler
from eisen.validation.modulevisitor import ModuleVisitor
from eisen.validation.typechecker import TypeChecker
from eisen.validation.functionvisitor import FunctionVisitor
from eisen.validation.usagechecker import UsageChecker
from eisen.validation.declarationvisitor import DeclarationVisitor
from eisen.validation.finalizationvisitor import FinalizationVisitor, Finalization2
from eisen.validation.fnconverter import FnConverter
from eisen.validation.initalizer import Initializer
from eisen.validation.nilcheck import NilCheck
from eisen.validation.instancevisitor import InstanceVisitor
from eisen.memory.memcheck import MemCheck
from eisen.state.basestate import BaseState as State

# Notes:
# A module is a collection of structs/functions
# A context, properly, is a block with instances defined
# A context may have a parent as a module (as module level functions are available
# for use as instances)
# They are implemented the same.

# class used to debug
class PrintAsl():
    def run(self, state: State):
        print(state.asl)
        return state

class Workflow():
    steps: list[Visitor] = [
        # initialize the .data attribute for all asls with empty NodeData instances
        Initializer,

        # create the module structure of the program.
        #   - the module of a node can be accessed by params.asl_get_mod()
        ModuleVisitor,

        # add proto types for struct/interfaces, which are the representation
        # of struct declaration without definition.
        DeclarationVisitor,

        # finalizes the proto types (which moves from declaration to definition)
        # TODO: for now, interfaces can only be implemented from the same module
        # in which they are defined.
        #
        # we must finalize interfaces first because structs depend on interfaces
        # as they implement interfaces
        FinalizationVisitor,
        Finalization2,

        # adds types for and constructs the functions. this also normalizes the
        # (def ...) and (create ...) asls so they have the same child structure,
        # which allows us to process them identically later in the
        # TypeClassFlowWrangler.
        FunctionVisitor,

        # this changes (ref ...) to (fn ...) if they refer to global functions
        FnConverter,

        # evaluate the flow of types through the program.
        #   - the type which is flowed through a node can be accessed by
        #     params.get_returned_type()
        TypeChecker,

        InstanceVisitor,

        # this handles restrictions based on let/var/val differences
        UsageChecker,

        NilCheck,
        MemCheck,

        # note: def, create, fn, ref, ilet, :: need instances!!
    ]

    @staticmethod
    def _choose_steps(supplied_steps: list[Visitor]=None):
        if supplied_steps:
            return supplied_steps
        return Workflow.steps

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
