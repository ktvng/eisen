struct Integer {
    value: int

    create(value: int) -> self: Integer {
        self.value = value
    }
}

fn max(x: Integer var, y: Integer var) -> r: Integer var {
    if (x.value > y.value) {
        r = x
    }
    else {
        r = y
    }
}

fn main() {
    let a, b = Integer(15), Integer(9)
    var x = max(a, b)
    print("%i ", x.value)
    a.value = 4
    print("%i ", x.value)

    x = max(a, b)
    print("%i", x.value)
}
