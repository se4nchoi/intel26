
from neuromeka import IndyDCP3
import time
ROBOT_IP = "192.168.3.2"
indy = IndyDCP3(ROBOT_IP)
def wait_move_done():
    indy.wait_for_motion_state("is_target_reached")
    # print("이동 완료 대기 중...")
    # while True:
    #         motion_data = indy.get_motion_data()
    #         movedone = motion_data['is_target_reached']
    #         print("movedone =", movedone)
    #         if movedone == True:
    #             break
    #         time.sleep(0.1)
    print("이동 완료!")
# Joint 절대 이동
def move_joint_absolute(jtarget):
    print("Absolute Joint Target =", jtarget)
    result = indy.movej(  jtarget=jtarget    )
    print("movej result =", result)
    wait_move_done()
# Joint 상대 이동
def move_joint_relative(joffset):
    # 현재 관절각 읽기
    current_q = indy.get_control_state()['q']
    print("Current Joint =", current_q)
    print("Relative Offset =", joffset)
    # 현재값 + 상대값
    target_q = [current_q[i] + joffset[i]    for i in range(6)    ]
    print("Calculated Target =", target_q)
    # 계산된 절대 Joint 위치로 이동
    result = indy.movej(   jtarget=target_q    )
    print("movej result =", result)
    wait_move_done()
# 실행
# 절대 Joint 이동
indy.move_home()
wait_move_done()
move_joint_absolute(  [0, 0, -80, 0, -90, 0] )
time.sleep(1)
# 현재 위치에서 J1을 +10도 상대 이동
move_joint_relative( [10, 0, 0, 0, 0, 0])
wait_move_done()
indy.move_home()
wait_move_done()