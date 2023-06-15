fn apply(x: int, f: (int) -> int) -> result: int {
    result = f(x)
}

fn times(x: int, f: () -> void) -> result: int {
    result = 0
    while (x > 0) {
        x -= 1
        f()
    }
}

fn moo() {
    print("moo ")
}

fn double(x: int) -> r: int {
    r = x + x
}

fn main() {
    print("%i ", 10.apply(double))
    5.times(moo)
}
