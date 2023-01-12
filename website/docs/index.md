# Eisen, A Programming Language
Eisen is a conceptual language that pushes the notions of what a programming language should be. It's low level, like C/C++, compiling to machine code and providing very minimal support for memory management. It doesn't try to do everything, but what it does try is to provide the _right_ kind of abstraction; the kind that engineers _want_ to use because they're low cost and reduce complexity.

That's the fundemental drive of Eisen. Complexity leads to error; error leads to sadness; most people agree that sadness is bad. That's it.

## Overview
After a particularly dark and souless day of C++ development, Eisen was born.

```eisen
fn main() {
    print("hello world")
}
```

Eisen draws inspiration from Rust, Go, and many other languages out there. We try to balance the dream of abstraction with the reality that machines operate on verbose exactness. 

## Get Started
Currently, the Eisen compiler is written in Python (... yes I know, deal with it). You can play around with it by cloning the repository and following the readme there.
```sh
$ git clone https://github.com/ktvng/eisen.git
```

You can run the tests with the following command
```sh
$ python ./src/main.py -t
```

## Vision
Eisen is currently in prototype state, and there's no definitive plans to create a production ready standard (this is a lot of work, and it's very small here). 

But we hope that Eisen serves as a demonstration and an example of what is possible. Named after the historic Stanley Eisenstat (affectionately know as Stan), a tenured Professor at Yale University, and cannonical guardian of the CPSC323 gateway, we hope that likewise, Eisen manages to inspire others.

