"""
# 'AI' lecture 2...
# strings, memory, variables
# all very basic level of intro to python

# i believe I am ... rusty on tooling, but not too rusty on logical thinking?

I can set up logical processes; just need to know the tooling? but what if
logical processes exceed your capable knowledge?

if you know what you want to achieve, can AI help me work through the problem?

But then again, I need to produce visible, tangible OUTPUT in order to gauge 
my actual capacity.


NotebookLM-based learning .
Feynman Technique .

"""

def stringTest():
  # f-strings
  test_str = "python expertise"
  print(f"testing out my {test_str} in practice!")

  # f string output formatting
  price_array = [42.3, 9.99, 10, 1688.1]
  for price in price_array:
    print(f"${price:>20.2f}")


"""
considering it is 1st week, 2nd session (other that the half-ass 
1st session with 4hrs of environment settings...), i guess this is the standard
to expose non-technical background members to the coding world.

variables, literals, functions, data types. input, output (print).
all things that I myself had once walked the baby steps in years 1 and 2 during
university. C, C++, python. ah the memories.

so how could I utilize the current boring session ?

"""

"""
두개 정수 입력, 사칙연산 결과 출력
"""
def Q1():
  while 1:
    try:
      a = int(input("Enter first number: "))
      b = int(input("Enter second number: "))

      print(f"Entered numbers: {a} and {b}")
      print(f"a + b = : {a + b}")
      print(f"a - b = : {a - b}")
      print(f"a * b = : {a * b}")
      print(f"a / b = : {a / b}")    
      
      break
    except ValueError:
      print("Entered numbers are not integers!")
  return 0
"""
5개 정수 값 입력; 리스트에 저장; 리스트 합, 평균, 최소, 최대 값 출력
"""
def Q2():
  while 1:
    try:
      a = int(input("Enter first number: "))
      b = int(input("Enter second number: "))
      c = int(input("Enter third number: "))
      d = int(input("Enter fourth number: "))
      e = int(input("Enter fifth number: ")) 

      num_list = [a, b, c, d, e]
      
      # sum
      list_sum = 0
      for num in num_list:
        list_sum += num
      print(f"Sum : {list_sum}")
      
    
      # avg
      avg = list_sum / len(num_list)
      print(f"Average : {avg}")
      
      # min, max
      list_min = min(num_list)
      list_max = max(num_list)
      print(f"Min : {list_min}")
      print(f"Max : {list_max}")
      break
    except ValueError:
      print("Entered numbers are not integers!")
  return 0
"""
과일명 리스트 정의; 리스트 첫+마지막ㄱ string 출력
"""
def Q3():
  fruits = []
  for i in range(5):
    fruit = input("Enter fruit name: ")
    fruits.append(fruit)
    
  print(fruits[0])
  print(fruits[-1])


# -------------------------------------
# dictionaries !



# ============= EXECUTION =============
#Q1()
#Q2()
#Q3()

# and... operators

# and... if/else statements

"""
*python treats all literals as an OBJECT
a = 1           
b = a 
looks like 

addr  |   val
---------------
0x100 |   1         [somewhere in the heap]
...
0x200 |   0x100     [a]
0x204 |   0x100     [b]

therefore b = 2 is treated as 
    b = (0x204)* = 0x100 = 2
and change print(a) = 2
"""

"""
all concepts are not new to me.
elevated thinking ? 
relating these into computer architecture concepts : 

  how does the CPU / computer ACTUALLY carry out the high-level language ?
  -> do arithmetic, move data (registers), change stack pointer positions 
    for execution, and do logical expressions
  
operators => CPU does only 1 thing; ADD. 
  - subtraction is A - B ==> A + (-B) using 2's compliment
  - mult is A * 10 ==> A + A + A ....
  - division is A / 2 ==> A + (-2) + (-2) + ...

if/else -> remember the execution stack pointer, jump to where the if/else
code block address is depending on conditional expression (true/false)
"""

# famous example of arithmetic, comparison, logical
# why? because 365.24 (not quite 0.25)
# so every 4 years is almost correct; skipping every 400 years balances this
def is_leapyear(year):
  if year % 4 == 0 and year % 100 != 0 or year % 400 == 0:
    return True
  else:
    return False
  
def Q4():
  year = int(input("Enter year: "))
  if (is_leapyear(int(year))):
    print(f"{year} is a leap year!")
  else:
    print(f"{year} is not a leap year!")
      
  return 0

#Q4()
