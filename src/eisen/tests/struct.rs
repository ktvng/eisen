fn main() {
    let p = point(1, 2)
    print("%i %i", p.x, p.y)

    p.x = 5
    p.y = 15
    print(" %i", p.x + (p.y))
}

struct point {
    x: int
    y: int

    create(x: int, y: int) -> self: point {
        self.x = x
        self.y = y
    }
}