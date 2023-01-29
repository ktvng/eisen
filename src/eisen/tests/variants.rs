struct point {
    x: int
    y: int

    create(x: int, y: int) -> self: point {
        self.x = x
        self.y = y
    }
}

variant origin of point {
    is(self: point) -> result: bool {
        result = self.x == 0 and self.y == 0
    }
}

fn say(p: point) {
    print("point ")
}

fn say(p: origin) {
    print("origin ")
}

fn main() {
    let p = point(5, 5)
    p.say()
    if (p is origin) {
        print("yes ")
    }

    p.x = 0
    p.y = 0
    if (p is origin) {
        p.as(origin).say()
    }
}
