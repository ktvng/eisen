fn main() {
    print("%i", fib(7))
}

fn fib(n: int) -> nth_fib: int {
    if(n == 0) {
        nth_fib = 0
    }
    else if(n == 1) {
        nth_fib = 1
    }
    else {
        nth_fib = fib(n - 1) + fib(n - 2)
    }
}