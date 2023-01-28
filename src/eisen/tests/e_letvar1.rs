struct point {
    x: int
    y: int

    create() -> self: point {
        self.x = 0
        self.y = 0
    }
}

fn main() {
    let p = point()
    p = point()
    let p2: point

    var myP = p
    p2 = myP

    let p3: point
    p3 = p
}
