from compiler import visitor

class Visitors():
    build_map = {}

    from ._procedures._basic import string_, int_, bool_, tag_, var_
    from ._procedures._shared import default_, unwrap_
    from ._procedures._var_decl import var_decl_, let_
    from ._procedures._function_call import function_call_
    from ._procedures._function import function_, return_
    from ._procedures._assigns import assigns_
    from ._procedures._bin_op import bin_op_
    from ._procedures._if_statement import if_statement_
    from ._procedures._while_statement import while_statement_

    visitor(build_map, string_)
    visitor(build_map, int_)
    visitor(build_map, bool_)
    
    visitor(build_map, tag_)
    visitor(build_map, var_)
    visitor(build_map, default_)
    visitor(build_map, unwrap_)
    visitor(build_map, var_decl_)
    visitor(build_map, let_)
    visitor(build_map, function_call_)
    visitor(build_map, function_)
    visitor(build_map, return_)
    visitor(build_map, assigns_)
    visitor(build_map, bin_op_)
    visitor(build_map, if_statement_)
    visitor(build_map, while_statement_)
