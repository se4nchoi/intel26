"""
    문제
        2 ~ 9단 까지 구구단을 출력하는 프로그램을 작성하시오.
            - 앞의 숫자: 피승수(被乘數) 또는 곱해지는 수 (multiplicand, dan)
            - 뒤의 숫자: 승수(乘數) 또는 곱하는 수 (multiplier, num)

    요구사항
        1. 2중 for문을 이용하여 구구단 2~9단을 출력하는 프로그램을 작성하시오.
        

    출력 예시:
        2x1 = 2   3x1 = 3   4x1 = 4   5x1 = 5   
        2x2 = 4   3x2 = 6   4x2 = 8   5x2 = 10   
        2x3 = 6   3x3 = 9   4x3 = 12   5x3 = 15   
        2x4 = 8   3x4 = 12   4x4 = 16   5x4 = 20   
        2x5 = 10   3x5 = 15   4x5 = 20   5x5 = 25   
        2x6 = 12   3x6 = 18   4x6 = 24   5x6 = 30   
        2x7 = 14   3x7 = 21   4x7 = 28   5x7 = 35   
        2x8 = 16   3x8 = 24   4x8 = 32   5x8 = 40   
        2x9 = 18   3x9 = 27   4x9 = 36   5x9 = 45   


        6x1 = 6   7x1 = 7   8x1 = 8   9x1 = 9   
        6x2 = 12   7x2 = 14   8x2 = 16   9x2 = 18   
        6x3 = 18   7x3 = 21   8x3 = 24   9x3 = 27   
        6x4 = 24   7x4 = 28   8x4 = 32   9x4 = 36   
        6x5 = 30   7x5 = 35   8x5 = 40   9x5 = 45   
        6x6 = 36   7x6 = 42   8x6 = 48   9x6 = 54   
        6x7 = 42   7x7 = 49   8x7 = 56   9x7 = 63   
        6x8 = 48   7x8 = 56   8x8 = 64   9x8 = 72   
        6x9 = 54   7x9 = 63   8x9 = 72   9x9 = 81 
"""

def main():

    for i in range(1, 10):
        col = 0
        for dan in range(2,6):
            print(f'{dan} x {i} = {dan*i:<8}', end=" ")
            col += 1
            if col > 3:
                col = 0
                print()
    print()
    for i in range(1,10):
        col = 0
        for dan in range(6,10):
            print(f'{dan} x {i} = {dan*i:<8}', end=" ")
            col += 1
            if col > 3:
                col = 0
                print()
    
if __name__ == "__main__":
    main()