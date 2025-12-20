import customtkinter as ctk
from tkinter import ttk, simpledialog
from config_manager import ConfigManager
from tabs.rule_editor import RuleEditor
from task_engine import TaskEngine

class Tab4Backup(ctk.CTkFrame):
    def __init__(self, master, logger, **kwargs):
        super().__init__(master, **kwargs)
        self.logger = logger
        self.config_mgr = ConfigManager()
        self.rules_data = self.config_mgr.load_config()
        
        # UI 變數
        self.timer_mode = ctk.StringVar(value="固定秒數")
        self.timer_setting = ctk.StringVar(value="60.0")
        self.countdown_text = ctk.StringVar(value="等待啟動...")

        self._create_widgets()
        self._refresh_tree()
        
        # 啟動引擎
        self.engine = TaskEngine(self, self.logger)

    def _create_widgets(self):
        self.ctrl_frame = ctk.CTkFrame(self)
        self.ctrl_frame.pack(fill="x", padx=10, pady=5)

        # 模式設定
        set_frame = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        set_frame.pack(side="left", padx=5)
        ctk.CTkLabel(set_frame, text="Timer模式:").pack(side="left", padx=5)
        ctk.CTkComboBox(set_frame, values=["固定秒數", "指定分鐘"], 
                        variable=self.timer_mode, width=100).pack(side="left", padx=5)
        ctk.CTkEntry(set_frame, textvariable=self.timer_setting, width=120).pack(side="left", padx=5)

        # 按鈕群
        btn_frame = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        btn_frame.pack(side="left", padx=15)
        ctk.CTkButton(btn_frame, text="+ 設定規則", width=90, fg_color="#28a745", 
                      command=self._add_rule_btn_click).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="儲存狀態", width=90, command=self._save_all).pack(side="left", padx=5)

        # 倒數計時 (修正顏色：深橘色 #D35400)
        self.lbl_countdown = ctk.CTkLabel(self.ctrl_frame, textvariable=self.countdown_text, 
                                          font=("Arial", 15, "bold"), text_color="#D35400")
        self.lbl_countdown.pack(side="right", padx=15)

        # Treeview 表格
        style = ttk.Style()
        style.configure("Treeview", rowheight=28)
        
        columns = ("id", "loc", "file", "status", "broken", "no_upd", "lost", "enable")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        
        headers = {"id":"編號", "loc":"地點", "file":"來源檔名", "status":"狀態", 
                   "broken":"破損", "no_upd":"無更新", "lost":"遺失", "enable":"啟用"}
        for col, text in headers.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=60 if len(col)<5 else 120, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<Double-1>", self._on_double_click)

    def _refresh_tree(self):
        """重新整理表格數字與狀態"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        for r in self.rules_data:
            enable_mark = "✔" if r["enabled"] else "✘"
            # 狀態顯示由引擎更新的 rule['status'] 決定
            st = r.get('status', '停止')
            
            self.tree.insert("", "end", values=(
                r["id"], r["location"], 
                r["source_filename"] if r["source_filename"] else "---",
                st, r["count_broken"], r["count_no_update"],
                r["count_missing"], enable_mark
            ))

    def _on_double_click(self, event):
        selected = self.tree.selection()
        if not selected: return
        idx = self.tree.item(selected)["values"][0]
        RuleEditor(self, self.rules_data[idx-1], self._update_callback)

    def _add_rule_btn_click(self):
        tid = simpledialog.askinteger("設定", "輸入規則編號 (1-256):", minvalue=1, maxvalue=256)
        if tid: RuleEditor(self, self.rules_data[tid-1], self._update_callback)

    def _update_callback(self, rid, data):
        self.rules_data[rid-1].update(data)
        self.rules_data[rid-1]["enabled"] = True
        self.rules_data[rid-1]["status"] = "正常" # 編輯後重設狀態
        self.config_mgr.save_config(self.rules_data)
        self._refresh_tree()

    def _save_all(self):
        self.config_mgr.save_config(self.rules_data)
        self.logger.write_log("配置已手動存檔。")