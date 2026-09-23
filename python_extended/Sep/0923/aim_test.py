import tkinter as tk
import random
import time
import ctypes

# Enable High-DPI awareness on Windows for razor-sharp rendering
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class AimTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("APEX AIM // Reflex Lab")
        self.root.geometry("740x660")
        self.root.resizable(False, False)
        self.root.configure(bg="#0B0D13")

        # Game settings
        self.game_duration = 20  # seconds
        self.target_radius = 26  # pixels

        # Game state
        self.is_playing = False
        self.is_counting_down = False
        self.time_left = self.game_duration
        self.hits = 0
        self.total_clicks = 0
        self.reaction_times = []
        self.target_spawn_time = 0.0
        self.timer_after_id = None
        self.countdown_after_id = None
        self.last_target_pos = None

        self.create_widgets()

        # Keyboard shortcuts for zero-friction gaming
        self.root.bind("<space>", lambda e: self.on_hotkey_start())
        self.root.bind("<r>", lambda e: self.start_countdown())
        self.root.bind("<R>", lambda e: self.start_countdown())

    def create_widgets(self):
        # ── 1. Top HUD Bar (Zero Layout Shift via uniform grid columns) ─
        self.hud_container = tk.Frame(self.root, bg="#111420", pady=10, padx=14)
        self.hud_container.pack(side="top", fill="x")

        # Lock all 4 columns to mathematically identical, non-shifting widths
        self.hud_container.columnconfigure((0, 1, 2, 3), weight=1, uniform="stat_card")

        self.cards = {}
        stats_config = [
            ("TIME", f"{self.game_duration}s", "#00F2FE", "time"),
            ("HITS", "0", "#4FACFE", "hits"),
            ("ACCURACY", "100.0%", "#00F5D4", "acc"),
            ("AVG REACTION", "0 ms", "#FEE140", "reaction")
        ]

        for idx, (label, val, color, key) in enumerate(stats_config):
            card = tk.Frame(
                self.hud_container,
                bg="#181C2E",
                padx=10,
                pady=8,
                highlightbackground="#252A42",
                highlightthickness=1
            )
            card.grid(row=0, column=idx, sticky="nsew", padx=5)

            title_lbl = tk.Label(
                card, text=label, font=("Segoe UI", 8, "bold"),
                fg="#6E7699", bg="#181C2E", anchor="center"
            )
            title_lbl.pack(fill="x")

            # Fixed width label ensures single-digit vs double-digit numbers never jitter
            val_lbl = tk.Label(
                card, text=val, font=("Segoe UI", 16, "bold"),
                fg=color, bg="#181C2E", width=10, anchor="center"
            )
            val_lbl.pack(fill="x", pady=(2, 0))

            self.cards[key] = val_lbl

        # ── 2. Tactical Canvas ──────────────────────────────────────
        self.canvas_width = 740
        self.canvas_height = 510
        self.canvas = tk.Canvas(
            self.root,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="#0D101A",
            highlightthickness=0,
            cursor="crosshair"
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        self.draw_grid_background()

        # ── 3. Bottom Minimal Controls & Shortcut Bar ───────────────
        self.bottom_bar = tk.Frame(self.root, bg="#0B0D13", pady=10, padx=20)
        self.bottom_bar.pack(side="bottom", fill="x")

        # Restart Button on bottom left
        self.btn_bottom_restart = tk.Button(
            self.bottom_bar,
            text="↺ RESTART [R]",
            font=("Segoe UI", 9, "bold"),
            bg="#181C2E",
            fg="#BAC3E0",
            activebackground="#252A42",
            activeforeground="#FFFFFF",
            highlightbackground="#2D3552",
            highlightthickness=1,
            relief="flat",
            padx=14,
            pady=4,
            cursor="hand2",
            command=self.start_countdown
        )
        self.btn_bottom_restart.pack(side="left")

        # Shortcuts hint on bottom right
        self.lbl_shortcuts = tk.Label(
            self.bottom_bar,
            text="Hotkeys: [SPACE] Start / Restart  •  [R] Quick Reset",
            font=("Segoe UI", 9),
            fg="#515B7D",
            bg="#0B0D13"
        )
        self.lbl_shortcuts.pack(side="right")

        # Center Start Button inside Canvas Overlay
        self.center_button_window = None
        self.show_welcome_screen()

    def draw_grid_background(self):
        """Draws subtle tactical grid markings for a polished arena look."""
        grid_size = 40
        for x in range(0, self.canvas_width, grid_size):
            self.canvas.create_line(x, 0, x, self.canvas_height, fill="#121624", width=1, tags="bg_grid")
        for y in range(0, self.canvas_height, grid_size):
            self.canvas.create_line(0, y, self.canvas_width, y, fill="#121624", width=1, tags="bg_grid")

        # Center reticle mark
        cx, cy = self.canvas_width // 2, self.canvas_height // 2
        self.canvas.create_line(cx - 15, cy, cx + 15, cy, fill="#1D2338", width=1, tags="bg_grid")
        self.canvas.create_line(cx, cy - 15, cx, cy + 15, fill="#1D2338", width=1, tags="bg_grid")

    def clear_center_button(self):
        """Removes the embedded Tkinter button from the canvas if it exists."""
        if self.center_button_window:
            self.canvas.delete(self.center_button_window)
            self.center_button_window = None

    def show_welcome_screen(self):
        self.clear_center_button()
        self.canvas.delete("overlay")
        cx, cy = self.canvas_width // 2, self.canvas_height // 2

        # Card backdrop
        self.canvas.create_rectangle(
            cx - 240, cy - 110, cx + 240, cy + 110,
            fill="#121626", outline="#252D47", width=1, tags="overlay"
        )
        self.canvas.create_text(
            cx, cy - 60,
            text="APEX AIM TRAINER",
            fill="#FFFFFF", font=("Segoe UI", 18, "bold"), tags="overlay"
        )
        self.canvas.create_text(
            cx, cy - 25,
            text="20-second reflex & accuracy challenge",
            fill="#7B84A6", font=("Segoe UI", 10), justify="center", tags="overlay"
        )

        # Centered Start Button (Zero mouse travel to countdown!)
        btn_center_start = tk.Button(
            self.canvas,
            text="START TRAINING",
            font=("Segoe UI", 11, "bold"),
            bg="#FF2A5F",
            fg="#FFFFFF",
            activebackground="#FF4D7A",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=24,
            pady=8,
            cursor="hand2",
            command=self.start_countdown
        )
        btn_center_start.bind("<Enter>", lambda e: btn_center_start.config(bg="#FF4D7A"))
        btn_center_start.bind("<Leave>", lambda e: btn_center_start.config(bg="#FF2A5F"))

        self.center_button_window = self.canvas.create_window(
            cx, cy + 35, window=btn_center_start, tags="overlay"
        )

    def on_hotkey_start(self):
        """Allows pressing SPACE to start/restart cleanly."""
        if not self.is_playing:
            self.start_countdown()

    def cancel_active_timers(self):
        """Cancels running game loop or countdown timers."""
        if self.timer_after_id:
            self.root.after_cancel(self.timer_after_id)
            self.timer_after_id = None
        if self.countdown_after_id:
            self.root.after_cancel(self.countdown_after_id)
            self.countdown_after_id = None

    def start_countdown(self):
        """Triggered by center button, restart button, or hotkeys."""
        self.cancel_active_timers()
        self.clear_center_button()

        self.is_playing = False
        self.is_counting_down = True
        self.time_left = self.game_duration
        self.hits = 0
        self.total_clicks = 0
        self.reaction_times = []

        # Reset HUD
        self.cards["time"].config(text=f"{self.game_duration}s", fg="#00F2FE")
        self.cards["hits"].config(text="0")
        self.cards["acc"].config(text="100.0%")
        self.cards["reaction"].config(text="0 ms")

        # Clean canvas
        self.canvas.delete("overlay")
        self.canvas.delete("target")
        self.canvas.delete("fx")
        self.canvas.delete("countdown")

        # Run 2-second countdown right in the center: 2 -> 1 -> GO!
        self.step_countdown(2)

    def step_countdown(self, seconds_left):
        if not self.is_counting_down:
            return

        self.canvas.delete("countdown")
        cx, cy = self.canvas_width // 2, self.canvas_height // 2

        if seconds_left > 0:
            # Outer neon countdown ring centered where mouse is
            self.canvas.create_oval(
                cx - 65, cy - 65, cx + 65, cy + 65,
                fill="#121626", outline="#00F2FE", width=3, tags="countdown"
            )
            # Big countdown digit
            self.canvas.create_text(
                cx, cy - 2,
                text=str(seconds_left),
                fill="#FFFFFF", font=("Segoe UI", 36, "bold"), tags="countdown"
            )
            self.canvas.create_text(
                cx, cy + 90,
                text="GET READY",
                fill="#6E7699", font=("Segoe UI", 11, "bold"), tags="countdown"
            )

            self.countdown_after_id = self.root.after(1000, lambda: self.step_countdown(seconds_left - 1))
        else:
            # Flash "GO!" badge
            self.canvas.create_oval(
                cx - 65, cy - 65, cx + 65, cy + 65,
                fill="#121626", outline="#00F5D4", width=3, tags="countdown"
            )
            self.canvas.create_text(
                cx, cy - 2,
                text="GO!",
                fill="#00F5D4", font=("Segoe UI", 30, "bold"), tags="countdown"
            )

            self.countdown_after_id = self.root.after(300, self.begin_gameplay)

    def begin_gameplay(self):
        self.is_counting_down = False
        self.is_playing = True
        self.canvas.delete("countdown")

        self.spawn_target()
        self.timer_tick()

    def timer_tick(self):
        if not self.is_playing:
            return

        self.time_left -= 1
        # Formatted string length is constant to prevent any micro jitter
        self.cards["time"].config(text=f"{self.time_left}s")

        if self.time_left <= 5:
            self.cards["time"].config(fg="#FF4D4D")
        else:
            self.cards["time"].config(fg="#00F2FE")

        if self.time_left <= 0:
            self.end_game()
        else:
            self.timer_after_id = self.root.after(1000, self.timer_tick)

    def spawn_target(self):
        if not self.is_playing:
            return

        self.canvas.delete("target")

        margin = self.target_radius + 25
        x = random.randint(margin, self.canvas_width - margin)
        y = random.randint(margin, self.canvas_height - margin)
        self.last_target_pos = (x, y)
        r = self.target_radius

        # 1. Subtle Outer Glow Ring
        self.canvas.create_oval(
            x - (r + 7), y - (r + 7), x + (r + 7), y + (r + 7),
            fill="", outline="#3D1A2E", width=3, tags="target"
        )
        # 2. Main High-contrast Ring
        self.canvas.create_oval(
            x - r, y - r, x + r, y + r,
            fill="#FF2A5F", outline="#FFFFFF", width=2, tags="target"
        )
        # 3. Inner Concentric Ring
        self.canvas.create_oval(
            x - (r * 0.55), y - (r * 0.55), x + (r * 0.55), y + (r * 0.55),
            fill="#FFFFFF", outline="#FF2A5F", width=2, tags="target"
        )
        # 4. Precision Center Dot
        self.canvas.create_oval(
            x - 4, y - 4, x + 4, y + 4,
            fill="#FF2A5F", outline="", tags="target"
        )

        self.target_spawn_time = time.time()

    def on_canvas_click(self, event):
        if not self.is_playing or self.is_counting_down:
            return

        self.total_clicks += 1

        clicked = self.canvas.find_withtag("current")
        hit = any("target" in self.canvas.gettags(item) for item in clicked)

        if hit:
            reaction_ms = int((time.time() - self.target_spawn_time) * 1000)
            self.reaction_times.append(reaction_ms)
            self.hits += 1

            if self.last_target_pos:
                self.trigger_hit_fx(self.last_target_pos[0], self.last_target_pos[1], reaction_ms)

            self.update_stats()
            self.spawn_target()
        else:
            self.trigger_miss_fx(event.x, event.y)
            self.update_stats()

    def trigger_hit_fx(self, x, y, ms):
        """Creates an expanding ripple effect and floating response badge."""
        txt_id = self.canvas.create_text(
            x, y - 28, text=f"+1  {ms}ms", fill="#00F5D4",
            font=("Segoe UI", 10, "bold"), tags="fx"
        )
        ring_id = self.canvas.create_oval(
            x - 10, y - 10, x + 10, y + 10,
            outline="#00F5D4", width=2, tags="fx"
        )

        def animate(step=0):
            if step < 5:
                growth = (step + 1) * 7
                self.canvas.coords(ring_id, x - growth, y - growth, x + growth, y + growth)
                self.canvas.move(txt_id, 0, -3)
                self.root.after(35, lambda: animate(step + 1))
            else:
                self.canvas.delete(ring_id)
                self.canvas.delete(txt_id)

        animate()

    def trigger_miss_fx(self, x, y):
        """Creates a subtle red crosshair flash on click miss."""
        miss_tag = f"miss_{time.time()}"
        self.canvas.create_line(x - 8, y - 8, x + 8, y + 8, fill="#FF4D4D", width=2, tags=("fx", miss_tag))
        self.canvas.create_line(x - 8, y + 8, x + 8, y - 8, fill="#FF4D4D", width=2, tags=("fx", miss_tag))
        self.root.after(250, lambda: self.canvas.delete(miss_tag))

    def update_stats(self):
        self.cards["hits"].config(text=str(self.hits))

        acc = (self.hits / self.total_clicks * 100) if self.total_clicks > 0 else 100.0
        self.cards["acc"].config(text=f"{acc:.1f}%")

        if self.reaction_times:
            avg_rt = sum(self.reaction_times) // len(self.reaction_times)
            self.cards["reaction"].config(text=f"{avg_rt} ms")
        else:
            self.cards["reaction"].config(text="0 ms")

    def end_game(self):
        self.is_playing = False
        self.is_counting_down = False
        self.cancel_active_timers()

        self.canvas.delete("target")
        self.canvas.delete("fx")
        self.canvas.delete("countdown")

        acc = (self.hits / self.total_clicks * 100) if self.total_clicks > 0 else 0.0
        avg_rt = (sum(self.reaction_times) // len(self.reaction_times)) if self.reaction_times else 0

        # Performance Tier Assessment
        if avg_rt < 260 and acc >= 90:
            rank = "⚡ CYBORG REFLEXES (TIER S)"
            rank_color = "#FEE140"
        elif avg_rt < 340 and acc >= 80:
            rank = "🎯 SHARPSHOOTER (TIER A)"
            rank_color = "#00F5D4"
        elif avg_rt < 420:
            rank = "🏹 MARKSMAN (TIER B)"
            rank_color = "#4FACFE"
        else:
            rank = "👍 SOLID RECRUIT (TIER C)"
            rank_color = "#A0A8C0"

        # Game-over summary card
        cx, cy = self.canvas_width // 2, self.canvas_height // 2
        self.canvas.create_rectangle(
            cx - 240, cy - 130, cx + 240, cy + 130,
            fill="#121626", outline="#252D47", width=2, tags="overlay"
        )
        self.canvas.create_text(
            cx, cy - 85, text="SESSION COMPLETE",
            fill="#FFFFFF", font=("Segoe UI", 16, "bold"), tags="overlay"
        )
        self.canvas.create_text(
            cx, cy - 45, text=rank,
            fill=rank_color, font=("Segoe UI", 13, "bold"), tags="overlay"
        )
        self.canvas.create_text(
            cx, cy + 5,
            text=f"Hits: {self.hits}   •   Accuracy: {acc:.1f}%\nAverage Speed: {avg_rt} ms",
            fill="#BAC3E0", font=("Segoe UI", 11), justify="center", tags="overlay"
        )

        # Centered "PLAY AGAIN" Button right inside the results card
        btn_again = tk.Button(
            self.canvas,
            text="PLAY AGAIN",
            font=("Segoe UI", 11, "bold"),
            bg="#FF2A5F",
            fg="#FFFFFF",
            activebackground="#FF4D7A",
            activeforeground="#FFFFFF",
            relief="flat",
            padx=24,
            pady=7,
            cursor="hand2",
            command=self.start_countdown
        )
        btn_again.bind("<Enter>", lambda e: btn_again.config(bg="#FF4D7A"))
        btn_again.bind("<Leave>", lambda e: btn_again.config(bg="#FF2A5F"))

        self.center_button_window = self.canvas.create_window(
            cx, cy + 75, window=btn_again, tags="overlay"
        )


if __name__ == "__main__":
    root = tk.Tk()
    app = AimTestApp(root)
    root.mainloop()
