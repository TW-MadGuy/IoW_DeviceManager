import customtkinter as ctk
from tkinter import Menu
from collections import deque

class RAMLogger(ctk.CTkTextbox):
    def __init__(self, master, max_lines=2000, **kwargs): # max_lines 可自行調整
        super().__init__(master, **kwargs)
        self.log_data = deque(maxlen=max_lines) # 自動推擠的核心
        self.configure(state="disabled")
        
        # 右鍵選單
        self.menu = Menu(self, tearoff=0)
        self.menu.add_command(label="複製全部 (Copy All)", command=self.copy_all)
        self.menu.add_command(label="另存 Log (Save as)", command=self.save_to_file)
        self.menu.add_separator()
        self.menu.add_command(label="清空 (Clear)", command=self.clear_log)
        self.bind("<Button-3>", self.show_menu)

    def write_log(self, text):
        """
        這是我標示出的功能函數，內容您可以之後自行精簡。
        """
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 這裡的文字格式您可以自行修改
        log_entry = f"[{timestamp}] {text}"
        self.log_data.append(log_entry)
        
        # 刷新介面顯示
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.insert("end", "\n".join(self.log_data))
        self.see("end")
        self.configure(state="disabled")

    def show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def copy_all(self):
        self.clipboard_clear()
        self.clipboard_append("\n".join(self.log_data))

    def save_to_file(self):
        # 這裡留給您未來實作 file_save_as 邏輯
        pass

    def clear_log(self):
        self.log_data.clear()
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")