from __future__ import annotations
from parser._abstractbuilder import AbstractBuilder
from asts import ASTNode
from error import Raise

class CommonBuilder(AbstractBuilder):
    build_map = {}

    def _build_procedure(build_map, name):
        def _decorator(f):
            def pure_f(*args, **kwargs):
                return f(CommonBuilder, *args, **kwargs)
                
            build_map[name] = pure_f

            return f

        return _decorator

    @classmethod
    def flatten_components(cls, components : list[ASTNode | list[ASTNode]]) -> list[ASTNode]:
        flattened_components = []
        for comp in components:
            if isinstance(comp, list):
                flattened_components += comp
            else:
                flattened_components.append(comp)

        return flattened_components

    @classmethod
    @_build_procedure(build_map, "build")
    def build(cls, components : list[ASTNode], build_name : str, *args) -> list[ASTNode]:
        flattened_components = CommonBuilder.flatten_components(components)
        if not flattened_components:
            Raise.code_error("flattened_components must not be empty")

        newnode = ASTNode(
            type=build_name,
            value="none",
            match_with="type",
            children=flattened_components)

        newnode.line_number = flattened_components[0].line_number
        return [newnode]


    @classmethod
    @_build_procedure(build_map, "pool")
    def pool_(cls, components : list[ASTNode], *args) -> list[ASTNode]:
        pass_up_list = []
        for component in components:
            if isinstance(component, list):
                pass_up_list += component
            elif isinstance(component, ASTNode):
                pass_up_list.append(component)
            else:
                Raise.code_error("reverse engineering with pooling must be either list or ASTNode")

        return pass_up_list


    @classmethod
    @_build_procedure(build_map, "pass")
    def pass_(cls, components : list[ASTNode], *args) -> list[ASTNode]:
        return components


    @classmethod
    @_build_procedure(build_map, "convert")
    def convert_(cls, components : list[ASTNode], name : str, *args) -> list[ASTNode]:
        if len(components) != 1:
            Raise.code_error("expects size of 1")

        components[0].type = name
        return components