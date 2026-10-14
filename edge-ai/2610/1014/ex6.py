def introduce(name="아무개", age=20):
    print(f'안녕하세요, 제 이름은 {name}이고 {age}살 입니다.')
introduce()

n = int(input("정수를 입력하세요: "))
def check_even_odd(num):
    ch = "짝수" if num % 2 == 0 else "홀수"
    print(f'{num} = {ch}입니다.')
check_even_odd(n)

score = int(input("점수를 입력하세요: "))
def is_passed(score):
    decision = "합격" if score >= 80 else "불합격"
    print(f'판정: {decision}')
is_passed(score)


first = input("성을 입력하세요: ").strip()
last = input("이름을 입력하세요: ").strip()
def make_fullname(first_name, last_name):
    print(f'{last_name + first_name}님, 안녕하세요!')
make_fullname(last_name=last,first_name=first)


a,b,c = map(int, input("숫자 3개를 한 줄에 띄워서 입력하세요 (예: 1 2 3): ").split())
def find_max(a,b,c):
    big = a if a > b else b
    big = c if c > big else big
    print(f'가장 큰 수: {big}')
find_max(a,b,c)


def unique_sorted(lst):
    unique = set(lst)
    return sorted(list(unique))
unique_sorted([5, 2, 8, 2, 1, 5, 9])


def sum_positives(lst):
    pos = [x for x in lst if x >= 0]
    return sum(pos)

sum_positives([5, -2, 10, -7, 3])

def count_letters(str):
    s = [c for c in str if c != " "]
    return len(s)

count_letters("Hello Python World")

input_age = int(input("나이를 입력하세요: "))
def get_ticket_type(age):
    ticket_type = "" 
    if 0 <= age < 13:
        ticket_type = "어린이"
    elif 13 <= age < 19:
        ticket_type = "청소년"
    else:
        ticket_type = "성인"
    print(f'{age}세: {ticket_type} 요금 적용')

get_ticket_type(input_age)


def sum_all(*args):
    inputs = []
    for n in args:
        inputs.append(n)
    return sum(inputs)
print(f'합계: {sum_all(1,2,3,4,5)}')

def calc_bmi(height, weight):
    return round(weight/((height/100)**2),1)
print(f'BMI 지수: {calc_bmi(height=175, weight=70)}')

def clean_code(str):
    s = str.strip().replace(" ", "")
    s = s.upper()
    return(s)
print(f'변환 결과: {clean_code("   python_quiz   ")}')

n = int(input("정수를 입력하세요: "))
def get_multiples_of_3(n):
    return [x for x in range(1,n+1) if x % 3 == 0]
print(f'3의 배수 리스트: {get_multiples_of_3(n)}')

test_word = input("단어를 입력하세요: ")
def is_palindrome(word):
    w = word.strip()
    j = -1
    for i in range(len(word)//2):
        if word[i] != word[j]:
            return False
        j -= 1
    return True
print(f'{test_word}: {is_palindrome(test_word)}')