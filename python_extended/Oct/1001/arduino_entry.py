import serial
import serial.tools.list_ports
import customtkinter as ctk

# 기본 테마: 다크 모드 (배경 Dark, 세련된 파스텔 네온/카드 톤)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

seri = None
current_port = "COM6"

def get_detected_ports():
    """연결된 포트 목록을 검색하고 아두이노가 있으면 우선 반환"""
    ports = list(serial.tools.list_ports.comports())
    port_dict = {}
    best_port = None

    for p in ports:
        desc = p.description or ""
        label = f"{p.device} ({desc})" if desc else p.device
        port_dict[label] = p.device
        
        # 아두이노 관련 키워드 감지 시 우선 선택
        if any(keyword in desc.lower() for keyword in ["arduino", "ch340", "usb-serial", "cp210"]):
            best_port = label

    if not port_dict:
        port_dict["COM6 (미연결)"] = "COM6"
        best_port = "COM6 (미연결)"
    elif not best_port:
        best_port = list(port_dict.keys())[0]

    return port_dict, best_port

def connect_serial(target_device):
    global seri, current_port
    current_port = target_device
    try:
        if seri and seri.is_open:
            seri.close()
        seri = serial.Serial(port=target_device, baudrate=9600, timeout=1)
        update_conn_badge(True, f"● {target_device} 연결 성공")
        set_feedback(f"아두이노({target_device}) 연결 완료! 체크박스로 LED를 토글할 수 있습니다.", "success")
    except serial.serialutil.SerialException as se:
        seri = None
        err_msg = str(se)
        if "PermissionError" in err_msg or "액세스가 거부" in err_msg:
            update_conn_badge(False, f"⚠ {target_device} 포트 점유 중")
            set_feedback("아두이노 IDE의 [시리얼 모니터]를 닫은 후 [⟳ 재연결]을 눌러주세요.", "error")
        else:
            update_conn_badge(False, f"○ {target_device} 미연결 (테스트 모드)")
            set_feedback(f"{target_device} 연결 대기: 케이블 연결 및 포트 번호를 확인해주세요.", "warning")
    except Exception as e:
        seri = None
        update_conn_badge(False, f"○ {target_device} 오류")
        set_feedback(f"오류 발생: {e}", "error")

def refresh_ports():
    """포트 목록 다시 검색 및 갱신"""
    port_dict, best_port = get_detected_ports()
    port_dropdown.configure(values=list(port_dict.keys()))
    port_dropdown.set(best_port)
    connect_serial(port_dict[best_port])

def update_conn_badge(connected: bool, text: str):
    if connected:
        conn_badge.configure(text=text, fg_color="#064E3B", text_color="#6EE7B7")
    elif "포트 점유" in text:
        conn_badge.configure(text=text, fg_color="#451A24", text_color="#FDA4AF")
    else:
        conn_badge.configure(text=text, fg_color="#451A03", text_color="#FCD34D")

def set_feedback(msg: str, status_type: str = "normal"):
    colors = {
        "normal": ("#1E293B", "#94A3B8"),
        "success": ("#064E3B", "#6EE7B7"),
        "warning": ("#451A03", "#FCD34D"),
        "error": ("#451A24", "#FDA4AF"),
    }
    bg, fg = colors.get(status_type, colors["normal"])
    feedback_lbl.configure(text=msg, fg_color=bg, text_color=fg)

# --- 메인 윈도우 생성 (다크 슬레이트 배경) ---
win = ctk.CTk()
win.title("[파이썬] 4-LED Checkbox Toggle Controller - Arduino")
win.geometry("520x720")
win.configure(fg_color="#0B0F19")  # 딥 다크 배경
win.resizable(False, False)

# --- 체크박스 바인딩 변수들 ---
var_led1 = ctk.BooleanVar(value=False)
var_led2 = ctk.BooleanVar(value=False)
var_led3 = ctk.BooleanVar(value=False)
var_led4 = ctk.BooleanVar(value=False)
var_master = ctk.BooleanVar(value=False)

def apply_led1_state(is_on: bool, send_serial: bool = True):
    var_led1.set(is_on)
    if is_on:
        la1.configure(text="● LED 1 ON", fg_color="#064E3B", text_color="#6EE7B7")
        if send_serial:
            send_to_serial(b'A', "첫번째 LED ON (A / Pin 11)")
    else:
        la1.configure(text="○ LED 1 OFF", fg_color="#451A24", text_color="#FDA4AF")
        if send_serial:
            send_to_serial(b'B', "첫번째 LED OFF (B / Pin 11)")
    update_master_checkbox()

def apply_led2_state(is_on: bool, send_serial: bool = True):
    var_led2.set(is_on)
    if is_on:
        la2.configure(text="● LED 2 ON", fg_color="#1E3A8A", text_color="#93C5FD")
        if send_serial:
            send_to_serial(b'C', "두번째 LED ON (C / Pin 12)")
    else:
        la2.configure(text="○ LED 2 OFF", fg_color="#451A24", text_color="#FDA4AF")
        if send_serial:
            send_to_serial(b'D', "두번째 LED OFF (D / Pin 12)")
    update_master_checkbox()

def apply_led3_state(is_on: bool, send_serial: bool = True):
    var_led3.set(is_on)
    if is_on:
        la3.configure(text="● LED 3 ON", fg_color="#4C1D95", text_color="#C4B5FD")
        if send_serial:
            send_to_serial(b'E', "세번째 LED ON (E / Pin 13)")
    else:
        la3.configure(text="○ LED 3 OFF", fg_color="#451A24", text_color="#FDA4AF")
        if send_serial:
            send_to_serial(b'F', "세번째 LED OFF (F / Pin 13)")
    update_master_checkbox()

def apply_led4_state(is_on: bool, send_serial: bool = True):
    var_led4.set(is_on)
    if is_on:
        la4.configure(text="● LED 4 ON", fg_color="#134E4A", text_color="#5EEAD4")
        if send_serial:
            send_to_serial(b'G', "네번째 LED ON (G / Pin 14)")
    else:
        la4.configure(text="○ LED 4 OFF", fg_color="#451A24", text_color="#FDA4AF")
        if send_serial:
            send_to_serial(b'H', "네번째 LED OFF (H / Pin 14)")
    update_master_checkbox()

def update_master_checkbox():
    """모든 개별 체크박스가 켜지면 마스터 체크, 하나라도 꺼지면 해제"""
    all_checked = var_led1.get() and var_led2.get() and var_led3.get() and var_led4.get()
    var_master.set(all_checked)

# 체크박스 클릭 핸들러
def on_toggle_led1():
    apply_led1_state(var_led1.get())

def on_toggle_led2():
    apply_led2_state(var_led2.get())

def on_toggle_led3():
    apply_led3_state(var_led3.get())

def on_toggle_led4():
    apply_led4_state(var_led4.get())

def on_toggle_master():
    target_state = var_master.get()
    apply_led1_state(target_state)
    apply_led2_state(target_state)
    apply_led3_state(target_state)
    apply_led4_state(target_state)
    if target_state:
        set_feedback("전체 4개 LED가 켜졌습니다. (ALL ON)", "success")
    else:
        set_feedback("전체 4개 LED가 꺼졌습니다. (ALL OFF)", "normal")

fancy_window_instance = None

def open_fancy_panel():
    global fancy_window_instance
    if fancy_window_instance is None or not fancy_window_instance.win.winfo_exists():
        import arduino_btn_class
        fancy_window_instance = arduino_btn_class.LEDControl(
            seri_obj=seri,
            port=current_port,
            master=win
        )
    else:
        fancy_window_instance.win.focus()

# --- 메인 컨트롤 함수 (jang1 - Entry 호환 유지) ---
def jang1():
    va11 = e1.get().strip().lower()
    
    if va11 == "led1on":
        apply_led1_state(True)
    elif va11 == "led1off":
        apply_led1_state(False)
    elif va11 == "led2on":
        apply_led2_state(True)
    elif va11 == "led2off":
        apply_led2_state(False)
    elif va11 == "led3on":
        apply_led3_state(True)
    elif va11 == "led3off":
        apply_led3_state(False)
    elif va11 == "led4on":
        apply_led4_state(True)
    elif va11 == "led4off":
        apply_led4_state(False)
    elif va11 == "allon":
        var_master.set(True)
        on_toggle_master()
    elif va11 == "alloff":
        var_master.set(False)
        on_toggle_master()
    elif va11 in ("fancy", "knight", "police", "binary", "cpu", "blink"):
        open_fancy_panel()
        if fancy_window_instance:
            anim_map = {
                "knight": "KNIGHT_RIDER",
                "police": "POLICE",
                "binary": "BINARY_COUNTER",
                "cpu": "CPU_METER",
                "blink": "BLINK"
            }
            if va11 in anim_map:
                fancy_window_instance.button_click(anim_map[va11])
        set_feedback(f"쇼타임 패널 실행: '{va11}' 모드 가동", "success")
    else:
        set_feedback(f"입력 오류: '{va11}' (유효: led1on~led4off, allon, alloff, fancy)", "error")
        return

def send_to_serial(byte_data, label_name):
    print(byte_data)
    if seri and seri.is_open:
        try:
            seri.write(byte_data)
            set_feedback(f"전송 완료: '{byte_data.decode()}' → {label_name}", "success")
        except Exception as e:
            set_feedback(f"전송 실패: {e}", "error")
    else:
        set_feedback(f"[시뮬레이션] '{byte_data.decode()}' → {label_name} (포트 미연결)", "warning")

# ================= UI 레이아웃 구성 =================

CARD_BG = "#161F30"      # 다크 카드 배경
BORDER_COL = "#253147"   # 카드 경계선
TEXT_MAIN = "#F1F5F9"    # 메인 화이트 텍스트
TEXT_SUB = "#94A3B8"     # 서브 텍스트
BOX_BG = "#111827"       # 내부 박스 배경

# 1. 상단 헤더 & 포트 감지 카드 (Dark Rounded Card)
header_card = ctk.CTkFrame(
    win,
    fg_color=CARD_BG,
    corner_radius=16,
    border_width=1,
    border_color=BORDER_COL
)
header_card.pack(fill="x", padx=18, pady=(16, 8))

header_top = ctk.CTkFrame(header_card, fg_color="transparent")
header_top.pack(fill="x", padx=16, pady=(12, 2))

title_label = ctk.CTkLabel(
    header_top,
    text="4-LED Checkbox Controller",
    font=ctk.CTkFont(family="Malgun Gothic", size=17, weight="bold"),
    text_color=TEXT_MAIN
)
title_label.pack(side="left")

btn_fancy_launcher = ctk.CTkButton(
    header_top,
    text="✨ 쇼타임 효과 열기",
    font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"),
    fg_color="#312E81",
    hover_color="#4338CA",
    text_color="#C7D2FE",
    height=28,
    corner_radius=8,
    command=open_fancy_panel
)
btn_fancy_launcher.pack(side="right")

subtitle_label = ctk.CTkLabel(
    header_card,
    text="[파이썬] 체크박스 토글 기반 아두이노 직렬 제어 패널 (Pins 11, 12, 13, 14)",
    font=ctk.CTkFont(family="Malgun Gothic", size=12),
    text_color=TEXT_SUB
)
subtitle_label.pack(anchor="w", padx=16, pady=(0, 10))

# 포트 선택 및 재검색 바
port_frame = ctk.CTkFrame(header_card, fg_color="transparent")
port_frame.pack(fill="x", padx=16, pady=(0, 12))

port_dict_init, initial_best = get_detected_ports()

def on_port_selected(choice_label):
    dev = port_dict_init.get(choice_label, choice_label.split(" ")[0])
    connect_serial(dev)

port_dropdown = ctk.CTkOptionMenu(
    port_frame,
    values=list(port_dict_init.keys()),
    width=200,
    height=28,
    corner_radius=8,
    fg_color=BOX_BG,
    text_color=TEXT_MAIN,
    button_color="#1E293B",
    button_hover_color="#334155",
    font=ctk.CTkFont(family="Malgun Gothic", size=11),
    command=on_port_selected
)
port_dropdown.set(initial_best)
port_dropdown.pack(side="left")

btn_refresh = ctk.CTkButton(
    port_frame,
    text="⟳ 재연결",
    width=65,
    height=28,
    corner_radius=8,
    font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"),
    fg_color="#312E81",
    hover_color="#4338CA",
    text_color="#C7D2FE",
    command=refresh_ports
)
btn_refresh.pack(side="left", padx=(6, 0))

conn_badge = ctk.CTkLabel(
    port_frame,
    text="연결 확인 중...",
    corner_radius=8,
    font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"),
    height=28,
    padx=10
)
conn_badge.pack(side="left", padx=(8, 0))


# 2. 4-LED 체크박스 토글 카드 (2x2 Grid Dark Rounded Card)
toggle_card = ctk.CTkFrame(
    win,
    fg_color=CARD_BG,
    corner_radius=16,
    border_width=1,
    border_color=BORDER_COL
)
toggle_card.pack(fill="x", padx=18, pady=6)

# 토글 카드 상단 헤더 & 마스터 전체 토글 체크박스
toggle_header_frame = ctk.CTkFrame(toggle_card, fg_color="transparent")
toggle_header_frame.pack(fill="x", padx=16, pady=(12, 8))

toggle_title = ctk.CTkLabel(
    toggle_header_frame,
    text="체크박스 LED 토글 제어",
    font=ctk.CTkFont(family="Malgun Gothic", size=14, weight="bold"),
    text_color=TEXT_MAIN
)
toggle_title.pack(side="left")

# 마스터 전체 제어 체크박스
chk_master = ctk.CTkCheckBox(
    toggle_header_frame,
    text="전체 일괄 토글 (ALL)",
    variable=var_master,
    command=on_toggle_master,
    font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"),
    fg_color="#6366F1",
    hover_color="#4F46E5",
    border_color="#475569",
    corner_radius=6,
    checkbox_width=20,
    checkbox_height=20,
    text_color="#C7D2FE"
)
chk_master.pack(side="right")

# 2x2 토글 서브 박스 그리드
grid_frame = ctk.CTkFrame(toggle_card, fg_color="transparent")
grid_frame.pack(fill="x", padx=14, pady=(0, 14))
grid_frame.columnconfigure((0, 1), weight=1)

# [LED 1 토글 박스 - Pin 11]
box1 = ctk.CTkFrame(grid_frame, fg_color=BOX_BG, corner_radius=12, border_width=1, border_color=BORDER_COL)
box1.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

chk_led1 = ctk.CTkCheckBox(
    box1,
    text="LED 1 (Pin 11 / OK)",
    variable=var_led1,
    command=on_toggle_led1,
    font=ctk.CTkFont(family="Malgun Gothic", size=12, weight="bold"),
    fg_color="#10B981",          # 소프트 민트 체크
    hover_color="#059669",
    border_color="#475569",
    corner_radius=6,
    checkbox_width=22,
    checkbox_height=22,
    text_color="#A7F3D0"
)
chk_led1.pack(anchor="w", padx=12, pady=(12, 8))

la1 = ctk.CTkLabel(
    box1,
    text="○ LED 1 OFF",
    font=ctk.CTkFont(family="Malgun Gothic", size=12, weight="bold"),
    fg_color="#451A24",
    text_color="#FDA4AF",
    corner_radius=8,
    height=30
)
la1.pack(fill="x", padx=12, pady=(0, 12))


# [LED 2 토글 박스 - Pin 12]
box2 = ctk.CTkFrame(grid_frame, fg_color=BOX_BG, corner_radius=12, border_width=1, border_color=BORDER_COL)
box2.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

chk_led2 = ctk.CTkCheckBox(
    box2,
    text="LED 2 (Pin 12 / NG)",
    variable=var_led2,
    command=on_toggle_led2,
    font=ctk.CTkFont(family="Malgun Gothic", size=12, weight="bold"),
    fg_color="#3B82F6",          # 스카이 블루 체크
    hover_color="#2563EB",
    border_color="#475569",
    corner_radius=6,
    checkbox_width=22,
    checkbox_height=22,
    text_color="#BFDBFE"
)
chk_led2.pack(anchor="w", padx=12, pady=(12, 8))

la2 = ctk.CTkLabel(
    box2,
    text="○ LED 2 OFF",
    font=ctk.CTkFont(family="Malgun Gothic", size=12, weight="bold"),
    fg_color="#451A24",
    text_color="#FDA4AF",
    corner_radius=8,
    height=30
)
la2.pack(fill="x", padx=12, pady=(0, 12))


# [LED 3 토글 박스 - Pin 13 확장]
box3 = ctk.CTkFrame(grid_frame, fg_color=BOX_BG, corner_radius=12, border_width=1, border_color=BORDER_COL)
box3.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

chk_led3 = ctk.CTkCheckBox(
    box3,
    text="LED 3 (Pin 13 / 확장)",
    variable=var_led3,
    command=on_toggle_led3,
    font=ctk.CTkFont(family="Malgun Gothic", size=12, weight="bold"),
    fg_color="#8B5CF6",          # 라벤더 퍼플 체크
    hover_color="#7C3AED",
    border_color="#475569",
    corner_radius=6,
    checkbox_width=22,
    checkbox_height=22,
    text_color="#DDD6FE"
)
chk_led3.pack(anchor="w", padx=12, pady=(12, 8))

la3 = ctk.CTkLabel(
    box3,
    text="○ LED 3 OFF",
    font=ctk.CTkFont(family="Malgun Gothic", size=12, weight="bold"),
    fg_color="#451A24",
    text_color="#FDA4AF",
    corner_radius=8,
    height=30
)
la3.pack(fill="x", padx=12, pady=(0, 12))


# [LED 4 토글 박스 - Pin 14 / A0 확장]
box4 = ctk.CTkFrame(grid_frame, fg_color=BOX_BG, corner_radius=12, border_width=1, border_color=BORDER_COL)
box4.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

chk_led4 = ctk.CTkCheckBox(
    box4,
    text="LED 4 (Pin 14 · A0)",
    variable=var_led4,
    command=on_toggle_led4,
    font=ctk.CTkFont(family="Malgun Gothic", size=12, weight="bold"),
    fg_color="#14B8A6",          # 틸 민트 체크
    hover_color="#0D9488",
    border_color="#475569",
    corner_radius=6,
    checkbox_width=22,
    checkbox_height=22,
    text_color="#99F6E4"
)
chk_led4.pack(anchor="w", padx=12, pady=(12, 8))

la4 = ctk.CTkLabel(
    box4,
    text="○ LED 4 OFF",
    font=ctk.CTkFont(family="Malgun Gothic", size=12, weight="bold"),
    fg_color="#451A24",
    text_color="#FDA4AF",
    corner_radius=8,
    height=30
)
la4.pack(fill="x", padx=12, pady=(0, 12))


# 3. 명령어 입력 카드 (Entry 제어 호환)
control_card = ctk.CTkFrame(
    win,
    fg_color=CARD_BG,
    corner_radius=16,
    border_width=1,
    border_color=BORDER_COL
)
control_card.pack(fill="x", padx=18, pady=6)

control_title = ctk.CTkLabel(
    control_card,
    text="명령어 입력 (Entry 제어)",
    font=ctk.CTkFont(family="Malgun Gothic", size=13, weight="bold"),
    text_color=TEXT_MAIN
)
control_title.pack(anchor="w", padx=16, pady=(10, 2))

control_sub = ctk.CTkLabel(
    control_card,
    text="명령어: led1on~led4off, allon, alloff (타이핑 시 체크박스 자동 연동)",
    font=ctk.CTkFont(family="Malgun Gothic", size=11),
    text_color=TEXT_SUB
)
control_sub.pack(anchor="w", padx=16, pady=(0, 8))

input_row = ctk.CTkFrame(control_card, fg_color="transparent")
input_row.pack(fill="x", padx=16, pady=(0, 12))

e1 = ctk.CTkEntry(
    input_row,
    placeholder_text="예: led1on 또는 allon",
    placeholder_text_color="#64748B",
    font=ctk.CTkFont(family="Malgun Gothic", size=13),
    height=36,
    corner_radius=10,
    fg_color=BOX_BG,
    border_color="#334155",
    border_width=1,
    text_color=TEXT_MAIN
)
e1.pack(side="left", fill="x", expand=True, padx=(0, 8))
e1.bind("<Return>", lambda event: jang1())

bu1 = ctk.CTkButton(
    input_row,
    text="전송",
    command=jang1,
    font=ctk.CTkFont(family="Malgun Gothic", size=13, weight="bold"),
    height=36,
    width=75,
    corner_radius=10,
    fg_color="#4F46E5",
    hover_color="#6366F1",
    text_color="#FFFFFF"
)
bu1.pack(side="right")


# 4. 하단 피드백 / 로그 바 (Dark Rounded Card)
feedback_lbl = ctk.CTkLabel(
    win,
    text="체크박스를 클릭하여 LED를 직접 켜고 꺼보세요.",
    font=ctk.CTkFont(family="Malgun Gothic", size=11),
    fg_color=CARD_BG,
    text_color=TEXT_SUB,
    corner_radius=10,
    height=32,
    padx=14
)
feedback_lbl.pack(fill="x", padx=18, pady=(4, 14))

# 초기 감지된 포트로 연결 시도
initial_target = port_dict_init.get(initial_best, "COM6")
connect_serial(initial_target)

if __name__ == "__main__":
    win.mainloop()
