from llvmlite import ir

# TODO: move this to seer
class IrTypes():
    char = ir.IntType(8)
    bool = ir.IntType(1)
    int = ir.IntType(32)
    float = ir.FloatType()
