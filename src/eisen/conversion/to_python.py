from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import AST, ASTToken
from alpaca.pattern import Pattern
import alpaca
from eisen.common.traits import TraitsLogic
from eisen.state.topythonstate import ToPythonState as State
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
import eisen.adapters as adapters



def new_token(value: str):
    return ASTToken(["TAG"], value=value)

def no_content() -> AST:
    return AST("no_content", lst=[])

class ToPython(Visitor):
    builtins = """
def append(a, b):
    if isinstance(b, lmda):
        b = b()
    a.append(b)

"""

    lmda = """
class lmda:
    def __init__(self, f):
        self.f = f
        self.params=list()

    def __call__(self, *args):
        return self.f(*self.params, *args)

    def curry(self, args):
        fn = lmda(self.f)
        fn.params = self.params + args
        return fn
"""

    def __init__(self, debug: bool = False):
        super().__init__(debug)
        self.python_gm = alpaca.config.parser.run("./src/python/python.gm")

    def run(self, state: State_PostInstanceVisitor) -> AST:
        return self.apply(State.create_from_basestate(state))

    def apply(self, state: State) -> AST:
        return self._route(state.get_ast(), state)

    def create_ast(self, txt: str):
        return alpaca.clr.CLRParser.run(self.python_gm, txt)

    @Visitor.for_ast_types("annotation")
    def annotation_(fn, _: State):
        return no_content()

    @Visitor.for_ast_types("start")
    def start_(fn, state: State):
        lst = []
        for child in state.get_all_children():
            match child.type:
                case "mod": lst.extend(fn.apply(state.but_with(ast=child)))
                case "trait": pass
                case _: lst.append(fn.apply(state.but_with(ast=child)))

        return AST("start", lst=lst)

    @Visitor.for_ast_types("mod")
    def mod_(fn, state: State) -> list[AST]:
        """
        This is the only node which returns a list of ASTs, and must be handled differently
        """
        node = adapters.Mod(state)
        parts = []
        for child in state.get_child_asts():
            match child.type:
                case "mod":
                    parts.extend(fn.apply(state.but_with(
                        ast=child,
                        mod=node.get_entered_module())))
                case _:
                    parts.append(fn.apply(state.but_with(
                        ast=child,
                        mod=node.get_entered_module())))
        return parts

    @Visitor.for_ast_types("trait_def")
    def trait_def(fn, state: State):
        node = adapters.TraitDef(state)
        trait_class_name = TraitsLogic.get_python_writable_name_for_trait_class(
            struct_name=node.get_struct_name(),
            trait_name=node.get_trait_name())

        # First build a new class representing the trait's implementation
        class_pattern = """
        ('class TRAIT_IMPLEMENTATION_CLASS_NAME
            ('init
                ('args 'self 'obj)
                ('seq ('= ('. ('ref 'self) '_me) 'obj))))"""

        x = Pattern(class_pattern).build({
            "TRAIT_IMPLEMENTATION_CLASS_NAME": new_token(trait_class_name)
        })

        # Apply this visitor on the child (def ...) ASTs
        fns = [fn.apply(state.but_with(ast=child))
               for child in node.get_asts_of_implemented_functions()]

        # Map the obtained (def ...) ASTs so that the [FIRST] argument (which is the object which
        # implements the trait), is assigned to 'self._me' inside the trait object. When a cast
        # occurs, the object will be wrapped with a new class of type [TRAIT_IMPLEMENTATION_CLASS_NAME]
        # which will store a reference to the original object as 'self._me'
        def_pattern = Pattern("('def NAME ('args FIRST XS_ARGS...) ('seq XS_SEQ...))")
        new_fns = [
            def_pattern.match(fn).to("""
                ('def NAME ('args '__self XS_ARGS...)
                    ('seq
                        ('= ('ref FIRST) ('. ('ref '__self) '_me))
                        XS_SEQ...
                        ))""")
            for fn in fns
        ]

        x._list.extend(new_fns)
        return x

    @Visitor.for_ast_types("struct")
    def struct_(fn, state: State):
        class_pattern = """
        ('class NAME
            ('init
                ('args SELF_NAME ARGS...)
                ('seq DECLS... SEQ...)))
        """

        node = adapters.Struct(state)
        create_node = adapters.CommonFunction(state.but_with(ast=node.get_create_ast()))

        name = Pattern("('struct name xs...)").match(state.get_ast()).name
        self_name = Pattern("('create _ _ ('rets (': ('new name) _)) _)") \
            .match(create_node.state.get_ast()).name

        args = [fn.apply(state.but_with(ast=arg)) for arg in create_node.get_args_ast()\
            .get_all_children()]

        seq = fn.apply(state.but_with(create_node.get_seq_ast()))._list

        # These are the self.attr = None lines that must be added.
        decls = Pattern("(': (?? attr_name) _)").map(state.get_ast(),
            into_pattern=f"('= ('. ('ref '{self_name.value}) attr_name) 'None)")

        return Pattern(class_pattern).build(
            {
                "NAME": name,
                "SELF_NAME": self_name,
                "ARGS": args,
                "SEQ": seq,
                "DECLS": decls
            }
        )

    @staticmethod
    def get_ret_names(ret_ast: AST) -> list[ASTToken]:
        if ret_ast.has_no_children():
            return []
        if ret_ast.first().type == "prod_type":
            return [m.name for m in map(Pattern("(': (?? name) _)").match, ret_ast.first().get_all_children()) if m]
        return [Pattern("('rets (': (?? name) _))").match(ret_ast).name]

    @Visitor.for_ast_types("def")
    def def_(fn, state: State):
        node = adapters.Def(state)
        def_pattern = """
        ('def NAME
            ARGS
            ('seq RET_VARS... SEQ_PARTS... RETURN ))
        """
        ret_names = ToPython.get_ret_names(node.get_rets_ast())
        return_vars = [Pattern("'= NAME 'None").build({"NAME": name}) for name in ret_names]
        arg_ast = fn.apply(state.but_with(ast=node.get_args_ast()))
        seq_parts = fn.apply(state.but_with(
            ast=node.get_seq_ast(),
            ret_names=ret_names)).get_all_children()

        return Pattern(def_pattern).build({
            "NAME": new_token(node.get_function_instance().get_full_name()),
            "ARGS": arg_ast,
            "SEQ_PARTS": seq_parts,
            "RET_VARS": return_vars,
            "RETURN": AST(type="return", lst=([] if not ret_names else [AST("tags", lst=ret_names)]))
        })

    @Visitor.for_ast_types("return")
    def return_(fn, state: State):
        ret_names = state.get_ret_names() or []
        if state.get_ast().has_no_children():
            if ret_names:
                return Pattern("('return ('tags NAMES...))").build({"NAMES": ret_names})
            return Pattern("('return )").build()
        match ast := Pattern("('return x)").match(state.get_ast()).x:
            case ASTToken():
                ret_values = [ast]
            case AST():
                ret_values = ast.get_all_children()
        ret_assigns = [Pattern("'= NAME VALUE").build({"NAME": name, "VALUE": value})
            for name, value in zip(ret_names, ret_values)]
        return Pattern("('subseq ASSIGNS... ('return ('tags NAMES...)))").build({
            "NAMES": ret_names,
            "ASSIGNS": ret_assigns
        })

    @Visitor.for_ast_types("args")
    def args_(fn, state: State):
        if state.get_ast().has_no_children():
            return Pattern("('args )").build()
        match ast := fn.apply(state.but_with_first_child()):
            case ASTToken():
                return Pattern("('args NAME)").build({"NAME": ast})
            case AST():
                ast.update(type="args")
                return ast

    @Visitor.for_ast_types(":")
    def colon_(fn, state: State):
        return Pattern("(': (?? name) _)").match(state.get_ast()).name

    @staticmethod
    def _apply_fn_to_all_children_and_build_ast(ast_type: str, fn: Visitor, state: State) -> AST:
        return AST(ast_type, lst=[fn.apply(state.but_with(ast=child))
            for child in state.get_all_children()])

    @Visitor.for_ast_types("prod_type")
    def prod_type_(fn, state: State):
        return ToPython._apply_fn_to_all_children_and_build_ast("tags", fn, state)

    @Visitor.for_ast_types("seq")
    def seq_(fn, state: State):
        return ToPython._apply_fn_to_all_children_and_build_ast("seq", fn, state)

    @Visitor.for_ast_types(*adapters.InferenceAssign.ast_types)
    def iletivar_(fn, state: State):
        return ToPython._apply_fn_to_all_children_and_build_ast("=", fn, state)


    @Visitor.for_ast_types(*adapters.Decl.ast_types)
    def decls_(fn, state: State):
        # This is the case for multiple assignment
        if Pattern("(?? ('bindings xs...) _)").match(state.get_ast()):
            values = "'None " * len(state.first_child().get_all_children())
            return Pattern("('= BINDINGS VALUES)").build({
                "BINDINGS": fn.apply(state.but_with_first_child()),
                "VALUES": Pattern(f"('tuple {values})").build()
            })

        # This is the case for single assignment
        else:
            return Pattern("(?? (?? name) _)").match(state.get_ast()).to("('= ('ref name) 'None)")

    @Visitor.for_ast_types("ref")
    def ref_(fn, state: State):
        return AST("ref", lst=[state.first_child()])

    @Visitor.for_ast_types("fn")
    def fn_(fn, state: State):
        instance = state.get_instances()[0]
        ast = Pattern(f"('fn '{instance.get_full_name()})").build()

        if instance.no_lambda:
            return Pattern("('fn name)").match(ast).to("('ref name)")
        return Pattern("('fn name)").match(ast).to("('call ('ref 'lmda) ('params name))")

    @Visitor.for_ast_types("call")
    def call_(fn, state: State):
        node = adapters.Call(state)
        if node.is_print():
            other_params = state.second_child()[1:]
            value: str = state.second_child().first().value
            index = {
                "BASE": ASTToken(type_chain=["str"], value=value.replace("%i", "{}")),
                "PARAMS": [fn.apply(state.but_with(ast=child)) for child in other_params],
                "EMPTY_STR": ASTToken(["str"], value="")
            }
            return Pattern(
                """('call
                    ('ref 'print)
                    ('params
                        ('call
                            ('. BASE ('ref 'format))
                            ('params PARAMS...))
                        ('named 'end EMPTY_STR)))""").build(index)

        if node.is_trait_function_call():
            # Remove the first parameters which is the original object
            state.second_child()._list = state.second_child()._list[1:]

        return AST("call", lst=[fn.apply(state.but_with(ast=child))
            for child in state.get_all_children()])

    @Visitor.for_ast_types("bindings")
    def bindings_(fn, state: State):
        return AST("tags", lst=[fn.apply(state.but_with(ast=child))
            for child in state.get_all_children()])

    @Visitor.for_ast_types("if", "cond", "lvals",
        "params", "tags", "tuple",
        "=", ".", "+", "-",
        "*", "==", "+=", "-=", "*=", "!=",
        "<", ">", "<=", ">=",
        "and", "or",
        "while")
    def binop_(fn, state: State):
        return AST(state.get_ast().type, lst=[fn.apply(state.but_with(ast=child))
            for child in state.get_all_children()])

    @Visitor.for_ast_types("::")
    def mod_scope_(fn, state: State):
        node = adapters.ModuleScope(state)
        return ASTToken(type_chain=["code"], value=node.get_instance().get_full_name())

    @Visitor.for_ast_types("<-")
    def ptr_(fn, state: State):
        return AST("=", lst=[fn.apply(state.but_with(ast=child))
            for child in state.get_all_children()])

    @Visitor.for_ast_types("!")
    def not_(fn, state: State):
        return AST("not", lst=[fn.apply(state.but_with_first_child())])

    @Visitor.for_ast_types("/=")
    def div_eq_(fn, state: State):
        return AST("//=", lst=[fn.apply(state.but_with(ast=child))
            for child in state.get_all_children()])

    @Visitor.for_ast_types("/")
    def div_(fn, state: State):
        return AST("//", lst=[fn.apply(state.but_with(ast=child))
            for child in state.get_all_children()])

    @Visitor.for_ast_types("cast")
    def cast_(fn, state: State):
        node = adapters.Cast(state)
        if not node.get_cast_into_type().is_trait(): raise Exception("cast should only be for trait?")

        name = TraitsLogic.get_python_writable_name_for_trait_class(
            struct_name=node.get_original_type().name,
            trait_name=node.get_cast_into_type().name)

        return Pattern(f"('call ('ref '{name}) ('params OBJ))").build({
            "OBJ": fn.apply(state.but_with_first_child())
        })

    @Visitor.for_ast_types("curry_call")
    def curry_call_(fn, state: State):
        state.get_ast()[0] = fn.apply(state.but_with_first_child())
        return Pattern("('curry_call FN ('curried XS...)").match(state.get_ast())\
            .to("('call ('. FN 'curry) ('params ('list XS...)))")

    @Visitor.for_ast_types("new_vec")
    def new_vec_(fn, state: State):
        return Pattern("('list )").build()
        return AST(type="list", lst=[])

    @Visitor.for_ast_types("index")
    def index_(fn, state: State):
        return state.get_ast()

    @Visitor.for_ast_types(*adapters.BindingAST.ast_types)
    def _binding(fn, state: State):
        return state.first_child()

    @Visitor.for_tokens
    def tokens_(fn, state: State):
        match state.get_ast().value:
            case "true": return ASTToken(type_chain=["code"], value="True")
            case "false": return ASTToken(type_chain=["code"], value="False")
            case "nil": return ASTToken(type_chain=["code"], value="None")
            case _: return state.get_ast()
