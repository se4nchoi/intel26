# Lecture - Python OOP & NumPy Fundamentals

**Date:** 2024-07-06

## Topics Covered

*   **Object-Oriented Programming (OOP) in Python**
    *   Class definition (`class`)
    *   Constructor (`__init__`)
    *   Instance vs. Class variables
    *   Special "dunder" methods (`__str__`, `__add__`) for operator overloading
*   **Introduction to NumPy**
    *   Creating `ndarray` objects (`np.array`, `np.zeros`, `np.arange`, `np.linspace`)
    *   Array attributes (`.shape`, `.ndim`, `.dtype`, `.size`)
    *   Vectorized (element-wise) operations
    *   Indexing and slicing

---

## Practice Implementations

*   **`lessons.py`**: Implemented `TeleVision` and `Rectangle` classes to practice OOP concepts.
    *   The `TeleVision` class demonstrates instance and class variables (for serial numbers).
    *   The `Rectangle` class overloads the `+` operator using `__add__` to combine two rectangles.
*   **`Car.py`**: A simple `Car` class to demonstrate basic class structure, methods, and `__str__` for a clean string representation.
*   **`numpy_practice.py`**: A script covering fundamental NumPy operations, serving as a reference for creating and manipulating numerical arrays efficiently.

---

## Key Takeaways

### Object-Oriented Programming

Classes allow us to model real-world entities by bundling data (attributes) and behavior (methods) together. This is a powerful way to structure complex applications. Using dunder methods like `__str__` and `__add__` makes our custom objects behave more intuitively, integrating them smoothly with Python's built-in syntax.

### NumPy for Numerical Computing

NumPy is the cornerstone of the scientific Python ecosystem. Its core strength lies in the `ndarray` object, which enables efficient, vectorized operations on large datasets. This avoids slow, explicit loops in Python. Understanding NumPy is essential for any work in data analysis, machine learning, or scientific computing.

```python
# Instead of a Python loop:
result = []
for i in range(len(a)):
    result.append(a[i] + b[i])

# NumPy's vectorized approach is faster and more readable:
result = a + b
```

The ability to perform mathematical operations on entire arrays at once is a fundamental shift from standard Python lists and is key to performance.