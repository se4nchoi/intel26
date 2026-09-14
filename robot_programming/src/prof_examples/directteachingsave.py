
from neuromeka import IndyDCP3
import time
ROBOT_IP = "192.168.3.2"
indy = IndyDCP3(ROBOT_IP)
def print_current_position():
    try:
        state = indy.get_control_state()
        print("\n현재 Joint 위치")
        print(state.get("q"))
        print("\n현재 Task 위치")
        print(state.get("p"))
    except Exception as e:
        print("현재 위치 읽기 오류 :", e)
# Direct Teaching 시작
def start_direct_teaching():
    print("Direct Teaching 시작")
    try:
        result = indy.set_direct_teaching(True)
        print("Direct Teaching ON Result =", result)
        return result
    except Exception as e:
        print("Direct Teaching 시작 실패 :", e)
        raise
# Direct Teaching 종료
def stop_direct_teaching():
    print("Direct Teaching 종료")
    try:
        result = indy.set_direct_teaching(False)
        print("Direct Teaching OFF Result =", result)
        return result
    except Exception as e:
        print("Direct Teaching 종료 실패 :", e)
        raise
# Teaching 위치 저장
def save_teaching_position():
    try:
        state = indy.get_control_state()
        joint_position = state.get("q")
        task_position = state.get("p")
        print("Teaching Position 저장")
        print("Joint =", joint_position)
        print("Task  =", task_position)
        return joint_position, task_position
    except Exception as e:
        print("Teaching 위치 저장 실패 :", e)
        raise
# Direct Teaching 전체 동작
def direct_teaching_mode():
    print("Indy7 Direct Teaching Mode")
    # 1. Teaching 시작 전 위치 확인
    print("\n[1] Teaching 시작 전 현재 위치")
    print_current_position()
    # 2. Direct Teaching 시작
    print("\n[2] Direct Teaching 시작")
    start_direct_teaching()
    print("로봇을 손으로 원하는 위치까지 이동하십시오.")
    input()
    # 4. Direct Teaching 종료
    print("\n[3] Direct Teaching 종료")
    stop_direct_teaching()
    time.sleep(0.5)
    # 5. Teaching 위치 저장
    print("\n[4] Teaching 위치 저장")
    joint_pos, task_pos = save_teaching_position()
    # 6. 최종 저장 결과 출력
    print("최종 Teaching 위치")
    print("Joint Position")
    print(joint_pos)
    print("\nTask Position")
    print(task_pos)
    return joint_pos, task_pos
# Main
if __name__ == "__main__":
    try:
        print("Indy7 Direct Teaching Program")
        joint_pos, task_pos = direct_teaching_mode()
        print("Teaching 완료")
        print("\n저장된 Joint 위치")
        print(joint_pos)
        print("\n저장된 Task 위치")
        print(task_pos)
    except KeyboardInterrupt:
        print("\n사용자가 프로그램을 중지했습니다.")
        # Direct Teaching 중 프로그램이 중단되었을 경우
        # Teaching Mode를 OFF 시도
        try:
            indy.set_direct_teaching(False)
            print("Direct Teaching OFF 처리 완료")
        except Exception as e:
            print("Direct Teaching OFF 처리 실패 :", e)
    except Exception as e:
        print("\nRobot Error :", e)
        try:
            indy.set_direct_teaching(False)
        except:
            pass
    finally:
        print("\n프로그램 종료")