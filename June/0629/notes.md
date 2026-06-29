# Python Fundamentals II — Control Flow & File I/O

> *"Do not be bored. Find the deeper meaning inside."*

---

## Today's Lecture

Topics covered:

* Conditional statements (`if`, `elif`, `else`)
* Loops (`for`, `while`)
* Pattern generation with nested loops
* `lambda`, `map()`, list comprehensions
* File I/O
* Command line arguments (`sys.argv`)
* Basic exception handling

Most of today's lecture was review, but it served as a good opportunity to reconnect basic programming concepts with real engineering systems.

---

# Control Flow

Programming is fundamentally about **control**.

Conditionals allow software to make decisions based on the current state of the world.

```python
if condition:
    ...
elif another_condition:
    ...
else:
    ...
```

Examples:

* Emergency stop logic
* Sensor threshold detection
* Quality inspection
* Robot state transitions

---

# Loops

Loops are not simply "repeating code."

They describe **repeated interaction with a system**.

Instead of writing an instruction many times, define:

* what should happen
* what should be repeated

Examples:

```python
for product in conveyor:
    inspect(product)
```

```python
while robot_running:
    observation = read_sensors()
    state = estimate(observation)
    action = planner(state)
    execute(action)
```

This general loop appears everywhere:

* PLC scan cycles
* Robotics
* Embedded systems
* Computer vision
* AI inference

The syntax changes very little.

The system changes.

---

# Pattern Generation

The star-printing exercises were simple, but reinforced several useful concepts.

* nested loops
* iteration
* indexing
* formatting

Sometimes beginner exercises aren't about the output.

They're about learning how to think recursively and systematically.

---

# Python Features Worth Remembering

### List Comprehension

Very readable for simple transformations.

```python
clean_names = [
    name.strip().title()
    for name in messy_names
]
```

---

### Lambda

Useful for small anonymous functions.

Powerful, but should remain readable.

---

### File I/O

Most software eventually follows the same pattern.

```
Read
    ↓
Process
    ↓
Store
```

Examples:

* robot logs
* AI datasets
* sensor measurements
* PLC event logs
* configuration files

---

### Exception Handling

Handle failures intentionally.

```python
except FileNotFoundError:
```

is almost always preferable to

```python
except:
```

because it documents the expected failure.

---

# Small Code Quality Notes

* Prefer `total` over `sum` (don't shadow Python built-ins)
* Prefer returning values instead of printing inside functions
* Comments should explain *why*, not *what*

---

# Engineering Perspective

Today's biggest takeaway wasn't Python syntax.

It was recognizing that simple programming constructs become the foundation for complex systems.

| Programming | Engineering Example      |
| ----------- | ------------------------ |
| `if`        | Safety logic             |
| `for`       | Conveyor inspection      |
| `while`     | Robot control loop       |
| Function    | Reusable robot behaviour |
| File I/O    | Sensor logging           |
| Exceptions  | Fault recovery           |

The abstraction remains the same.

Only the application changes.

---

# Personal Reflection

Today's Python lecture was below my current programming level.

Instead of checking out mentally, I tried to practice a different skill:

> extracting engineering meaning from simple material.

Going forward, every lecture should answer two questions:

1. **What is the underlying computer science idea?**
2. **Where does this appear in robotics, automation, or AI?**

If I can answer both consistently over the next six months, the lectures will become much more valuable than simply learning syntax.

---

# Questions for Later

* How is a PLC scan cycle implemented internally?
* Why are many industrial robots still programmed with PLCs instead of Python?
* Where does Python stop being sufficient and C/C++ become necessary?
* How do modern Physical AI systems combine perception, planning, and control?
