"""
    문제
        2개의 리스트를 병합, sort, 중복 제거하는 프로그램을 작성 하시오

    요구사항
        1. set을 사용해서 리스트에서 중복 제거
        2. sort() 메서드(또는 sorted())를 사용해서 리스트 값 정렬
        3. min(), max() 함수를 사용해서 리스트에서 최솟값, 최댓값 추출
        4. 각 메뉴는 함수에서 구현해서 결과값을 반환 후 출력

    출력 예시:
        1. 두 리스트를 합친 뒤 오름차순으로 정렬하여 반환합니다.
        2. 두 리스트를 합친 뒤 내림차순으로 정렬하여 반환합니다.
        3. 두 리스트를 합친 뒤 min, max값 출력
        4. 두 리스트를 합친 뒤 중복 제거
        q. 프로그램 종료
        원하는 번호를 선택하세요:

        1번 선택
            오름차순 리스트: [1, 1, 2, 2, 3, 3, 4, 4, 6, 6, 8, 8, 9, 9]

        2번 선택
            내림차순 리스트: [9, 9, 8, 8, 6, 6, 4, 4, 3, 3, 2, 2, 1, 1]

        3번 선택
            최솟값: 1,    최댓값: 9

        4번 선택
            중복 제거 리스트: [1, 2, 3, 4, 6, 8, 9]

        q 선택
            프로그램을 종료합니다.
"""

# 요구사항
#     1. set을 사용해서 리스트에서 중복 제거
#     2. sort() 메서드(또는 sorted())를 사용해서 리스트 값 정렬
#     3. min(), max() 함수를 사용해서 리스트에서 최솟값, 최댓값 추출
#     4. 각 메뉴는 함수에서 구현해서 결과값을 반환 후 출력


def sort_ascending(list1, list2):
    return sorted(list1 + list2)

def sort_descending(list1, list2):
    return sorted(list1 + list2, reverse=True)

def get_min_max(list1, list2):
    return min(list1 + list2), max(list1+list2)

def remove_duplicates(list1, list2):
    return list(set(list1 + list2))


def main():
    USER_MESSAGE = """
메뉴를 선택하세요.
1. 두 리스트를 합친 뒤 오름차순으로 정렬하여 반환합니다.
2. 두 리스트를 합친 뒤 내림차순으로 정렬하여 반환합니다.
3. 두 리스트를 합친 뒤 min, max값 출력
4. 두 리스트를 합친 뒤 중복 제거
q. 프로그램 종료
"""
    num_list_1 = [9, 2, 6, 8, 2, 6, 1]
    num_list_2 = [1, 4, 9, 3, 8, 4, 3]

    while True:
        select_menu = input(USER_MESSAGE)

        match select_menu:
            case "1":
                value = sort_ascending(num_list_1, num_list_2)
                print(f"오름차순 리스트: {value}")
            case "2":
                value = sort_descending(num_list_1, num_list_2)
                print(f"내림차순 리스트: {value}")
            case "3":
                min_value, max_value = get_min_max(num_list_1, num_list_2)
                print(f"최솟값: {min_value},    최댓값: {max_value}")
            case "4":
                value = remove_duplicates(num_list_1, num_list_2)
                print(f"중복 제거 리스트: {value}")
            case "q":
                exit(0)


if __name__ == "__main__":
    main()