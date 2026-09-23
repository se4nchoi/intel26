import tkinter as tk
import tkinter.ttk as ttk

root = tk.Tk()
root.geometry("350x200")
root.title("Progressbar Demo")

# 1. Create a Determinate Progressbar (0 to 100)
pbar = ttk.Progressbar(root, maximum=100, length=250, mode="determinate")
pbar.pack(pady=30)

lbl = tk.Label(root, text="Click Start")
lbl.pack(pady=5)

# 2. Timer-driven update function (like recursive setTimeout)
def update_progress():
    current_val = pbar['value']
    
    if current_val < 100:
        pbar['value'] += 5                 # Increase progress
        lbl.config(text=f"Loading: {int(pbar['value'])}%")
        
        # Schedule the next tick in 50ms (non-blocking)
        root.after(50, update_progress)
    else:
        lbl.config(text="Done! 🎉")
        btn.config(state="normal")

def start_task():
    btn.config(state="disabled")
    pbar['value'] = 0
    update_progress()

btn = tk.Button(root, text="Start", command=start_task)
btn.pack(pady=10)

root.mainloop()
