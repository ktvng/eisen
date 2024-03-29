from __future__ import annotations
from alpaca.config._config import Config
from alpaca.clr import AST, ASTToken, ASTElements
from alpaca.parser._builder import Builder

class CommonBuilder(Builder):
    @classmethod
    def _filter(cls, config: Config, components: ASTElements) -> ASTElements:
        return [c for c in components
            if  (isinstance(c, ASTToken)
                    and not c.is_classified_as("keyword")
                    and not c.is_classified_as("symbol")
                    and not c.is_classified_as("operator"))
                or isinstance(c, AST)]

    @classmethod
    def flatten_components(cls, components: list[ASTToken | AST | ASTElements]) -> ASTElements:
        flattened_components = []
        for comp in components:
            if isinstance(comp, list):
                flattened_components += comp
            else:
                flattened_components.append(comp)

        return flattened_components

    @Builder.for_procedure("build_operator")
    def _build_operator(
            fn,
            config: Config,
            components: ASTElements,
            *args) -> ASTElements:

        flattened_comps = CommonBuilder.flatten_components(components)
        operators = [elem for elem in flattened_comps if isinstance(elem, ASTToken) and elem.is_classified_as("operator")]
        if len(operators) != 1:
            raise Exception("There should be only one operator in the build_operator procedure")

        operator = operators[0]
        children = [elem for elem in flattened_comps if elem != operator]
        return [AST(
            type=operator.type,
            lst=children,
            line_number=operator.line_number)]

    @Builder.for_procedure("filter_build")
    def filter_build_(
            fn,
            config: Config,
            components: ASTElements,
            *args) -> ASTElements:

        newCLRList = CommonBuilder.build(fn, config, components, *args)[0]
        filtered_children = CommonBuilder._filter(config, newCLRList)

        newCLRList[:] = filtered_children
        return [newCLRList]

    @Builder.for_procedure("filter_pass")
    def filter_pass(
            fn,
            config : Config,
            components : ASTElements,
            *args) -> ASTElements:

        return CommonBuilder._filter(config, components)

    @Builder.for_procedure("build")
    def build(
            fn,
            config: Config,
            components: ASTElements,
            build_name: str,
            *args) -> ASTElements:

        flattened_components = CommonBuilder.flatten_components(components)
        if not flattened_components:
            raise Exception("flattened_components must not be empty")

        newCLRList = AST(build_name, flattened_components, flattened_components[0].line_number)
        return [newCLRList]

    @Builder.for_procedure("pool")
    def pool_(
            fn,
            config: Config,
            components: ASTElements,
            *args) -> ASTElements:

        pass_up_list = []
        for component in components:
            if isinstance(component, list):
                pass_up_list += component
            elif isinstance(component, ASTToken) | isinstance(component, AST):
                pass_up_list.append(component)
            else:
                print(type(component))
                raise Exception("reverse engineering with pooling must be either CLRRawList, CLRList, or CLRToken")
        return pass_up_list


    @Builder.for_procedure("pass")
    def pass_(
            fn,
            config: Config,
            components: ASTElements,
            *args) -> ASTElements:

        return components


    @Builder.for_procedure("convert")
    def convert_(
            fn,
            config: Config,
            components: ASTElements,
            name: str,
            *args) -> ASTElements:

        if len(components) != 1:
            for c in components:
                print(c)
            raise Exception(f"expects size of 1 but got {len(components)}")

        if isinstance(components[0], AST):
            components[0].set_type(name)
        elif isinstance(components[0], ASTToken):
            components = [AST(name, components, components[0].line_number)]
        return components
