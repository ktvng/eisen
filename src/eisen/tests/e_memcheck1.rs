struct ptr {
    x: int var

    create(x: int var) -> self: ptr {
        self.x = x
    }
}

fn select(a: int var, b: int var) -> c: int var {
    if (a < 4) {
        c = a
    }
    else {
        c = b
    }
}

fn cond(a: int var) -> c: int var {
    var x: int
    if (a == 4) {
        let y = 4
        x = y
    }
}

fn one(a: int var, b: int var) -> c: int var {
    let y = 5
    c = select(a, b)
    c = select(a, y)
}

fn make_ptr(a: int var) -> p: ptr {
    let y = 5
    p = ptr(y)
    let p2 = ptr(y)
}

fn make_ptr2(a: int var) -> p: ptr {
    p = ptr(a)
}


fn main() {
    let myInt = 0
    var a, b: int
    a = myInt
    b = myInt

    a = one(a, b)
    let p: ptr
    p = make_ptr(a)

    let p2: ptr
    p2 = make_ptr(a)
}
