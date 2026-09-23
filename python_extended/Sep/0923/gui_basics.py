from tkinter import *
win = Tk()
win.geometry("400x400")
win.title("choi")
txt = Text(win, width=10, height=5)
txt.insert("1.5", "enter text...")
txt.pack()

e=Entry(win, width=30)
e.pack()
e.insert(0, "enter 1 line")

def btnCmd():
    print(txt.get("1.0", "end"))
    print(e.get())
    e.delete(0, 'end')

btn = Button(win, text="click", command=btnCmd)
btn.pack()

win.mainloop()