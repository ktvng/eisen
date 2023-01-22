fn swap(a: int var, b: int var) -> x: int var, y: int var {
    let n = 4
    var t, t2: int
    t = x
    t2 = x

    // this is okay because the if only executes once
    if (true) {
        x = b
        y = t2
        t2 = n
    }

    // this throws an exception because the while could execute multiple times
    while(true) {
        x = b
        y = t
        t = n
    }
}

fn main() {
    var a, b: int
    let x, y = 2, 3
    swap(x, y)
}
