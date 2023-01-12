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

    var myP = p
    p = myP

    let p2 = point()
    p = p2
}
