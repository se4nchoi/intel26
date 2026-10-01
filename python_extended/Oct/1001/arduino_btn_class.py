import time
import threading
import psutil
import serial
import serial.tools.list_ports
import customtkinter as ctk

# 기본 테마: 다크 모드 (배경 Dark, 세련된 파스텔 네온/카드 톤)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class LEDControl:
    def __init__(self, seri_obj=None, port="COM6", baudrate=9600, master=None):
        # 1. 시리얼 통신 객체 초기화
        self.seri = None
        self.current_port = port
        self.baudrate = baudrate
        self.init_serial(seri_obj)

        # 2. 애니메이션 및 백그라운드 작업 제어 변수
        self.active_animation = None
        self.anim_thread = None
        self.stop_event = threading.Event()

        # 3. GUI 메인 윈도우 생성 (독립 실행 시 CTk, 다른 창에서 호출 시 CTkToplevel)
        if master is not None:
            self.win = ctk.CTkToplevel(master)
            self.win.attributes("-topmost", True)
        else:
            self.win = ctk.CTk()

        self.win.title("[파이썬] 4-LED OOP Controller & Fancy Effects")
        self.win.geometry("540x840")
        self.win.configure(fg_color="#0B0F19")
        self.win.resizable(False, False)

        # 4. LED 상태 및 체크박스 바인딩 변수 (LED 1~4)
        self.var_led1 = ctk.BooleanVar(value=False)
        self.var_led2 = ctk.BooleanVar(value=False)
        self.var_led3 = ctk.BooleanVar(value=False)
        self.var_led4 = ctk.BooleanVar(value=False)
        self.var_master = ctk.BooleanVar(value=False)

        # 5. UI 위젯 빌드
        self.build_ui()

        # 윈도우 닫기 이벤트 핸들러 등록
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)

    def init_serial(self, seri_obj):
        """기존 serial 인스턴스가 넘어오면 사용하고, 아니면 자동 감지 및 오픈"""
        if isinstance(seri_obj, serial.Serial):
            self.seri = seri_obj
        else:
            # 포트 감지 후 연결 시도
            self.connect_port(self.current_port)

    def connect_port(self, port_name):
        """지정된 포트로 시리얼 연결"""
        self.current_port = port_name
        try:
            if self.seri and self.seri.is_open:
                self.seri.close()
            self.seri = serial.Serial(port=port_name, baudrate=self.baudrate, timeout=1)
            print(f"[시리얼 연결 성공] {port_name}")
            if hasattr(self, 'conn_badge'):
                self.conn_badge.configure(text=f"● {port_name} 연결됨", fg_color="#064E3B", text_color="#6EE7B7")
                self.set_feedback(f"아두이노({port_name})에 연결되었습니다.", "success")
        except Exception as e:
            self.seri = None
            print(f"[시리얼 연결 실패] {port_name} : {e}")
            if hasattr(self, 'conn_badge'):
                err_str = str(e)
                if "PermissionError" in err_str or "액세스가 거부" in err_str:
                    self.conn_badge.configure(text=f"⚠ {port_name} 점유 중", fg_color="#451A24", text_color="#FDA4AF")
                    self.set_feedback("아두이노 IDE 시리얼 모니터를 닫고 재연결하세요.", "error")
                else:
                    self.conn_badge.configure(text=f"○ {port_name} 미연결", fg_color="#451A03", text_color="#FCD34D")
                    self.set_feedback(f"{port_name} 미연결 (테스트 모드)", "warning")

    # ================= 핵심 버튼 및 시리얼 전송 메서드 =================

    def button_click(self, value):
        """기존 코드 인터페이스 완벽 호환 + 확장 명령어 처리"""
        print("버튼: ", value)
        
        # 1. 애니메이션 관련 명령어 처리
        if value == 'BLINK':
            self.start_animation('BLINK')
            return
        elif value == 'KNIGHT_RIDER':
            self.start_animation('KNIGHT_RIDER')
            return
        elif value == 'BINARY_COUNTER':
            self.start_animation('BINARY_COUNTER')
            return
        elif value == 'POLICE':
            self.start_animation('POLICE')
            return
        elif value == 'CPU_METER':
            self.start_animation('CPU_METER')
            return
        elif value == 'STOP':
            self.stop_animation()
            self.button_click('ALL_OFF')
            return

        # 애니메이션이 실행 중인데 개별 수동 버튼을 누르면 애니메이션 일시 중지
        if self.active_animation:
            self.stop_animation()

        # 2. 개별 LED 및 마스터 제어
        if value in ('ON', 'LED1_ON'):
            self.set_led(1, True)
            send_data = 'A'
        elif value in ('OFF', 'LED1_OFF'):
            self.set_led(1, False)
            send_data = 'B'
        elif value == 'LED2_ON':
            self.set_led(2, True)
            send_data = 'C'
        elif value == 'LED2_OFF':
            self.set_led(2, False)
            send_data = 'D'
        elif value == 'LED3_ON':
            self.set_led(3, True)
            send_data = 'E'
        elif value == 'LED3_OFF':
            self.set_led(3, False)
            send_data = 'F'
        elif value == 'LED4_ON':
            self.set_led(4, True)
            send_data = 'G'
        elif value == 'LED4_OFF':
            self.set_led(4, False)
            send_data = 'H'
        elif value == 'ALL_ON':
            for i in range(1, 5):
                self.set_led(i, True)
            self.raw_write(b'A')
            self.raw_write(b'C')
            self.raw_write(b'E')
            self.raw_write(b'G')
            self.set_feedback("전체 LED (1~4) 점등 완료", "success")
            return
        elif value == 'ALL_OFF':
            for i in range(1, 5):
                self.set_led(i, False)
            self.raw_write(b'B')
            self.raw_write(b'D')
            self.raw_write(b'F')
            self.raw_write(b'H')
            self.set_feedback("전체 LED (1~4) 소등 완료", "normal")
            return
        else:
            return
        
        send_byte = send_data.encode()
        self.raw_write(send_byte)
        print("전송 데이터 : ", send_byte)

    def raw_write(self, send_byte):
        """시리얼 데이터 안전 전송"""
        if self.seri and self.seri.is_open:
            try:
                self.seri.write(send_byte)
            except Exception as e:
                print("전송 실패:", e)

    def set_led(self, index, state, sync_serial=False):
        """UI 배지 및 체크박스 상태 동기화"""
        vars_map = {1: self.var_led1, 2: self.var_led2, 3: self.var_led3, 4: self.var_led4}
        labels_map = {1: self.la1, 2: self.la2, 3: self.la3, 4: self.la4}
        pins_map = {1: 11, 2: 12, 3: 13, 4: 14}
        colors_on = {1: ("#064E3B", "#6EE7B7"), 2: ("#1E3A8A", "#93C5FD"), 3: ("#4C1D95", "#C4B5FD"), 4: ("#134E4A", "#5EEAD4")}

        vars_map[index].set(state)
        bg, fg = colors_on[index] if state else ("#451A24", "#FDA4AF")
        text = f"● LED {index} ON" if state else f"○ LED {index} OFF"
        labels_map[index].configure(text=text, fg_color=bg, text_color=fg)

        if sync_serial:
            cmd = {1: ('A', 'B'), 2: ('C', 'D'), 3: ('E', 'F'), 4: ('G', 'H')}[index][0 if state else 1]
            self.raw_write(cmd.encode())

        # 마스터 체크박스 갱신
        all_on = all(vars_map[i].get() for i in range(1, 5))
        self.var_master.set(all_on)

    # ================= 화려한 4-LED 애니메이션 기능 =================

    def start_animation(self, anim_name):
        """애니메이션 스레드 실행"""
        self.stop_animation()
        self.active_animation = anim_name
        self.stop_event.clear()

        names_ko = {
            'BLINK': '깜빡이 점멸 (Blink)',
            'KNIGHT_RIDER': '전격 Z작전 키트 스캐너 (Knight Rider)',
            'BINARY_COUNTER': '4비트 2진 카운터 (0~15)',
            'POLICE': '경찰차 경광등 스트로브 (Police Strobe)',
            'CPU_METER': '실시간 PC CPU 사용량 게이지 (Hardware Monitor)'
        }
        self.anim_badge.configure(
            text=f"▶ {names_ko.get(anim_name, anim_name)} 실행 중...",
            fg_color="#312E81",
            text_color="#C7D2FE"
        )
        self.set_feedback(f"효과 실행: {names_ko.get(anim_name, anim_name)}", "success")

        target_map = {
            'BLINK': self._loop_blink,
            'KNIGHT_RIDER': self._loop_knight_rider,
            'BINARY_COUNTER': self._loop_binary_counter,
            'POLICE': self._loop_police,
            'CPU_METER': self._loop_cpu_meter
        }

        self.anim_thread = threading.Thread(target=target_map[anim_name], daemon=True)
        self.anim_thread.start()

    def stop_animation(self):
        """현재 실행 중인 애니메이션 정지"""
        if self.active_animation:
            self.stop_event.set()
            if self.anim_thread and self.anim_thread.is_alive():
                self.anim_thread.join(timeout=0.3)
            self.active_animation = None
            if hasattr(self, 'anim_badge'):
                self.anim_badge.configure(text="■ 대기 중 (정지됨)", fg_color="#1E293B", text_color="#94A3B8")

    # 1) 전체 깜빡이 (Blink)
    def _loop_blink(self):
        while not self.stop_event.is_set():
            for i in range(1, 5):
                self.set_led(i, True, sync_serial=True)
            time.sleep(0.35)
            if self.stop_event.is_set():
                break
            for i in range(1, 5):
                self.set_led(i, False, sync_serial=True)
            time.sleep(0.35)

    # 2) 키트 스캐너 (Knight Rider / Cylon Eye) : 1 -> 2 -> 3 -> 4 -> 3 -> 2
    def _loop_knight_rider(self):
        sequence = [1, 2, 3, 4, 3, 2]
        curr_idx = 0
        while not self.stop_event.is_set():
            active_led = sequence[curr_idx]
            for i in range(1, 5):
                self.set_led(i, (i == active_led), sync_serial=True)
            curr_idx = (curr_idx + 1) % len(sequence)
            time.sleep(0.12)

    # 3) 4비트 2진수 카운터 (0 ~ 15)
    def _loop_binary_counter(self):
        count = 0
        while not self.stop_event.is_set():
            # bit0: LED 1, bit1: LED 2, bit2: LED 3, bit3: LED 4
            self.set_led(1, bool(count & 1), sync_serial=True)
            self.set_led(2, bool(count & 2), sync_serial=True)
            self.set_led(3, bool(count & 4), sync_serial=True)
            self.set_led(4, bool(count & 8), sync_serial=True)
            bin_str = format(count, '04b')
            self.set_feedback(f"2진수 카운터: {count} (2진법: {bin_str})", "normal")
            count = (count + 1) % 16
            time.sleep(0.45)

    # 4) 경찰차 스트로브 (1,2번 ↔ 3,4번 교차 급속 점멸)
    def _loop_police(self):
        while not self.stop_event.is_set():
            # 좌측(1,2번) 3회 플래시
            for _ in range(3):
                self.set_led(1, True, sync_serial=True)
                self.set_led(2, True, sync_serial=True)
                self.set_led(3, False, sync_serial=True)
                self.set_led(4, False, sync_serial=True)
                time.sleep(0.06)
                self.set_led(1, False, sync_serial=True)
                self.set_led(2, False, sync_serial=True)
                time.sleep(0.06)
            
            # 우측(3,4번) 3회 플래시
            for _ in range(3):
                self.set_led(1, False, sync_serial=True)
                self.set_led(2, False, sync_serial=True)
                self.set_led(3, True, sync_serial=True)
                self.set_led(4, True, sync_serial=True)
                time.sleep(0.06)
                self.set_led(3, False, sync_serial=True)
                self.set_led(4, False, sync_serial=True)
                time.sleep(0.06)

    # 5) 실시간 PC CPU 사용량 인디케이터 게이지!
    def _loop_cpu_meter(self):
        while not self.stop_event.is_set():
            cpu = psutil.cpu_percent(interval=0.5)
            # 0~25%: 1개, ~50%: 2개, ~75%: 3개, ~100%: 4개
            l1 = cpu >= 5
            l2 = cpu >= 25
            l3 = cpu >= 50
            l4 = cpu >= 75
            self.set_led(1, l1, sync_serial=True)
            self.set_led(2, l2, sync_serial=True)
            self.set_led(3, l3, sync_serial=True)
            self.set_led(4, l4, sync_serial=True)
            self.set_feedback(f"실시간 CPU 점유율: {cpu}%  [ 게이지: {'■'*sum([l1,l2,l3,l4])}{'□'*(4-sum([l1,l2,l3,l4]))} ]", "success")

    # ================= UI 레이아웃 구성 =================

    def build_ui(self):
        CARD_BG = "#161F30"
        BORDER_COL = "#253147"
        TEXT_MAIN = "#F1F5F9"
        TEXT_SUB = "#94A3B8"
        BOX_BG = "#111827"

        # 1. 헤더 카드 (포트 상태)
        header = ctk.CTkFrame(self.win, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=BORDER_COL)
        header.pack(fill="x", padx=18, pady=(16, 8))

        ctk.CTkLabel(header, text="Arduino 4-LED OOP Control Class", font=ctk.CTkFont(family="Malgun Gothic", size=17, weight="bold"), text_color=TEXT_MAIN).pack(anchor="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(header, text="클래스(LEDControl) 기반 제어 및 4-LED 다이나믹 효과 패널", font=ctk.CTkFont(family="Malgun Gothic", size=12), text_color=TEXT_SUB).pack(anchor="w", padx=16, pady=(0, 10))

        port_bar = ctk.CTkFrame(header, fg_color="transparent")
        port_bar.pack(fill="x", padx=16, pady=(0, 12))

        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports:
            ports = ["COM6"]
        elif "COM6" not in ports:
            ports.insert(0, "COM6")

        self.port_opt = ctk.CTkOptionMenu(port_bar, values=ports, width=120, height=28, corner_radius=8, fg_color=BOX_BG, text_color=TEXT_MAIN, button_color="#1E293B", command=self.connect_port)
        self.port_opt.set(self.current_port if self.current_port in ports else ports[0])
        self.port_opt.pack(side="left")

        self.conn_badge = ctk.CTkLabel(port_bar, text="연결 확인 중...", corner_radius=8, font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), height=28, padx=10)
        self.conn_badge.pack(side="left", padx=(8, 0))

        # 2. 4-LED 체크박스 토글 모니터링 카드
        chk_card = ctk.CTkFrame(self.win, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=BORDER_COL)
        chk_card.pack(fill="x", padx=18, pady=6)

        chk_header = ctk.CTkFrame(chk_card, fg_color="transparent")
        chk_header.pack(fill="x", padx=16, pady=(10, 6))

        ctk.CTkLabel(chk_header, text="개별 LED 체크박스 토글 (Pins 11, 12, 13, 14)", font=ctk.CTkFont(family="Malgun Gothic", size=13, weight="bold"), text_color=TEXT_MAIN).pack(side="left")

        self.chk_master = ctk.CTkCheckBox(
            chk_header, text="전체 토글", variable=self.var_master,
            command=lambda: self.button_click('ALL_ON' if self.var_master.get() else 'ALL_OFF'),
            font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"),
            fg_color="#6366F1", hover_color="#4F46E5", border_color="#475569", corner_radius=6, checkbox_width=18, checkbox_height=18
        )
        self.chk_master.pack(side="right")

        # 2x2 그리드
        grid = ctk.CTkFrame(chk_card, fg_color="transparent")
        grid.pack(fill="x", padx=14, pady=(0, 12))
        grid.columnconfigure((0, 1), weight=1)

        # LED 1
        b1 = ctk.CTkFrame(grid, fg_color=BOX_BG, corner_radius=10, border_width=1, border_color=BORDER_COL)
        b1.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        self.chk_led1 = ctk.CTkCheckBox(b1, text="LED 1 (Pin 11)", variable=self.var_led1, command=lambda: self.button_click('LED1_ON' if self.var_led1.get() else 'LED1_OFF'), font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), fg_color="#10B981", text_color="#A7F3D0")
        self.chk_led1.pack(anchor="w", padx=10, pady=(8, 4))
        self.la1 = ctk.CTkLabel(b1, text="○ LED 1 OFF", font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), fg_color="#451A24", text_color="#FDA4AF", corner_radius=6, height=24)
        self.la1.pack(fill="x", padx=10, pady=(0, 8))

        # LED 2
        b2 = ctk.CTkFrame(grid, fg_color=BOX_BG, corner_radius=10, border_width=1, border_color=BORDER_COL)
        b2.grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        self.chk_led2 = ctk.CTkCheckBox(b2, text="LED 2 (Pin 12)", variable=self.var_led2, command=lambda: self.button_click('LED2_ON' if self.var_led2.get() else 'LED2_OFF'), font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), fg_color="#3B82F6", text_color="#BFDBFE")
        self.chk_led2.pack(anchor="w", padx=10, pady=(8, 4))
        self.la2 = ctk.CTkLabel(b2, text="○ LED 2 OFF", font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), fg_color="#451A24", text_color="#FDA4AF", corner_radius=6, height=24)
        self.la2.pack(fill="x", padx=10, pady=(0, 8))

        # LED 3
        b3 = ctk.CTkFrame(grid, fg_color=BOX_BG, corner_radius=10, border_width=1, border_color=BORDER_COL)
        b3.grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        self.chk_led3 = ctk.CTkCheckBox(b3, text="LED 3 (Pin 13)", variable=self.var_led3, command=lambda: self.button_click('LED3_ON' if self.var_led3.get() else 'LED3_OFF'), font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), fg_color="#8B5CF6", text_color="#DDD6FE")
        self.chk_led3.pack(anchor="w", padx=10, pady=(8, 4))
        self.la3 = ctk.CTkLabel(b3, text="○ LED 3 OFF", font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), fg_color="#451A24", text_color="#FDA4AF", corner_radius=6, height=24)
        self.la3.pack(fill="x", padx=10, pady=(0, 8))

        # LED 4
        b4 = ctk.CTkFrame(grid, fg_color=BOX_BG, corner_radius=10, border_width=1, border_color=BORDER_COL)
        b4.grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        self.chk_led4 = ctk.CTkCheckBox(b4, text="LED 4 (Pin 14)", variable=self.var_led4, command=lambda: self.button_click('LED4_ON' if self.var_led4.get() else 'LED4_OFF'), font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), fg_color="#14B8A6", text_color="#99F6E4")
        self.chk_led4.pack(anchor="w", padx=10, pady=(8, 4))
        self.la4 = ctk.CTkLabel(b4, text="○ LED 4 OFF", font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), fg_color="#451A24", text_color="#FDA4AF", corner_radius=6, height=24)
        self.la4.pack(fill="x", padx=10, pady=(0, 8))

        # 3. 화려한 4-LED 이펙트 / 쇼타임 패널 (Fancy Things Panel)
        fancy_card = ctk.CTkFrame(self.win, fg_color=CARD_BG, corner_radius=16, border_width=1, border_color=BORDER_COL)
        fancy_card.pack(fill="x", padx=18, pady=6)

        fancy_header = ctk.CTkFrame(fancy_card, fg_color="transparent")
        fancy_header.pack(fill="x", padx=16, pady=(10, 6))

        ctk.CTkLabel(fancy_header, text="✨ 4-LED 다이나믹 쇼타임 & 모니터", font=ctk.CTkFont(family="Malgun Gothic", size=13, weight="bold"), text_color=TEXT_MAIN).pack(side="left")

        self.anim_badge = ctk.CTkLabel(fancy_header, text="■ 대기 중", font=ctk.CTkFont(family="Malgun Gothic", size=10, weight="bold"), fg_color="#1E293B", text_color="#94A3B8", corner_radius=6, height=22, padx=8)
        self.anim_badge.pack(side="right")

        f_grid = ctk.CTkFrame(fancy_card, fg_color="transparent")
        f_grid.pack(fill="x", padx=14, pady=(0, 10))
        f_grid.columnconfigure((0, 1), weight=1)

        # 🏎️ Knight Rider
        btn_kr = ctk.CTkButton(f_grid, text="🏎️ 키트 스캐너 (Knight Rider)", command=lambda: self.button_click('KNIGHT_RIDER'), font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), fg_color="#065F46", hover_color="#047857", text_color="#A7F3D0", height=32, corner_radius=8, width=0)
        btn_kr.grid(row=0, column=0, padx=3, pady=3, sticky="ew")

        # 🔢 4-bit Binary Counter
        btn_bin = ctk.CTkButton(f_grid, text="🔢 4비트 2진 카운터 (0~15)", command=lambda: self.button_click('BINARY_COUNTER'), font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), fg_color="#1E40AF", hover_color="#1D4ED8", text_color="#BFDBFE", height=32, corner_radius=8, width=0)
        btn_bin.grid(row=0, column=1, padx=3, pady=3, sticky="ew")

        # 🚨 Police Strobe
        btn_pol = ctk.CTkButton(f_grid, text="🚨 경찰차 경광등 (Police)", command=lambda: self.button_click('POLICE'), font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), fg_color="#7F1D1D", hover_color="#991B1B", text_color="#FECACA", height=32, corner_radius=8, width=0)
        btn_pol.grid(row=1, column=0, padx=3, pady=3, sticky="ew")

        # 💻 Real-time PC CPU Monitor
        btn_cpu = ctk.CTkButton(f_grid, text="💻 실시간 PC CPU 게이지", command=lambda: self.button_click('CPU_METER'), font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), fg_color="#0F766E", hover_color="#0D9488", text_color="#99F6E4", height=32, corner_radius=8, width=0)
        btn_cpu.grid(row=1, column=1, padx=3, pady=3, sticky="ew")

        # ⚡ 깜빡이 (Blink) & ⏹️ 애니메이션 정지 (Stop)
        btn_blk = ctk.CTkButton(f_grid, text="⚡ 깜빡이 점멸 (Blink)", command=lambda: self.button_click('BLINK'), font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), fg_color="#5B21B6", hover_color="#6D28D9", text_color="#DDD6FE", height=32, corner_radius=8, width=0)
        btn_blk.grid(row=2, column=0, padx=3, pady=3, sticky="ew")

        btn_stp = ctk.CTkButton(f_grid, text="⏹️ 효과 정지 (Stop & Clear)", command=lambda: self.button_click('STOP'), font=ctk.CTkFont(family="Malgun Gothic", size=11, weight="bold"), fg_color="#334155", hover_color="#475569", text_color="#F1F5F9", height=32, corner_radius=8, width=0)
        btn_stp.grid(row=2, column=1, padx=3, pady=3, sticky="ew")

        # 4. 하단 피드백 / 로그 바
        self.feedback_lbl = ctk.CTkLabel(self.win, text="원하는 효과 버튼이나 체크박스를 클릭하세요.", font=ctk.CTkFont(family="Malgun Gothic", size=11), fg_color=CARD_BG, text_color=TEXT_SUB, corner_radius=10, height=32, padx=14)
        self.feedback_lbl.pack(fill="x", padx=18, pady=(4, 14))

        # 초기 연결 상태 반영
        if self.seri and self.seri.is_open:
            self.conn_badge.configure(text=f"● {self.current_port} 연결됨", fg_color="#064E3B", text_color="#6EE7B7")

    def set_feedback(self, msg, status_type="normal"):
        colors = {
            "normal": ("#1E293B", "#94A3B8"),
            "success": ("#064E3B", "#6EE7B7"),
            "warning": ("#451A03", "#FCD34D"),
            "error": ("#451A24", "#FDA4AF"),
        }
        bg, fg = colors.get(status_type, colors["normal"])
        if hasattr(self, 'feedback_lbl'):
            self.feedback_lbl.configure(text=msg, fg_color=bg, text_color=fg)

    def on_close(self):
        """종료 시 애니메이션 중단 및 포트 정리"""
        self.stop_animation()
        try:
            if self.seri and self.seri.is_open:
                self.seri.close()
        except Exception:
            pass
        self.win.destroy()


# Standalone 실행 지원
if __name__ == "__main__":
    app = LEDControl(port="COM6")
    app.win.mainloop()