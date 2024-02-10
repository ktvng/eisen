from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import AST, ASTToken
from alpaca.pattern import Pattern
import alpaca
from eisen.state.topythonstate import ToPythonState as State
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
import eisen.adapters as adapters


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
        # print(state.get_ast())
        # input()
        result = self.apply(State.create_from_basestate(state))
        return result

    def apply(self, state: State) -> AST:
        return self._route(state.get_ast(), state)

    def create_ast(self, txt: str):
        return alpaca.clr.CLRParser.run(self.python_gm, txt)

    @Visitor.for_ast_types("annotation")
    def annotation_(fn, state: State):
        return AST("no_content", lst=[])

    @Visitor.for_default
    def default_(fn, state: State):
        print(f"ToPython unimplemented for {state.get_ast()}")
        return ASTToken(type_chain=["code"], value="***TODO***")

    @Visitor.for_ast_types("start")
    def start_(fn, state: State):
        lst = []
        for child in state.get_all_children():
            if child.type == "mod":
                lst.extend(fn.apply(state.but_with(ast=child)))
            elif child.type != "interface":
                lst.append(fn.apply(state.but_with(ast=child)))

        return AST("start", lst=lst)

    @Visitor.for_ast_types("mod")
    def mod_(fn, state: State):
        node = adapters.Mod(state)
        parts = []
        for child in state.get_child_asts():
            if child.type == "mod":
                parts.extend(fn.apply(state.but_with(
                    ast=child,
                    mod=node.get_entered_module())))
            else:
                parts.append(fn.apply(state.but_with(
                    ast=child,
                    mod=node.get_entered_module())))
        return parts

    @Visitor.for_ast_types("struct")
    def struct_(fn, state: State):
        node = adapters.Struct(state)

        struct_name_token = Pattern("('struct name xs...)").match(state.get_ast()).name

        create_ast = node.get_create_ast()
        self_name_token: ASTToken = Pattern("('create _ _ ('rets (': ('new name) _)) _)") \
            .match(create_ast).name
        attr_toks = Pattern("(': (?? attr_name) _)").map(state.get_ast(),
            into_pattern=f"('= ('. ('ref '{self_name_token.value}) attr_name) 'None)")

        create_node = adapters.Create(state.but_with(ast=create_ast))
        arg_ast = fn.apply(state.but_with(ast=create_node.get_args_ast()))
        arg_ast._list = [AST("tags", lst=[self_name_token, *arg_ast._list])]
        seq_ast = fn.apply(state.but_with(ast=create_node.get_seq_ast()))
        seq_ast._list = [*attr_toks, *seq_ast._list]
        init_ast = AST("init", lst=[arg_ast, seq_ast])
        return AST("class", lst=[struct_name_token, init_ast])

    @staticmethod
    def get_ret_names(ret_ast: AST) -> list[ASTToken]:
        if ret_ast.has_no_children():
            return []
        if ret_ast.first().type == "prod_type":
            return [m.name for m in map(Pattern("(': (?? name) _)").match, ret_ast.first()._list) if m]
        return [Pattern("('rets (': (?? name) _))").match(ret_ast).name]

    @Visitor.for_ast_types("def")
    def def_(fn, state: State):
        node = adapters.Def(state)
        return_vars = Pattern("(': (?? ret_name) _)").map(node.get_rets_ast(),
            into_pattern=f"('= ret_name 'None)")
        ret_names = ToPython.get_ret_names(node.get_rets_ast())
        arg_ast = fn.apply(state.but_with(ast=node.get_args_ast()))
        seq_ast = fn.apply(state.but_with(
            ast=node.get_seq_ast(),
            ret_names=ret_names))
        returns = AST(type="return", lst=([] if not ret_names else [AST("tags", lst=ret_names)]))
        seq_ast._list = [*return_vars, *seq_ast._list, returns]
        return AST("def", lst=[ASTToken(["TAG"], value=node.get_function_instance().get_full_name()), arg_ast, seq_ast])

    @Visitor.for_ast_types("return")
    def return_(fn, state: State):
        if state.get_ret_names():
            return AST("return", lst=[AST("tags", lst=state.get_ret_names())])
        return AST("return", lst=[])

    @Visitor.for_ast_types("args")
    def args_(fn, state: State):
        if state.get_ast().has_no_children():
            return AST("args", lst=[])
        return AST("args", lst=[fn.apply(state.but_with_first_child())])

    @Visitor.for_ast_types(":")
    def colon_(fn, state: State):
        return Pattern("(': (?? name) _)").match(state.get_ast()).name

    @Visitor.for_ast_types("prod_type")
    def prod_type_(fn, state: State):
        return AST("tags", lst=[fn.apply(state.but_with(ast=child))
            for child in state.get_all_children()])

    @Visitor.for_ast_types("seq")
    def seq_(fn, state: State):
        children = state.get_all_children()
        return AST("seq", lst=[fn.apply(state.but_with(ast=child))
            for child in children])

    @Visitor.for_ast_types(*adapters.InferenceAssign.ast_types)
    def iletivar_(fn, state: State):
        return AST("=", lst=[fn.apply(state.but_with(ast=child))
            for child in state.get_all_children()])

    @Visitor.for_ast_types(*adapters.Decl.ast_types)
    def decls_(fn, state: State):
        if Pattern("(?? ('bindings xs...) _)").match(state.get_ast()):
            tags_ast = Pattern("(?? ('bindings xs...) _)").match(state.get_ast())\
                .to("('tags xs...)")

            tags_ast = Pattern("(?? name)").map(tags_ast,
                into_pattern="('ref name)")
            tags_ast = AST("tags", lst=tags_ast)

            number_of_vars = len(tags_ast)
            values = " ".join(["None"]*number_of_vars)
            values_ast = fn.create_ast(f"(tuple {values})")
            return AST("=", lst=[tags_ast, values_ast])
        else:
            return Pattern("(?? (?? name) _)").match(state.get_ast()).to("('= ('ref name) 'None)")

    @Visitor.for_ast_types("ref")
    def ref_(fn, state: State):
        return AST("ref", lst=[state.first_child()])

    @Visitor.for_ast_types("fn")
    def fn_(fn, state: State):
        instance = state.get_instances()[0]
        # if the function instance is a constructor we don't need
        # to append the function signature
        if instance.is_constructor:
            ast = state.get_ast()
        else:
            ast = AST(
                type="fn",
                lst=[ASTToken(type_chain=["TAG"],
                    value=instance.get_full_name())])
        if instance.no_lambda:
            return Pattern("('fn name)").match(ast).to("('ref name)")
        return Pattern("('fn name)").match(ast)\
            .to("('call ('ref 'lmda) ('params name))")

    @Visitor.for_ast_types("is_call")
    def is_call(fn, state: State):
        lst = []
        for child in state.get_all_children():
            lst.append(fn.apply(state.but_with(ast=child)))
        return AST(type="call", lst=lst)
        return Pattern("('is_call ('fn name) xs...)").match(state.get_ast())\
            .to("('call ('ref name) xs...)")

    @Visitor.for_ast_types("call")
    def all_(fn, state: State):
        if adapters.Call(state).is_print():
            other_params = state.second_child()[1:]
            value: str = state.second_child().first().value
            base = ASTToken(type_chain=["str"], value=value.replace("%i", "{}"))
            return AST("call", lst=[
                fn.apply(state.but_with_first_child()),
                AST("params", lst=[
                    AST("call", lst=[
                        AST(".", lst=[
                            base,
                            AST("ref", lst=[ASTToken(type_chain=["TAG"], value="format")])
                        ]),
                        AST("params", lst=[fn.apply(state.but_with(ast=child)) for child in other_params])
                    ]),
                    AST("named", lst=[ASTToken(["TAG"], value="end"), ASTToken(["str"], value="")])
                ])
            ])

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
        return fn.apply(state.but_with_first_child())

    @Visitor.for_ast_types("curry_call")
    def curry_call_(fn, state: State):
        state.get_ast()[0] = fn.apply(state.but_with_first_child())
        return Pattern("('curry_call FN ('curried XS...)").match(state.get_ast())\
            .to("('call ('. FN 'curry) ('params ('list XS...)))")

    @Visitor.for_ast_types("new_vec")
    def new_vec_(fn, state: State):
        return AST(type="list", lst=[])

    @Visitor.for_ast_types("index")
    def index_(fn, state: State):
        return state.get_ast()

    @Visitor.for_ast_types(*adapters.BindingAST.ast_types)
    def _binding(fn, state: State):
        return state.first_child()

    @Visitor.for_tokens
    def tokens_(fn, state: State):
        if state.get_ast().value == "true":
            return ASTToken(type_chain=["code"], value="True")
        if state.get_ast().value == "false":
            return ASTToken(type_chain=["code"], value="False")
        if state.get_ast().value == "nil":
            return ASTToken(type_chain=["code"], value="None")
        return state.get_ast()
