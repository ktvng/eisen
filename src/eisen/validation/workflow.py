from __future__ import annotations

import time

from eisen.common.exceptionshandler import ExceptionsHandler
from eisen.validation.modulevisitor import ModuleVisitor
from eisen.validation.typechecker import TypeChecker
from eisen.validation.functionvisitor import FunctionVisitor
from eisen.validation.usagechecker import UsageChecker
from eisen.validation.declarationvisitor import DeclarationVisitor
from eisen.validation.finalizationvisitor import FinalizationVisitor
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

class PrintAsl():
    def run(self, state: State):
        print(state.asl)
        return state

class Workflow():
    steps = [
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

    @classmethod
    def execute(cls, state: State, steps=None):
        if steps is None:
            steps = cls.steps

        for step in steps:
            state = step().run(state)

            ExceptionsHandler().apply(state)
            if cls.should_stop_execution(state):
                return False, state

        return True, state

    @classmethod
    def execute_with_benchmarks(cls, state: State, steps=None):
        if steps is None:
            steps = cls.steps
        perf = []
        def step_decorator(step):
            class decorated_step():
                def run(self, state: State):
                    start = time.perf_counter_ns()
                    state = step().run(state)
                    end = time.perf_counter_ns()
                    perf.append((step.__name__, (end-start)/1000000))
                    return state

            return decorated_step

        decorated_workflow = [step_decorator(step) for step in steps]
        result, state = cls.execute(state, steps=decorated_workflow)
        if not result:
            print("Failed to run...")
        cls.pretty_print_perf(perf)
        return state

    @classmethod
    def pretty_print_perf(cls, perf: list[tuple[str, int]]):
        longest_name_size = max(len(x[0]) for x in perf)
        block_size = longest_name_size + 4
        for name, val in perf:
            print(" "*(block_size - len(name)), name, " ", val)

        print(" "*(block_size-len("Total")), "Total", " ", sum(x[1] for x in perf))

    @classmethod
    def should_stop_execution(cls, state: State):
        return state.exceptions
