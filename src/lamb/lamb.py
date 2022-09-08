from __future__ import annotations

import alpaca

class LambBuilder(alpaca.parser.CommonBuilder):
    @alpaca.parser.CommonBuilder.for_procedure("filter_build")
    def filter_build_(
            fn,
            config : alpaca.config.Config,
            components : alpaca.clr.CLRRawList, 
            *args) -> alpaca.clr.CLRRawList: 

        newCLRList = LambBuilder.build(fn, config, components, *args)[0]
        filtered_children = LambBuilder._filter(config, newCLRList)

        newCLRList[:] = filtered_children
        return [newCLRList]

class LambInterpreter(alpaca.utils.Wrangler):
    def __init__(self):
        super().__init__()

    def run(self):
        pass

class LambRunner():
    @classmethod
    def run(cls, file_name: str):
        pass



# #####################################################
# class AbstractContext():
#     def __init__(self, params : dict = {}):
#         self.params = params

#     def add(self, key : str, val):
#         self.params[key] = val

#     def get(self, key : str):
#         return self.params.get(key, None)


# def ts(astnode : ASTNode, closure={}):
#     if astnode.match_with() == "lambda":
#         return f"\L {ts(astnode.children[0], closure)}.{ts(astnode.children[1], closure)}"
#     elif astnode.match_with() == "TAG":
#         if astnode.value in closure:
#             return obj_ts(closure[astnode.value])
#         return astnode.value
#     elif astnode.match_with() == "apply":
#         return f"({ts(astnode.children[0], closure)} {ts(astnode.children[1], closure)})"
        
# def obj_ts(obj):
#     if obj["type"] == "lambda":
#         return f"\L {obj['binds']['name']}.{ts(obj['body'], obj['closure'])}"
#     if obj["type"] == "def":
#         return ts(obj["body"])
#     if obj["type"] == "tag":
#         return obj["name"]




# def visit(astnode : ASTNode, cx : AbstractContext):
#     return astnode.visitor.visit(astnode, cx)

# # class print_(AbstractVisitor2):
#     matches = ["print"]

#     def visit(self, astnode: ASTNode, cx: AbstractContext):
#         obj = visit(astnode.children[0], cx)
#         print(obj_ts(obj))
#         return obj

# class start_(AbstractVisitor2):
#     matches = ["start"]

#     def visit(self, astnode: ASTNode, cx: AbstractContext):
#         results = [visit(child, cx) for child in astnode.children]
#         return results

# class lambda_(AbstractVisitor2):
#     matches = ["lambda"]

#     def visit(self, astnode: ASTNode, cx: AbstractContext):
#         name = visit(astnode.children[0], cx)
#         return {
#             "type": "lambda", 
#             "closure": { **cx.params["scope"] }, 
#             "binds": name, 
#             "body": astnode.children[1]}

# class tag_(AbstractVisitor2):
#     matches = ["TAG"]
    
#     def visit(self, astnode: ASTNode, cx: AbstractContext):
#         found_value = cx.params["scope"].get(astnode.value, None)
#         if found_value is not None:
#             return found_value

#         return {
#             "type": "tag", 
#             "name": astnode.value}
    
# class def_(AbstractVisitor2):
#     matches = ["def"]

#     def visit(self, astnode: ASTNode, cx: AbstractContext):
#         name = visit(astnode.children[0], cx)["name"]
#         obj = {
#             "type": "def",
#             "body": astnode.children[1]}
#         cx.params["scope"][name] = obj
#         return obj
    
# class apply_(AbstractVisitor2):
#     matches = ['apply']

#     def visit(self, astnode: ASTNode, cx: AbstractContext):
#         fn = visit(astnode.children[0], cx)
#         arg = visit(astnode.children[1], cx)

#         if arg["type"] == "def":
#             arg = visit(arg["body"], cx)
#         if fn["type"] == "def":
#             fn = visit(fn["body"], cx)

#         if fn["type"] != "lambda":
#             raise Exception("apply expects function as first argument")

#         bound_tag = fn["binds"]["name"]
#         fn["closure"][bound_tag] = arg
#         new_scope = { **cx.params["scope"], **fn["closure"] }
#         new_cx = AbstractContext({ "scope": new_scope })

#         return visit(fn["body"], new_cx)

# #####################################################
# class LambRunner():
#     def __init__(self):
#         self.build_map = {}

#     visitors = [
#         # start_,
#         # lambda_,
#         # tag_,
#         # apply_,
#         # def_,
#         # print_,
#     ]

#     def run(self, ast : alpaca.clr.AST):
#         self._create_build_map()
#         self._add_visitors(ast.head)
#         global_context = AbstractContext({"scope": {}})
#         return visit(ast.head, global_context)

#     def _create_build_map(self):
#         for visitor in self.visitors:
#             for match in visitor.matches:
#                 self.build_map[match] = visitor

#     def _add_visitors(self, astnode : ASTNode):
#         visitor = self.build_map.get(astnode.match_with(), None)
#         if visitor is None:
#             raise Exception(f"cannot find visitor matching {astnode.match_with()}")

#         astnode.visitor = visitor()
#         for child in astnode.children:
#             self._add_visitors(child)

        