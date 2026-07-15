"""
practicing function calls (...boring...)

temperature converter,
2 level of input:
    - ask for mode (f to c, c to f)
    - actual temp to convert
"""


def ftoc(f):
    c = (f - 32) * 5 / 9
    return c

def ctof(c):
    f = c * 9 / 5 + 32
    return f

def get_mode():
    print("1. 섭씨(C) -> 화씨(F)")
    print("2. 화씨(F) -> 섭씨(C)")
    print("3. 종료")
    while True:    
        mode = input("모드를 선택하세요: ")
        if mode in ["1", "2", "3"]:
            break
        else:
            print("잘못된 입력입니다. 다시 시도하세요.")
    
    return mode

def get_temp():
    while True:
        try:
            temp = float(input("온도를 입력하세요: "))
            break
        except ValueError:
            print("잘못된 입력입니다. 숫자를 입력하세요.")
    return temp


def Temperature_Converter():
    while True:
        mode = get_mode()
        if mode == "1":
            print("섭씨(C)를 화씨(F)로 변환합니다.")
            temp = get_temp()
            converted = ctof(temp)
            print(f"{temp:.2f}C는 {converted:.2f} F입니다.")
        elif mode == "2":
            print("화씨(F)를 섭씨(C)로 변환합니다.")
            temp = get_temp()
            converted = ftoc(temp)
            print(f"{temp:.2f} F는 {converted:.2f} C입니다.")
        elif mode == "3":
            print("프로그램을 종료합니다.")
            break
        else:
            print("잘못된 입력입니다. 다시 시도하세요.")


"""
fibonacci -- the typical example of recursion

same result as a clever for loop, but catastrophic run times

-> but what happens in recursion ? you keep piling function calls in the stack
-> eventually blows up if requested past capacity

recursions ARE very useful in cases though.
-> graph traversals
-> where else ?
"""
def fib(n):
    pass

if __name__ == "__main__":
    pass
    #Temperature_Converter()