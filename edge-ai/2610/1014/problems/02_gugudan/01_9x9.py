"""
    문제
        구구단의 2단을 출력하는 프로그램을 작성하시오.
            - 앞의 숫자: 피승수(被乘數) 또는 곱해지는 수 (multiplicand, dan)
            - 뒤의 숫자: 승수(乘數) 또는 곱하는 수 (multiplier, num)
            - dan * num = dan * num

    요구사항
        for문을 이용하여 프로그램을 작성하시오

    출력 예시:
        2 x 1 = 2
        2 x 2 = 4
        2 x 3 = 6
        2 x 4 = 8
        2 x 5 = 10
        2 x 6 = 12
        2 x 7 = 14
        2 x 8 = 16
        2 x 9 = 18
"""

def main():
    # dan = 2
    for num in range(1, 10):
        print(f'2 x {num} = {2*num}')

    return 0

if __name__ == "__main__":
    main()