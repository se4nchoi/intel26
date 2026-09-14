from neuromeka import IndyDCP3
import time
indy = IndyDCP3("192.168.3.2")
print("Direct Teaching ON")
print(indy.set_direct_teaching(True))
time.sleep(10)
print("Direct Teaching OFF")
print(indy.set_direct_teaching(False))
# from neuromeka import IndyDCP3
# import time
# ROBOT_IP = "192.168.3.2"
# indy = IndyDCP3(ROBOT_IP)
# # 현재 위치 출력
# def print_current_position():
#     try:
#         state = indy.get_control_state()
#         print("\n현재 Joint 위치")
#         print(state.get("q"))
#         print("\n현재 Task 위치")
#         print(state.get("p"))
#     except Exception as e:
#         print("현재 위치 읽기 오류 :", e)
# # Direct Teaching 시작
# def start_direct_teaching():
#     print("Direct Teaching 시작")
#     result = indy.set_direct_teaching(True)
#     print("Set Direct Teaching(True) Result =", result)
#     return result
# # Direct Teaching 종료
# def stop_direct_teaching():
#     print("Direct Teaching 종료")
#     result = indy.set_direct_teaching(False)
#     print("Set Direct Teaching(False) Result =", result)
#     return result
# # Direct Teaching 실행
# def direct_teaching_mode():
#     print("Indy7 Direct Teaching Mode")

#     # 현재 위치 출력
#     print_current_position()
#     # Direct Teaching 시작
#     start_direct_teaching()
#     print("\n로봇을 손으로 움직이십시오.")
#     print("Teaching을 종료하려면 Enter를 누르십시오.")
#     input()
#     # Direct Teaching 종료
#     stop_direct_teaching()
#     time.sleep(0.5)
#     print("\nTeaching 종료 후 위치")
#     print_current_position()
# # Main
# if __name__ == "__main__":
#     try:
#         direct_teaching_mode()
#     except KeyboardInterrupt:
#         print("\n사용자가 프로그램을 중지했습니다.")
#         try:
#             indy.set_direct_teaching(False)
#         except Exception as e:
#             print("Direct Teaching 종료 실패 :", e)
#     except Exception as e:
#         print("\nRobot Error :", e)
#     finally:
#         print("\n프로그램 종료")