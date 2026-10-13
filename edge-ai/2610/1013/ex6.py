# 15
try:
    n = int(input("정수를 입력하세요: "))

    if n % 2 == 1:
        print(f'{n}은 홀수 입니다.')
except Exception as error:
    print("에러가 발생했습니다: ", error)


# 16
try:
    age = int(input("나이를 입력하세요: "))
    
    if 0 <= age <= 5:
        print("영유아 입니다.")
    elif 6 <= age <= 12:
        print("아동 입니다.")
    elif 13 <= age <= 18:
        print("청소년 입니다.")
    else:
        print("성인 입니다.")
    
except Exception as error:
    print("에러가 발생했습니다: ", error)

# 17
try:
    a = int(input("정수 1: "))
    b = int(input("정수 2: "))

    big = a
    if a < b:
        big = b
    print(f'결과 {big}')
except Exception as error:
    print("에러가 발생했습니다: ", error)

# 18
try:
    a = int(input("정수 1: "))
    b = int(input("정수 2: "))

    print(f'결과: {a if a > b else b}')
except Exception as error:
    print("에러가 발생했습니다: ", error)


# 19
try:
    score = int(input("점수를 입력하세요: "))
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"
    print(grade)
except Exception as error:
    print("에러가 발생했습니다: ", error)

# 20
try:    
    write = int(input("Write 점수를 입력하세요: "))
    read = int(input("Read 점수를 입력하세요: "))
    if write >= 60 and read >= 60:
        print("합격")
    else:
        print("불합격")
except Exception as error:
    print("에러가 발생했습니다: ", error)

# 21
try:
    registered_id = ['hong', 'hong@mail.com']
    id = input("아이디를 입력하세요: ")
    if id in registered_id:
        print("로그인 성공")
    else: 
        print("로그인 실패")

except Exception as error:
    print("에러가 발생했습니다: ", error)

# 22
try:
    a = int(input("첫 번째 수 입력: "))
    b = int(input("두 번째 수 입력: "))
    c = int(input("세 번째 수 입력: "))

    big = a
    if b > a:
        big = b
    if c > b:
        big = c
    print(f'가장 큰 수는 {big} 입니다.')
    
except Exception as error:
    print("에러가 발생했습니다: ", error)

# 23
try:
    age = int(input("나이를 입력하세요: "))
    if age < 0:
        print("0 이상의 나이를 입력하세요.")  
    elif age <= 7:
        fee = 0
    elif age <=13:
        fee = 5000
    elif age <=18:
        fee = 8000
    else:
        fee = 12000

    print(f"요금은 {fee}원 입니다.")
except Exception as error:
    print("에러가 발생했습니다: ", error)


# 24
try:
    order_amt = int(input("주문 금액을 입력하세요: "))
    fee = 0
    if order_amt < 0:
        print("0 이상의 주문 금액을 입력하세요.")
    elif order_amt <= 50000:
        fee = 3000    

    print(f"총 결제금액은 {fee + order_amt}원 입니다.")
except Exception as error:
    print("에러가 발생했습니다: ", error)


# 25
try:
    height = int(input("키를 입력하세요 (cm): "))
    weight = int(input("몸무게를 입력하세요 (kg): "))
    bmi = round(weight / ((height/100) ** 2), 1)

    category = ""
    if bmi < 18.5:
        category = "저체중"
    elif bmi < 25:
        category = "정상"
    else:
        category = "과체중"

    print(f"BMI {bmi}: {category}")
except Exception as error:
    print("에러가 발생했습니다: ", error)

# 26
try:
    num = int(input("몇 월을 알고싶으신가요?: "))
    season = ""
    if 3 <= num <= 5:
        season = "봄"
    elif 6 <= num <= 8:
        season = "여름"
    elif 9 <= num <= 11:
        season = "가을"
    elif 0 < num and num <= 12:
        season = "겨울"
        
    if not season:
        print("잘못 입력하셨습니다!")
    else:
        print(f"{season}입니다.")
except Exception as error:
    print("에러가 발생했습니다: ", error)

# 27
try:
    num = int(input("몇 월을 알고싶으신가요?: "))
    season = ""
    match num:
        case 3 | 4 | 5:
            season = "봄"
        case 6 | 7 | 8:
            season = "여름"
        case 9 | 10 | 11:
            season = "가을"
        case 1 | 2 | 12:
            season = "겨울"
        case _:
            print("잘못 입력하셨습니다!")

    if season:
        print(f"{season}입니다.")
except Exception as error:
    print("에러가 발생했습니다: ", error)

# 28
try:
    num = int(input("값을 입력하세요: "))
    if not (0 <= num <= 100):
        print("잘못된 값")
except Exception as error:
    print("에러가 발생했습니다: ", error)