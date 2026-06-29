"""
recalling : conditional statements

if, elif, else...

conditionals are the fundamental way we can implement "control", or logic
and, logic is how we translate core ideas into real things with the computer 


"""

"""
after conditionals, of course, we should dive into LOOPs

while, for

"""

"""
Q.1 sum from 1 to 100

Q.2 sum from 1 to 100, only odd

Q.3 sum multiples of 6 from 1 to 100
"""

def answering_machine(question):
  match question:
    case 1:
      total = 0
      for i in range(1, 101):
        total += i
      print(total)
    case 2:
      total = 0
      for i in range(1, 101):
        if (i % 2):
          total += i
      print(total)
    case 3:
      total = 0
      for i in range(1, 101):
        if not (i % 6):
          total += i
      print(total)
    case _:
      print("not a valid question number!")
      pass
  return 0

#answering_machine(1)
#answering_machine(2)
#answering_machine(3)
#answering_machine(4)

"""
mirror looping as a 'sequence' ?

while robot is ON:
    read camera
    estimate pose
    plan motion
    move motors
    
or..

for product in conveyor:
    result = inspect()
    if result == defective:
        reject
    else:
        package
"""

"""
draw 
*
**
***
****
*****
and
    *
   **
  ***
 ****
*****
+
center aligned pyramid
+
center aligned diamond

==> initial thought is to just utilize f-string formatting with for loops
"""

# with the help of gemini
def print_mixed_star_shapes(rows=4):
    # 1) Left Aligned (Linear: 1, 2, 3, 4)
    print("1) Left Aligned")
    for i in range(1, rows + 1):
        print(f"{'*' * i:<{rows}}")

    # 2) Right Aligned (Linear: 1, 2, 3, 4)
    print("\n2) Right Aligned")
    for i in range(1, rows + 1):
        print(f"{'*' * i:>{rows}}")

    # Calculate max width based on the bottom row for odd progressions (1, 3, 5, 7)
    max_width_odd = (rows * 2) - 1

    # 3) Center Aligned (Odd: 1, 3, 5, 7)
    print("\n3) Center Aligned")
    for i in range(1, rows + 1):
        stars = '*' * ((i * 2) - 1)
        print(f"{stars:^{max_width_odd}}")

    # 4) Diamond (Odd: 1, 3, 5, 7, 5, 3, 1)
    print("\n4) Diamond")
    # Top half (inclusive of middle row)
    for i in range(1, rows + 1):
        stars = '*' * ((i * 2) - 1)
        print(f"{stars:^{max_width_odd}}")
    # Bottom half (shrinking)
    for i in range(rows - 1, 0, -1):
        stars = '*' * ((i * 2) - 1)
        print(f"{stars:^{max_width_odd}}")

# print_mixed_star_shapes(4)

# lambda practice
messy_names = ["   alice ", "BOB", "  cHArLie  "]
clean_names = list(map(lambda name: name.strip().lower().capitalize(), messy_names ))

lc_clean_names = [name.strip().title() for name in messy_names]
# print(lc_clean_names)
# print(clean_names)
# Expected Output: ['Alice', 'Bob', 'Charlie']

# list comp
numbers = [1, 2, 3, 4, 5]
squares = [x**2 for x in numbers if x % 2]
# print(squares)