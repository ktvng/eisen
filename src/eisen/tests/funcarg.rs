fn mul(a: int, b: int) -> c: int {
    c = a * b
}

fn red(f: (int) -> int, x: int) {
    print("%i ", f(x))
}

fn blue(f: (int, int) -> int, x: int) {
    print("%i ", f(x, x))
}

fn main() {
    let f = mul<5>
    red(f, 25)
    let g = mul
    blue(g, 5)
    blue(mul, 10)
}
