fn max(x: int var, y: int var) -> r: int var {
    if (x > y) {
        r = x
    }
    else {
        r = y
        // should not be able to edit memory that is passed in!
        // y <- 0
    }
}

fn letwhy(x: int) -> r: int {
    r = x
}

fn main() {
    let a, b = 15, 9
    var x = max(a, b)
    print("%i ", x)
    a = 4
    print("%i ", x)

    x = max(a, b)
    print("%i", x)
}
