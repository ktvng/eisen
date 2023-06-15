struct obj {
    x: int

    create(x: int) -> self: obj {
        self.x = x
    }
}

struct refs {
    o: obj var

    create(o: obj var) -> self: refs {
        self.o = o
    }
}

fn select_o(r: refs, o: obj) {
    let o3 = obj(3)
    select_o(r, o3, o)
}

fn select_o(r: refs, oA: obj, oB: obj) {
    r.o = oA
}

fn main() {
    let o1 = obj(1)
    let o2 = obj(2)
    let r = refs(o1)

    if (true) {
        r.o = o2
    }
    else {
        let o4 = obj(4)
        r.o = o4
    }

    select_o(r, o2)
    print("%i", r.o.x)
    return
}
