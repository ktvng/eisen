class Options():
    """
    Used to supply additional parameters to IRGenerationProcedure(s) without having to modify
    the precompile/compile signatures
    """

    def __init__(self, should_not_emit_ir : bool=False):
        self.should_not_emit_ir = should_not_emit_ir
