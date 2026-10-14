"""
    문제
        산행지 관리 프로그램을 작성하시오.
            산행지 등록 / 검색 / 출력 / 삭제 기능을 제공하며, 사용자로부터 메뉴 선택을 받아 해당 기능을 수행하도록 구현할 것
        사용자가 "q" 버튼을 입력하면 프로그램을 종료하도록 구현할 것

    요구사항
        1. 입력 처리: 사용자로부터 메뉴를 선택받아 해당 기능을 수행하도록 구현할 것
        2. 함수 처리: 등록 / 검색 / 출력 / 삭제를 수행하는 각 함수를 정의해서 구현할 것
        3. 등록: sqlite를 사용해서 데이터를 데이터 베이스에 저장 합니다. (sql.py 사용)
        4. 예외 처리:
            - 등록: 등록되어 있는 산행지 이름이 없는 경우, 오류 메시지를 출력
            - 검색: 검색한 산행지 이름이 없는 경우, 오류 메시지를 출력
            - 삭제: 삭제할 산행지 이름이 없는 경우, 오류 메시지를 출력
        5. 프로그램 종료 조건: 사용자가 "q" 혹은 "Q" 버튼을 입력하면 프로그램을 종료하도록 구현할 것

    출력 예시:
        1. 산행지 등록
        2. 산행지 검색
        3. 산행지 전체 출력
        4. 산행지 삭제
        q. 프로그램 종료
        원하는 번호를 선택하세요:

        1번 선택
            등록할 산행지 이름을 입력하세요: 설악산
            지역을 입력하세요: 강원도
            높이를 입력하세요: 1708m

            Success: 설악산이 등록되었습니다.
            Failure: 설악산이 이미 등록되어 있습니다.

        2번 선택
            검색할 산행지 이름을 입력하세요: 지리산

            Success: 지리산이 등록되어 있습니다.
            Failure: 지리산이 등록되어 있지 않습니다.

        3번 선택
            등록된 모든 산행지 이름을 출력합니다.
            등록된 산행지가 없는 경우 "등록된 산행지가 없습니다." 출력

        4번 선택
            삭제할 산행지 이름을 입력하세요: 한라산
            Success: 한라산이 삭제되었습니다.
            Failure: 한라산이 등록되어 있지 않습니다.

        q 선택
            프로그램을 종료합니다.
"""

import database.sql as db

def register_mtn():
    try:
        mtn_name = input("등록할 산행지 이름을 입력하세요: ")
        mtn_location = input("지역을 입력하세요: ")
        mtn_height = input("높이를 입력하세요 (m): ")
        print("=====================================")
        print()
        success = db.add_mountain_to_db(name=mtn_name, 
                                    height=mtn_height, location=mtn_location)
        if not success:
            # unique 위반만 false return ?
            print(f'Failure: {mtn_name}이 이미 등록되어 있습니다.')
        else:
            print(f'Success: {mtn_name}이 등록되었습니다.')
        return
    except Exception as error:
        print("에러가 발생하였습니다: ", error)
    
def search_mtn():
    try:
        mtn_name = input("검색할 산행지 이름을 입력하세요: ")
        print("=====================================")
        print()
        result = db.get_mountain_by_name(name=mtn_name)
        if result is not None:
            print(f"Success: {mtn_name}이 등록되어 있습니다.")
            print(f'이름: {result["name"]}')
            print(f'지역: {result["location"]}')
            print(f'높이: {result["height"]}')
        else:
            print(f"Failure: {mtn_name}이 등록되어 있지 않습니다.")

    except Exception as error:
        print("에러가 발생하였습니다: ", error)

def print_all_mtn():
    print("=====================================")
    print()
    mtn_list = db.get_all_mountains()
    if len(mtn_list) == 0:
        print("등록된 산행지가 없습니다.")
    else:
        for mtn in mtn_list:
            print(mtn['name'])
    return

def delete_mtn():
    mtn_name = input("삭제할 산행지 이름을 입력하세요: ")
    print("=====================================")
    print()

    result = db.delete_mountain_from_db(name=mtn_name)
    if result > 0:
        print(f"Success: {mtn_name}이 삭제되었습니다.")
    else:
        print(f"Failure: {mtn_name}이 등록되어 있지 않습니다.")

def main():
    db.init_db()
    msg_to_user = """
    1. 산행지 등록
    2. 산행지 검색
    3. 산행지 전체 출력
    4. 산행지 삭제
    q. 프로그램 종료
    원하는 번호를 선택하세요: """
    try:
        while (True):
            print("=====================================")
            user_cmd = input(msg_to_user)

            match user_cmd:
                case "1":
                    register_mtn()
                case "2":
                    search_mtn()
                case "3":
                    print_all_mtn()
                case "4":
                    delete_mtn()
                case "q" | "Q":
                    print("프로그램을 종료합니다.")
                    break
                case _:
                    print("메뉴를 잘못 선택하셨습니다. 다시 입력해 주세요")

    except Exception as error:
        print("에러가 발생하여 프로그램을 종료합니다: ", error)

    return 0

if __name__ == "__main__":
    main()