
from time import sleep
from neuromeka import IndyDCP3
ROBOT_IP = "192.168.3.2"
GRID_SIZE = 5
MAX_CELL = 25
CELL_PITCH = 40.0
APPROACH_HEIGHT = 50.0
VACUUM_DO = 2
MOVE_VEL = 30
MOVE_ACC = 10
POS_FIRST = [15.748302, 321.56088, 404.73798, 5.210189, 179.86049, 33.689323]
# 작업 종료 위치
CENTER = [108.16866, 389.27124, 471.23288, 1.4016397, 178.99274, 13.599214]
indy = None
# 로봇 연결
def connect_robot():
    global indy
    print(f"Indy7 연결 중: {ROBOT_IP}")
    indy = IndyDCP3(ROBOT_IP)
    print("Indy7 연결 완료")
def check_result(result, name):
    print(f"{name} result =", result)
    if not isinstance(result, dict):
        raise RuntimeError(  f"{name} 응답 형식 오류: {result}"        )
    # DCP3 버전에 따라 code가 숫자 0 또는 문자열 "0"일 수 있음
    if str(result.get("code")) != "0":
        raise RuntimeError(    f"{name} 명령 실패: {result}"        )
def motion_done_check():
    indy.wait_for_motion_state( "is_target_reached"   )
def move_linear(target, name="이동"):
    print()
    print(name)
    print("Target =", target)
    result = indy.movel(   ttarget=target,   blending_type=0,    base_type=0,
        blending_radius=0.0,  vel_ratio=MOVE_VEL,     acc_ratio=MOVE_ACC )
    check_result(  result,   name    )
    motion_done_check()
def vacuum_on():
    result = indy.set_do([  (VACUUM_DO, True)  ])
    check_result(  result,   "Vacuum ON"    )
    sleep(2.0)
def vacuum_off():
    result = indy.set_do([ (VACUUM_DO, False)  ])
    check_result(result,   "Vacuum OFF"    )
    sleep(1.0)
# 칸 번호를 좌표로 변환
def cell_position(cell_number):
    index = cell_number - 1
    row = index // GRID_SIZE
    print(row)
    column = index % GRID_SIZE
    print(column)
    position = POS_FIRST.copy()
    # 행이 증가하면 X 증가
    position[0] += row * CELL_PITCH
    # 열이 증가하면 Y 증가
    position[1] += column * CELL_PITCH
    print(position)
    return position
# 접근 위치 생성
def create_approach(target):
    approach = target.copy()
    # 목표 위치보다 Z축으로 50 mm 높은 위치
    approach[2] += APPROACH_HEIGHT
    return approach
# Pick 동작
def pick(position):
    approach = create_approach(position)
    # 목표점 위쪽으로 이동
    move_linear( approach,   "Pick approach"    )
    # Pick 위치로 하강
    move_linear(  position,   "Pick target"    )
    vacuum_on()
    # 목표점 위쪽으로 상승
    move_linear( approach,   "Pick retract"    )
# Place 동작
def place(position):
    approach = create_approach(position)
    # 목표점 위쪽으로 이동
    move_linear( approach,   "Place approach"  )
    # Place 위치로 하강
    move_linear( position,      "Place target"    )
    vacuum_off()
    # 목표점 위쪽으로 상승
    move_linear( approach,     "Place retract"    )
# 작업 위치 목록 생성
def create_work_positions( start_cell,  line_count,    total_count):
    # 시작 칸 확인
    if not 1 <= start_cell <= MAX_CELL:
        raise ValueError(  "시작 칸 번호는 1~25 범위여야 합니다."        )
    # 한 줄 개수 확인
    if not 1 <= line_count <= GRID_SIZE:
        raise ValueError( "한 줄 개수는 1~5 범위여야 합니다."      )
    # 물체를 이동하려면 최소한 두 위치가 필요함
    if total_count < 2:
        raise ValueError( "총 개수는 2 이상이어야 합니다."       )
    start_index = start_cell - 1
    start_row = start_index // GRID_SIZE
    start_column = start_index % GRID_SIZE
    positions = []
    for index in range(total_count):
        # line_count만큼 진행하면 다음 행으로 이동
        row_offset = index // line_count
        column_offset = index % line_count
        row = start_row + row_offset
        column = start_column + column_offset
        # 5×5 틀의 범위는 row 0~4, column 0~4
        if row >= GRID_SIZE or column >= GRID_SIZE:
            raise ValueError(
                f"{index + 1}번째 작업 위치가 "
                f"5×5 틀을 벗어납니다. "
                f"row={row}, column={column}"            )
        cell_number = ( row * GRID_SIZE + column  + 1        )
        position = cell_position(   cell_number  )
        print(position)
        positions.append({ "cell": cell_number, "position": position  })
    return positions
# 작업 위치 출력
def print_work_positions(positions):
    print()
    print("작업 위치")
    print("=" * 95)
    print(
        f"{'순서':^8}"
        f"{'칸':^8}"
        f"{'X(mm)':^15}"
        f"{'Y(mm)':^15}"
        f"{'Z(mm)':^15}"    )
    print("-" * 95)
    for index, item in enumerate(positions):
        position = item["position"]
        print(
            f"{index + 1:^8}"
            f"{item['cell']:^8}"
            f"{position[0]:^15.4f}"
            f"{position[1]:^15.4f}"
            f"{position[2]:^15.4f}"        )
    print("=" * 95)
    print( "위치 개수 =",   len(positions)    )
    print("실제 이송 횟수 =",   len(positions) - 1    )
# 틀 내부 순차 이동
def run_grid_mode():
    line_count = int( input("한 줄에 놓을 개수: ")    )
    total_count = int(input("사용할 총 위치 개수: ")    )
    start_cell = int( input("시작 칸 번호(1~25): ")    )
    # 로봇에 연결하기 전에 모든 작업 좌표를 생성하고 검사
    positions = create_work_positions( start_cell,  line_count,   total_count  )
    print_work_positions( positions    )
    connect_robot()
    # 프로그램 시작 전 진공 해제
    vacuum_off()
    # 현재 칸에서 Pick한 후 다음 칸에 Place
    for index in range( len(positions) - 1):
        pick_data = positions[index]
        place_data = positions[index + 1]
        print()
        print("=" * 60)
        print(
            f"STEP {index + 1}: "
            f"{pick_data['cell']}번 칸"
            f" → "
            f"{place_data['cell']}번 칸"        )
        print("=" * 60)
        pick( pick_data["position"]        )
        place( place_data["position"]        )
# Center 위치로 이동
def move_to_center():
    # Center보다 Z축으로 50 mm 높은 안전 위치
    center_approach = create_approach( CENTER    )
    # 먼저 높은 위치에서 Center 위쪽으로 이동
    move_linear( center_approach, "Center approach"    )
    # Center 위치로 하강
    move_linear( CENTER,  "Center 이동"    )
# 메인 함수
def main():
    print("Indy7 틀 내부 순차 이동 프로그램")
    run_grid_mode()
    move_to_center()
    print()
    print("프로그램 완료")
# 프로그램 시작
if __name__ == "__main__":
    main()