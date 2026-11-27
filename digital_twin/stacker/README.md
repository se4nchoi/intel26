# Factory I/O 스태커 크레인 — S 적재

기존 예제를 변경하지 않고 빈 장면에서 새 부품으로 구성했다. `stacker_crane_s_from_scratch.factoryio`가 실제 설비 파일이며 `stacker_s.ipynb`가 실행 노트북이다. 제어 구현은 같은 폴더의 `controller.py`에 있다.

> 현재 상태: 1번 칸 적재·복귀 확인 / Start 마우스 입력 및 S 전체 30개 적재 미검증. 상세 인계는 `VALIDATION.md` 참고.

## 실행

1. Factory I/O에서 `stacker_crane_s_from_scratch.factoryio`를 연다. My Scenes에도 같은 이름으로 설치되어 있다.
2. Driver를 **Modbus TCP/IP Server**로 선택한다. 서버 IP는 현재 PC의 `192.168.0.117`, Port `502`, Slave ID `1`이다. 네트워크가 바뀌면 드라이버 IP와 노트북 HOST를 함께 바꾼다. 현재 서버는 `127.0.0.1`에 바인딩되어 있지 않다.
3. Driver를 Start한다. 센서는 Discrete Inputs, 액추에이터는 Coils 및 Holding Registers를 사용한다. 주소 Offset은 모두 0, Scale은 1이다. 장면에 매핑을 저장했다.
4. 이전 실행이 있었다면 Factory I/O의 Edit → Run 전환으로 빈 초기 장면으로 되돌린다. 빈 랙, 빈 입고대, 정위치, 회수된 포크를 확인한다. 실행 중 다른 Python 제어기를 동시에 연결하지 않는다.
5. `stacker_s.ipynb`를 열고 Python 커널을 이 폴더의 `.venv/Scripts/python.exe`로 선택한다. 다른 환경이라면 설치 셀을 실행한다. PyModbus는 **3.11.1**로 고정했다. 3.x 전체가 동일한 인자명을 쓰는 것은 아니므로 낮은 3.x로 임의 변경하지 않는다.
6. 필요하면 Page Up / Page Down으로 Overview와 Controls 카메라를 전환한다. 노트북의 초기 장면 확인 값을 `True`로 바꾸고 실행 셀까지 실행한다. 출력 `IDLE`이 나오면 장면 앞쪽 조작반의 **Start Button 0**을 누른다. 버튼을 누른 채 제어기를 실행한 경우에는 한 번 놓았다가 다시 누른다.
7. S 좌표 30개를 차례로 적재한 뒤 정위치 99로 복귀하고 `DONE`으로 종료한다. 완료 후 다시 시작 버튼을 눌러도 중복 적재하지 않는다. 새 실행은 빈 장면으로 초기화한 뒤 새 제어기를 만들어 수행한다.

터미널 실행도 가능하다.

```powershell
cd D:\se4nchoi\factoryio-stacker-s
& .\.venv\Scripts\python.exe controller.py --empty-scene-confirmed
```

위 명령도 물리 Start 입력을 기다린다. `--start-now`는 단일 설비 시운전용 시작 우회 옵션이며 일반 운전에서는 사용하지 않는다.

## 번호와 S 형상

화면에서 왼쪽부터 x=1..9, 아래부터 z=1..6으로 정의한다.

```python
position = (z - 1) * 9 + (10 - x)
```

| 높이 | 왼쪽 → 오른쪽 Target Position |
|---|---|
| z=6 | 54 53 52 51 50 49 48 47 46 |
| z=5 | 45 44 43 42 41 40 39 38 37 |
| z=4 | 36 35 34 33 32 31 30 29 28 |
| z=3 | 27 26 25 24 23 22 21 20 19 |
| z=2 | 18 17 16 15 14 13 12 11 10 |
| z=1 | 9 8 7 6 5 4 3 2 1 |

6행으로 대문자 S를 표현하기 위해 가운데 가로획은 위에서 세 번째 줄에 두었다. `#`가 적재 위치다.

```text
#########
#........
#########
........#
........#
#########
```

적재 순서는 끊김 없이 S 획을 따라간다.

```text
46,47,48,49,50,51,52,53,54,45,
36,35,34,33,32,31,30,29,28,19,10,
1,2,3,4,5,6,7,8,9
```

## I/O 주소

설명서 주소는 1부터, PyModbus의 프로토콜 주소는 0부터 시작한다. `10001`, `40001` 같은 표기 자체를 API address에 넣지 않는다. 모든 호출에 `device_id=1`을 사용한다.

| 구분 | 표기 주소 | API address | 이름 |
|---|---|---:|---|
| DI | 10001 | 0 | Sensor |
| DI | 10002 | 1 | MovingX |
| DI | 10003 | 2 | MovingZ |
| DI | 10004 | 3 | Left Limit |
| DI | 10005 | 4 | Right Limit |
| DI | 10006 | 5 | Middle Limit |
| DI | 10007 | 6 | Start Button 0 |
| DI | 10008 | 7 | Reset Button 0 |
| Coil | 00001 | 0 | Lift |
| Coil | 00002 | 1 | Fork Left |
| Coil | 00003 | 2 | Fork Right |
| Coil | 00004 | 3 | Load in |
| Coil | 00005 | 4 | Load out |
| Coil | 00009 | 8 | Conveyor0 |
| Coil | 00010 | 9 | Conveyor1 |
| Coil | 00011 | 10 | Emitter 0 |
| Coil | 00012 | 11 | Remover 0 |
| HR | 40001 | 0 | Target Position |

Coil 5..7은 비워 두었다. 버튼 램프는 제어 매핑에 포함하지 않았다. Target Position은 문자열이 아닌 정수로 쓰며, 적재 위치 1..54, 정위치 99를 사용한다. 정위치 도착 전용 입력은 없으므로 `99 쓰기 → 실제 이동 시작 확인 → MovingX/MovingZ 모두 OFF 안정 확인`을 복귀 완료 조건으로 사용한다. 레지스터 읽기값 자체는 도착 확인이 아니다.

## 한 사이클의 상태와 전이

| 상태 | 출력 및 대기 조건 |
|---|---|
| IDLE | 모든 사용 Coil OFF, 정위치 99, Start의 새 누름 대기 |
| FEED | Conveyor0/1, Remover, Load in ON. Emitter는 **사이클마다** 한 번 0.2초 펄스. Sensor ON을 읽으면 즉시 Load in OFF |
| PICK_LEFT | X/Z 정지 확인 → Fork Left ON → Left Limit → Lift ON → 실제 MovingZ 시작 및 정지 확인 → Fork Left OFF → Middle Limit |
| TRAVEL | 포크 중앙 및 X/Z 정지 확인 → 정수 Target 쓰기 → 이동 시작 확인 → X/Z 모두 OFF 안정 확인 |
| PLACE_RIGHT | Fork Right ON → Right Limit → Lift OFF → 실제 MovingZ 시작 및 정지 확인 → Fork Right OFF → Middle Limit |
| RETURN_HOME | 99 쓰기 → 이동 시작 확인 → X/Z 모두 OFF 안정 확인 |
| CYCLE_DONE | 복귀가 끝난 뒤에만 완료 좌표에 추가하고 다음 사이클 진행 |
| DONE | 마지막 복귀 후 모든 사용 Coil OFF, 반복 시작 금지 |
| FAULT | 공급·이송 출력 OFF, 상태와 원인 기록, 자동 재시작 금지 |

Conveyor0/1과 Remover는 사이클 사이에도 유지된다. Emitter의 “한 번”은 전체 운전에서 한 개라는 뜻이 아니라 각 적재 사이클마다 한 팔레트를 생성한다는 뜻으로 구현했다. Load out은 이번 적재 작업에서 계속 OFF다. Emitter는 Square Pallet + BoxL 한 종류를 생성하고 임의 위치/방향 옵션은 껐다.

폴링 50ms, 입력 안정 시간 150ms, 공급 30초, 포크 20초, 리프트 15초, 이동 시작 5초, 이동 완료 90초를 기본 제한으로 사용한다. 리프트 대기를 단순 sleep으로 대체하지 않는다. 모든 대기 중 Reset 입력과 모순된 Limit 조합을 확인한다. 통신 오류와 커널 중단도 FAULT 처리한다. 로그는 `logs/*.jsonl`에 상태 전이마다 즉시 저장한다.

## Reset 및 중단의 실제 의미

Reset Button 0은 **작업 중단 및 재시작 차단**이다. 하중과 포크 위치를 임의로 바꾸지 않도록 크레인의 Lift/포크 출력은 그대로 보존하고 공급·컨베이어를 끈다. 자동 원점 복귀나 강제 Lift OFF를 하지 않는다.

현재 주어진 I/O에는 크레인 비상 정지 액추에이터가 없다. Numerical 모드에서 Target=0은 이전 이동 명령을 취소하지 않으므로 정지 명령으로 사용하지 않는다. 진행 중인 크레인 움직임까지 즉시 멈추려면 Factory I/O의 **Pause**를 사용한다. 통신 단절·커널 강제 종료 때도 시뮬레이터가 마지막 출력을 유지할 수 있으므로 Pause 후 Edit 모드로 초기화한다. Reset 후에는 실행 셀만 재실행하지 말고 빈 장면부터 다시 시작한다.

입고 센서와 이동 신호만으로는 팔레트가 실제로 포크 위에 있는지, 랙에 안착했는지 확정할 수 없다. 제어 로그의 완료 수는 확인된 시퀀스 수이며, 최종 안착은 Factory I/O 화면에서도 확인한다.

## 검증

```powershell
& .\.venv\Scripts\python.exe test_controller.py
```

독립적인 지연 응답 모형으로 전체 30개 좌표, 중복 없는 생성 펄스, 시작 버튼 재누름, 이동 시작 신호 누락, Reset 중단, 포크 이동 인터록을 확인한다. 실설비 파일 검증 결과는 `VALIDATION.md`에 별도로 기록한다.

`build_scene.py`는 자체 `authoring/parts_template.factoryio`에서 새 장면을 작성하는 보조 스크립트다. 일반 실행에는 필요 없다. 최종 `.factoryio`는 독립적으로 열 수 있다.
