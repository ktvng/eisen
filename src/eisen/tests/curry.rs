fn add(x: int, y: int) -> r: int {
    r = x + y
}

fn main() {
    let f = add
    let h = add<4>
    let g = h<4>
    let k = add<8, 1>

    print("%i %i %i %i", f(4, 2), h(3), g(), k())
    print(" %i", h(6))
}
