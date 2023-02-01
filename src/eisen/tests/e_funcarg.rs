fn bad(a: int, b: int) -> c: int var {
    c = b
}

fn good(a: int, b: int) -> c: int var {
    c = a
}

fn pass(f: (int) -> int var, b: int) -> c: int var {
    let x = 4
    c = f(x)
}

fn main() {
    let f = bad<12>
    let g = good<19>
    print("%i", pass(g, 5))
    print("%i", pass(f, 5))
}
