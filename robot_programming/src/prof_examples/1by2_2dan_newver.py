
from neuromeka import IndyDCP3
import time
ROBOT_IP = "192.168.3.2"
indy = IndyDCP3(ROBOT_IP)
PICK_BASE = [ 207.42805,    310.04932,    408.53357]
PLACE_BASE = [   154.8543564286797,    326.10252214202605,    410.56767700108]
# Pallet 설정
GRID_X = 1
GRID_Y = 2
NUM_LAYERS = 2
LAYER_HEIGHT = 30.0      # 30 mm
OFFSET_X = 40.0          # 40 mm
OFFSET_Y = 40.0          # 40 mm
RETRACT_Z = 50.0         # 접근 / 복귀 높이
ROTATION_PICK = [  -175.85,    5.51,    169.58]
ROTATION_PLACE = ROTATION_PICK.copy()
# ROTATION_PLACE = [ 1.96,   -177.90,  3.90 ]
MOVE_VEL = 70
MOVE_ACC = 30
VACUUM_DO = 2
# 응답 결과 확인
def check_result(result, command_name):
    if isinstance(result, dict):
        code = result.get("code")
        if code not in (0, "0", None):
            raise RuntimeError(    f"{command_name} Error : {result}"            )
def move_done_check():
    print("이동 완료 대기 중...")
    indy.wait_for_motion_state(   "is_target_reached"    )
    print("이동 완료!")
# MoveL 함수
def move_linear(position, rotation):
    target = [ position[0], position[1],   position[2],    rotation[0],   rotation[1],  rotation[2]    ]
    print("\n----------------------------------------")
    print("MoveL Target =", target)
    result = indy.movel(
        target,
        blending_type=0,
        base_type=0,
        blending_radius=0.0,
        vel_ratio=MOVE_VEL,
        acc_ratio=MOVE_ACC    )
    print(   "MoveL Result =",    result    )
    check_result(  result,    "MoveL"    )
    move_done_check()
def vacuum_on():
    result = indy.set_do([(VACUUM_DO, True)])
    print( "Vacuum ON Result =",     result    )
    check_result(   result,   "Vacuum ON"    )
    print(     "VACUUM ON"    )
    return result
def vacuum_off():
    result = indy.set_do([ (VACUUM_DO, False)])
    print("Vacuum OFF Result =",    result    )
    check_result(  result,   "Vacuum OFF"    )
    print(   "VACUUM OFF"   )
    return result
# Pallet 좌표 생성
def generate_grid(  base,  grid_x,  grid_y,   offset_x,   offset_y,   num_layers,   layer_height):
    coords = []
    print("팔레트 좌표 생성")
    for layer in range(num_layers):
        z = (  base[2] + layer * layer_height  )
        for y_index in range(grid_y):
            for x_index in range(grid_x):
                x = (  base[0] + x_index * offset_x)
                y = (  base[1] + y_index * offset_y    )
                position = [ x,  y,  z ]
                coords.append(   position       )
                print(
                    f"Layer {layer + 1} "
                    f"X={x_index + 1} "
                    f"Y={y_index + 1} "
                    f": {position}"      )
    return coords
# 현재 Robot 위치 출력
def print_current_position():
    try:
        state = indy.get_control_state()
        print( "현재 Joint 위치 =",   state.get("q")   )
        print(  "현재 Task 위치  =",  state.get("p") )
    except Exception as e:
        print(  "현재 위치 읽기 오류 :",   e        )
def move_home():
    print("HOME 이동")
    result = indy.move_home()
    print( "Move Home Result =",  result    )#dictionary타입
    check_result(   result,  "Move Home"   )
    move_done_check()
    print(        "HOME 위치 도착 완료"    )
def execute_pick_and_place():
    print("Pick & Place 초기화")
    vacuum_off()
    time.sleep(0.5)
    move_home()
    time.sleep(1.0)
    place_positions = generate_grid( PLACE_BASE, GRID_X, GRID_Y, OFFSET_X, OFFSET_Y, NUM_LAYERS, LAYER_HEIGHT    )
    print("\nPick 고정 위치 =",  PICK_BASE    )
    print( "팔레타이징 위치 수 =",  len(place_positions)    )
    # Pick & Place 반복
    for step, place in enumerate(  place_positions,  start=1):
        print(    f"STEP {step} / {len(place_positions)}"      )
        print(    "Pick  =",    PICK_BASE        )
        print(    "Place =",      place        )
        # Pick Approach 좌표
        pick_approach = [ PICK_BASE[0],    PICK_BASE[1],     PICK_BASE[2] + RETRACT_Z        ]
        # 1. PICK APPROACH
        print(   "\n[1] Pick Approach"      )
        move_linear(  pick_approach,     ROTATION_PICK     )
        # 2. PICK DOWN
        print( "\n[2] Pick Down"     )
        move_linear(  PICK_BASE,     ROTATION_PICK        )
        vacuum_on()
        # 4. PICK RETRACT
        move_linear( pick_approach,  ROTATION_PICK      )
        # Place Approach 좌표
        place_approach = [ place[0], place[1],   place[2] + RETRACT_Z     ]
        # 5. PLACE APPROACH
        move_linear(  place_approach,   ROTATION_PLACE       )
        # 6. PLACE DOWN
        move_linear(     place,      ROTATION_PLACE        )
        vacuum_off()
        time.sleep(1.0)
        # 8. PLACE RETRACT
        move_linear(  place_approach,     ROTATION_PLACE        )
        print(            f"\nSTEP {step} 완료"        )
    # 전체 작업 완료
    print("모든 Pick & Place 작업 완료")
    vacuum_off()
    move_home()
    # 최종 위치 확인
    print(  "\n최종 Robot 위치"    )
    print_current_position()
# 오류 발생 시 안전 처리
def safe_stop():
    print(  "\n===== 안전 정지 처리 ====="    )
    try:
        vacuum_off()
    except Exception as e: #e는 발생한 오류 객체
        print( "Vacuum OFF 실패 :",    e        )
    try:
        indy.stop_motion()
        print(       "Motion Stop 요청"        )
    except Exception as e:
        print(   "Motion Stop 실패 :",     e        )
# Main
if __name__ == "__main__":
    try:
        print_current_position()
        execute_pick_and_place()

    except KeyboardInterrupt:
        print(   "\n사용자가 프로그램을 중지했습니다."        )
        safe_stop()
    except Exception as e:
        print(  "Robot Error :",      e        )
        safe_stop()
    finally:
        print(       "\n프로그램 종료"        )