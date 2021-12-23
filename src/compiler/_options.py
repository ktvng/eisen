class Options():
    """
    Used to supply additional parameters to IRGenerationProcedure(s) without having to modify
    the precompile/compile signatures
    """

    # TODO: visitor should not be in options; pass directly to recursive_descent
    def __init__(self, should_not_emit_ir : bool=False, visitor=None):
        self.should_not_emit_ir = should_not_emit_ir
        self.visitor = visitor
