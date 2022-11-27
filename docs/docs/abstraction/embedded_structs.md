# Embedded Structs
While member functions and interfaces allow for powerful abstraction via polymorphism, embedded structs solves a different problem.

Most modern languages use classes/inheritence as a one-stop shop solution to abstraction, providing polymorphism and code reuse and extension all in one. However this is often leads to bloat and unnecessary abstraction.

Instead, Eisen separates concerns into polymorphism (handled by member functions and intefaces) and code reuse, enabled by Embedded Structs.