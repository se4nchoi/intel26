from neuromeka import IndyDCP3, TaskBaseType
import time
ROBOT_IP = "192.168.3.2"
indy = IndyDCP3(ROBOT_IP)
def wait_move_done():
    print("이동 완료 대기 중...")
    indy.wait_for_motion_state( "is_target_reached"    )
    print("이동 완료!")
# 툴 좌표계 상대 이동
def move_tool(tool_offset):
    print("\n툴 좌표계 상대 이동량 =", tool_offset)
    result = indy.movel( ttarget=tool_offset,
        # 툴 좌표계 기준 상대 이동
        base_type=TaskBaseType.TCP,
        blending_type=0,
        blending_radius=0.0,
        # 처음에는 낮은 속도로 시험
        vel_ratio=50,
        acc_ratio=10    )
    print("MoveL 결과 =", result)
    # 명령 결과 확인
    if not isinstance(result, dict):
        raise RuntimeError(
            f"MoveL 응답 오류: {result}"        )
    if str(result.get("code")) != "0":
        raise RuntimeError(
            f"MoveL 명령 실패: {result}"        )
    wait_move_done()
# 실행
try:
    # 현재 위치 출력
    current_p = indy.get_control_state()["p"]
    print("이동 전 TCP 위치 =", current_p)
    # 현재 TCP에서 Tool Z축 방향으로 +10mm 이동
    move_tool( [  0.0,  0.0,  30.0,  0.0, 0.0,  0.0  ] )
    # 이동 후 위치 출력
    current_p = indy.get_control_state()["p"]
    print("이동 후 TCP 위치 =", current_p)
except KeyboardInterrupt:
    print("\n사용자가 프로그램을 중지했습니다.")
    try:
        indy.stop_motion()
    except Exception as e:
        print("모션 정지 실패:", e)
except Exception as e:
    print("\nRobot Error:", e)
    try:
        indy.stop_motion()
    except Exception as stop_error:
        print("모션 정지 실패:", stop_error)
finally:
    print("\n프로그램 종료")