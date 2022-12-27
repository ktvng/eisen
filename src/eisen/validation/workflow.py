import time

from eisen.common.state import State
from eisen.common.exceptionshandler import ExceptionsHandler
from eisen.validation.modulevisitor import ModuleVisitor
from eisen.validation.flowvisitor import FlowVisitor
from eisen.validation.functionvisitor import FunctionVisitor
from eisen.validation.permissionsvisitor import PermissionsVisitor
from eisen.validation.declarationvisitor import DeclarationVisitor
from eisen.validation.finalizationvisitor import InterfaceFinalizationVisitor, StructFinalizationVisitor
from eisen.validation.initalizer import Initializer
from eisen.validation.nilcheck import NilCheck

# Notes:
# A module is a collection of structs/functions
# A context, properly, is a block with instances defined
# A context may have a parent as a module (as module level functions are available
# for use as instances)
# They are implemented the same.

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
        InterfaceFinalizationVisitor,
        StructFinalizationVisitor,

        # adds types for and constructs the functions. this also normalizes the
        # (def ...) and (create ...) asls so they have the same child structure,
        # which allows us to process them identically later in the 
        # TypeClassFlowWrangler.
        FunctionVisitor,
        
        # evaluate the flow of types through the program. 
        #   - the type which is flowed through a node can be accessed by
        #     params.get_returned_type()
        FlowVisitor,

        # this handles restrictions based on let/var/val differences
        PermissionsVisitor,

        # NilCheck,

        # note: def, create, fn, ref, ilet need instances!!
    ]

    @classmethod
    def execute(cls, state: State, steps=None):
        if steps is None:
            steps = cls.steps

        for step in steps:
            step().apply(state)

            ExceptionsHandler().apply(state)
            if cls.should_stop_execution(state):
                return False

        return True

    @classmethod
    def execute_with_benchmarks(cls, state: State, steps=None):
        if steps is None:
            steps = cls.steps
        perf = []
        def step_decorator(step):
            class decorated_step():
                def apply(self, state: State):
                    start = time.perf_counter_ns()
                    step().apply(state)
                    end = time.perf_counter_ns()
                    perf.append((step.__name__, (end-start)/1000000))
            return decorated_step
        
        decorated_workflow = [step_decorator(step) for step in steps]
        result = cls.execute(state, steps=decorated_workflow)
        if not result:
            print("Failed to run...")
        cls.pretty_print_perf(perf)

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

