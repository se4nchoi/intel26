
from neuromeka import IndyDCP3
import math
ROBOT_IP = "192.168.3.7"
RADIUS = 100.0       # 반지름 100 mm = 10 cm
NUM_POINTS = 120     # 원을 구성하는 점 개수
MOVE_VEL = 70       # 이동 속도 비율
MOVE_ACC = 20       # 이동 가속도 비율
indy = IndyDCP3(ROBOT_IP)
def move_done_check():
    indy.wait_for_motion_state("is_target_reached")
# 직선 이동 함수
def move_linear(target_position):
    print("이동 위치:", target_position)
    result = indy.movel( ttarget=target_position,
        vel_ratio=MOVE_VEL, acc_ratio=MOVE_ACC    )
    print("이동 명령 결과:", result)
    move_done_check()
# XY 평면에 원 그리기
def draw_circle_xy():
    # 현재 TCP 위치 읽기
    current_pose = indy.get_control_state()["p"]
    # 현재 위치를 원의 중심으로 설정
    center_x = current_pose[0]
    center_y = current_pose[1]
    center_z = current_pose[2]
    # 현재 TCP 자세 유지
    rx = current_pose[3]
    ry = current_pose[4]
    rz = current_pose[5]
    print("\n현재 TCP 위치:", current_pose)
    print("\n원의 중심 좌표")
    print("center_x =", center_x)
    print("center_y =", center_y)
    print("center_z =", center_z)
    print("\n원의 반지름 =", RADIUS, "mm")
    # 원의 시작점으로 이동
    # 시작점: 중심에서 X축으로 50 mm 떨어진 위치
    start_position = [center_x + RADIUS, center_y, center_z, rx, ry,rz ]
    print("\n원 시작점으로 이동")
    move_linear(start_position)
    # 원주를 따라 이동
    for point_number in range(1, NUM_POINTS + 1):
        # 각도를 라디안으로 계산
        angle = (2.0 * math.pi * point_number / NUM_POINTS  )
        # 원주 위의 X, Y 좌표 계산
        x = center_x + RADIUS * math.cos(angle)
        y = center_y + RADIUS * math.sin(angle)
        # Z 높이와 TCP 자세는 그대로 유지
        target_position = [ x, y, center_z, rx, ry,  rz ]
        print(  f"\n원 그리기 "
            f"{point_number}/{NUM_POINTS}"     )
        print(  f"각도 = "
            f"{math.degrees(angle):.1f}도"        )
        move_linear(target_position)
    print("\n반지름 10cm 원 그리기 완료")
def main():
    print("Indy7 원 그리기 프로그램 시작")
    draw_circle_xy()
if __name__ == "__main__":
    main()