# Lecture 02 - Python Fundamentals

**Date:** 2026-06-26

## Topics Covered

* Variables and literals
* Memory and variable assignment
* Primitive data types
* String formatting (`f-strings`)
* User input and output
* Functions
* Lists
* List slicing
* List comprehension
* Dictionaries (introduction)
* Arithmetic, comparison, and logical operators
* Conditional statements (`if / elif / else`)
* Exception handling (`try / except`)

---

## Practice Exercises

1. Input two integers and perform basic arithmetic operations.
2. Store five integers in a list and calculate:

   * Sum
   * Average
   * Minimum
   * Maximum
3. Store fruit names in a list and access the first and last elements.
4. Determine whether a given year is a leap year.

---

## Python Features Used

* `input()`
* `print()`
* `int()`
* `len()`
* `min()`
* `max()`
* `append()`
* `range()`
* `try / except`

---

## Additional Notes

* List comprehensions provide a concise way to construct lists.

```python
square_list = [x * x for x in range(1, 200) if x % 2 == 0]
```

* When solving problems, consider both readability and algorithmic efficiency (`O(n)`, memory usage).

---

**Reference Implementation**

See `lessons.py` for complete practice solutions and examples.


## Connections to Computer Architecture

These Python concepts can be related to lower-level computer architecture concepts:

| Python Concept         | Computer Architecture Perspective                                                                                                                                                                                                                                                             |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Variables              | Variables reference values stored in memory. At runtime, the interpreter manages these memory addresses and object references.                                                                                                                                                                |
| Arithmetic Operators   | High-level arithmetic is ultimately translated into CPU instructions. Operations such as subtraction are implemented using two's complement arithmetic, while multiplication and division may be optimized into hardware instructions or lower-level sequences depending on the architecture. |
| Conditional Statements | `if` statements are compiled/interpreted into conditional branch instructions that alter the program's execution flow.                                                                                                                                                                        |
| Functions              | Function calls create stack frames, manage parameters, local variables, and return addresses during execution.                                                                                                                                                                                |
| Lists                  | Lists are dynamic data structures managed by the Python runtime, abstracting away memory allocation and resizing.                                                                                                                                                                             |

### Engineering Perspective

Although Python abstracts away hardware details, understanding how high-level code maps onto memory, CPU instructions, and control flow provides useful intuition for writing efficient and maintainable software.
