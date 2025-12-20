import customtkinter as ctk
from tkinter import filedialog, messagebox
import os  # 修正：補上 os 模組

class RuleEditor(ctk.CTkToplevel):
    def __init__(self, master, rule_data, on_save_callback):
        super().__init__(master)
        self.title(f"編輯規則 - 編號 {rule_data['id']}")
        self.geometry("650x520") # 稍微拉高以容納新欄位
        self.attributes("-topmost", True)
        
        self.rule_data = rule_data
        self.on_save_callback = on_save_callback

        self._create_widgets()
        self._load_data()

    def _create_widgets(self):
        ctk.CTkLabel(self, text=f"規則編輯面板 (編號: {self.rule_data['id']})", 
                     font=("Microsoft JhengHei", 16, "bold")).pack(pady=10)

        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # [左欄: 來源設定]
        left_col = ctk.CTkFrame(main_frame)
        left_col.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(left_col, text="地點描述:").pack(anchor="w", padx=5)
        self.ent_loc = ctk.CTkEntry(left_col)
        self.ent_loc.pack(fill="x", padx=5, pady=2)

        ctk.CTkLabel(left_col, text="來源設定 (請點選檔案):").pack(anchor="w", padx=5, pady=(10,0))
        ctk.CTkButton(left_col, text="點我選取檔案", fg_color="#1f538d", 
                      command=self._browse_src_file).pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(left_col, text="來源資料匣:").pack(anchor="w", padx=5)
        self.ent_src_dir = ctk.CTkEntry(left_col, state="normal")
        self.ent_src_dir.pack(fill="x", padx=5, pady=2)

        ctk.CTkLabel(left_col, text="來源檔名:").pack(anchor="w", padx=5)
        self.ent_src_file = ctk.CTkEntry(left_col)
        self.ent_src_file.pack(fill="x", padx=5, pady=2)

        # [右欄: 輸出與還原設定]
        right_col = ctk.CTkFrame(main_frame)
        right_col.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(right_col, text="Resize 尺寸 (X / Y):").pack(anchor="w", padx=5)
        size_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        size_frame.pack(fill="x")
        self.ent_x = ctk.CTkEntry(size_frame, width=60)
        self.ent_x.pack(side="left", padx=5)
        ctk.CTkLabel(size_frame, text="x").pack(side="left")
        self.ent_y = ctk.CTkEntry(size_frame, width=60)
        self.ent_y.pack(side="left", padx=5)

        ctk.CTkLabel(right_col, text="備份輸出目錄 (-o, -s):").pack(anchor="w", padx=5, pady=(10,0))
        self.ent_out_dir = ctk.CTkEntry(right_col)
        self.ent_out_dir.pack(fill="x", padx=5, pady=2)
        ctk.CTkButton(right_col, text="選擇輸出目錄", command=self._browse_out_dir, height=20).pack(pady=2)

        ctk.CTkLabel(right_col, text="獨立還原目的地:").pack(anchor="w", padx=5, pady=(10,0))
        self.ent_restore_dir = ctk.CTkEntry(right_col)
        self.ent_restore_dir.pack(fill="x", padx=5, pady=2)
        ctk.CTkButton(right_col, text="選擇還原目錄", command=self._browse_restore_dir, height=20).pack(pady=2)

        # --- 按鈕區 ---
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", side="bottom", pady=20)
        
        ctk.CTkButton(btn_frame, text="儲存設定", fg_color="green", command=self._save).pack(side="right", padx=10)
        ctk.CTkButton(btn_frame, text="取消", fg_color="gray", command=self.destroy).pack(side="right", padx=10)

    def _load_data(self):
        self.ent_loc.insert(0, self.rule_data['location'])
        self.ent_src_dir.insert(0, self.rule_data['source_dir'])
        self.ent_src_file.insert(0, self.rule_data['source_filename'])
        self.ent_out_dir.insert(0, self.rule_data['output_dir'])
        self.ent_restore_dir.insert(0, self.rule_data.get('restore_dir', ""))
        self.ent_x.insert(0, str(self.rule_data['target_x']))
        self.ent_y.insert(0, str(self.rule_data['target_y']))

    def _browse_src_file(self):
        f = filedialog.askopenfilename(filetypes=[("影像檔案", "*.jpg *.png *.jpeg *.bmp")])
        if f:
            self.ent_src_dir.delete(0, "end")
            self.ent_src_dir.insert(0, os.path.dirname(f))
            self.ent_src_file.delete(0, "end")
            self.ent_src_file.insert(0, os.path.basename(f))

    def _browse_out_dir(self):
        d = filedialog.askdirectory()
        if d: 
            self.ent_out_dir.delete(0, "end")
            self.ent_out_dir.insert(0, d)

    def _browse_restore_dir(self):
        d = filedialog.askdirectory()
        if d: 
            self.ent_restore_dir.delete(0, "end")
            self.ent_restore_dir.insert(0, d)

    def _save(self):
        try:
            new_data = {
                "location": self.ent_loc.get(),
                "source_dir": self.ent_src_dir.get(),
                "source_filename": self.ent_src_file.get(),
                "output_dir": self.ent_out_dir.get(),
                "restore_dir": self.ent_restore_dir.get(),
                "target_x": int(self.ent_x.get()),
                "target_y": int(self.ent_y.get())
            }
            self.on_save_callback(self.rule_data['id'], new_data)
            self.destroy()
        except ValueError:
            messagebox.showerror("錯誤", "尺寸(X, Y)必須是數字！")