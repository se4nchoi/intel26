# 18
i, ttl, n = 0, 0, 11
while (i < n):
    ttl += i
    i += 1
print(ttl)

# 19

try:
    n = int(input("정수를 입력하세요: "))

    if (n > 20 or n < 1):
        print("입력값은 범위를 벗어났습니다.")
    else:
        print(f'합: {sum([x for x in range(1, n+1)])}')
except Exception as error:
    print("에러가 발생했습니다: ", error)


# 20
for dan in range(3,4):
    for i in range(1,10):
        print(f'{dan} x {i} = {dan*i}')

# 21
n = 1
while (n < 10):
    print(f'3 x {n} = {3*n}')
    n += 1

# 22
for i in range(5,0,-1):
    print(i)
print("발사!")

# 23 
n = 5
while (n > 0):
    print(n)
    n -= 1
print("발사!")

# 24
for i in range(1, 21):
    if i % 3 == 0:
        print(i, end=' ')
print()

# 25
n = 1
while (n < 21):
    if n % 5 == 0:
        print(n, end='')
    n += 1
print()


# 26
import math
print(math.factorial(10))

# 27
lst = [12, 7, 25, 3]
ttl = 0
for n in lst:
    ttl += n
print(ttl)


# 28
lst = [12, 7, 25, 3]
lst_len = len(lst)
i, ttl = 0, 0
while (i < lst_len):
    ttl += lst[i]
    i += 1
print(ttl)

# 29

try:
    n = int(input("값을 입력하세요: "))

    if (n > 50 or n < 1):
        print("입력값은 범위를 벗어났습니다.")
    else:
        for i in range(n+1):
            if i % 3 == 0:
                print("Fizz", end=' ')
            elif i % 5 == 0:
                print("Buzz", end=' ')
            elif i % 15 == 0:
                print("FizzBuzz", end=' ')
            else:
                print(i, end=' ')
        print()
except Exception as error:
    print("에러가 발생했습니다: ", error)


# 30

try:
    n = int(input("값을 입력하세요: "))

    for i in range(1, n+1):
        if n % i == 0:
            print(i, end=" ")
    print()
except Exception as error:
    print("에러가 발생했습니다: ", error)


# 31

s = 'a1b2c3'
num_str = ''
for char in s:
    if char in '0123456789':
        num_str += char
print(num_str)