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
        # 建立「本次開機」專用的小帳本 (Dict)，key 為規則 ID
        self.session_errors = {
            r.get("id"): {"broken": 0, "no_upd": 0, "lost": 0}
            for r in self.rules_data
        }

        # UI 變數
        self.timer_mode = ctk.StringVar(value="固定秒數")
        self.timer_setting = ctk.StringVar(value="10.0")
        self.countdown_text = ctk.StringVar(value="等待啟動...")

        # --- 新增：每次啟動時將計數器歸零 ---
        # if self.rules_data:
        #    for rule in self.rules_data:
        #        rule['count_broken'] = 0
        #        rule['count_no_update'] = 0
        # rule['count_missing'] = 0

        self._create_widgets()
        self._refresh_tree()

        # 啟動引擎
        self.engine = TaskEngine(self, self.logger)

    def _create_widgets(self):
        # 新增這行：讀取存好的寬度設定，如果沒有就給空字典
        saved_widths = self.rules_data[0].get("ui_widths", {}) if (
            self.rules_data and "ui_widths" in self.rules_data[0]) else {}

        self.ctrl_frame = ctk.CTkFrame(self)
        self.ctrl_frame = ctk.CTkFrame(self)
        self.ctrl_frame.pack(fill="x", padx=10, pady=5)

        # 模式設定
        set_frame = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        set_frame.pack(side="left", padx=5)
        ctk.CTkLabel(set_frame, text="Timer模式:").pack(side="left", padx=5)
        ctk.CTkComboBox(set_frame, values=["固定秒數", "指定分鐘"],
                        variable=self.timer_mode, width=100).pack(side="left", padx=5)
        ctk.CTkEntry(set_frame, textvariable=self.timer_setting,
                     width=120).pack(side="left", padx=5)

        # 按鈕群
        btn_frame = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        btn_frame.pack(side="left", padx=15)
        ctk.CTkButton(btn_frame, text="+ 設定規則", width=90, fg_color="#28a745",
                      command=self._add_rule_btn_click).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="儲存狀態", width=90,
                      command=self._save_all).pack(side="left", padx=5)

        # 倒數計時 (修正顏色：深橘色 #D35400)
        self.lbl_countdown = ctk.CTkLabel(self.ctrl_frame, textvariable=self.countdown_text,
                                          font=("Arial", 15, "bold"), text_color="#D35400")
        self.lbl_countdown.pack(side="right", padx=15)

        # Treeview 表格
        style = ttk.Style()
        style.configure("Treeview", rowheight=28)

        columns = ("id", "loc", "file", "status",
                   "broken", "no_upd", "lost", "enable")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")

        saved_widths = self.rules_data[0].get(
            "ui_widths", {}) if self.rules_data else {}

        headers = {"id": "編號", "loc": "地點", "file": "來源檔名", "status": "狀態",
                   "broken": "破損", "no_upd": "無更新", "lost": "遺失", "enable": "啟用"}

        for col, text in headers.items():
            self.tree.heading(col, text=text)
            # 如果 JSON 有存寬度就用 JSON 的，否則用預設值
            w = saved_widths.get(col, 100 if len(col) > 5 else 65)
            self.tree.column(col, width=w, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree.bind("<Double-1>", self._on_double_click)

    def _refresh_tree(self):
        """刷新表格內容：顯示本次執行數據，保留底層歷史數據"""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for r in self.rules_data:
            rid = r.get("id")  # 確保取得 rid 給小帳本搜尋使用
            
            # 讀取小帳本中的「本次數據」
            s_err = self.session_errors.get(rid, {"broken": 0, "no_upd": 0, "lost": 0})

            # 只保留這一個 insert 動作
            self.tree.insert("", "end", values=(
                rid, 
                r.get("location",""), 
                r.get("source_filename",""),
                r.get("status","等待"), 
                s_err["broken"],  # 顯示小帳本：本次破損
                s_err["no_upd"],  # 顯示小帳本：本次無更新
                s_err["lost"],    # 顯示小帳本：本次遺失
                "V" if r.get("enabled") else "-"
            ))

    def update_status(self, rid, status, error_type=None):
        """[錨點] 接收引擎回報的狀態與錯誤"""
        for r in self.rules_data:
            if r.get("id") == rid:
                r["status"] = status
                # 如果有錯誤類型，同時更新「小帳本」與「歷史存摺」
                if error_type and rid in self.session_errors:
                    # 更新介面小帳本 (session_errors)
                    if error_type == "broken": self.session_errors[rid]["broken"] += 1
                    elif error_type == "no_upd": self.session_errors[rid]["no_upd"] += 1
                    elif error_type == "lost": self.session_errors[rid]["lost"] += 1
                    
                    # 更新歷史存摺 (rules_data)
                    field_map = {"broken": "count_broken", "no_upd": "count_no_update", "lost": "count_missing"}
                    target_field = field_map.get(error_type)
                    r[target_field] = r.get(target_field, 0) + 1
                break
        self._refresh_tree()

    def handle_engine_report(self, rid, error_type):
        """
        [新函式] 當背景引擎發現錯誤時，必須呼叫此處！
        error_type: "broken", "no_upd", "lost"
        """
        # (1) 同步更新「小帳本」(讓畫面會動)
        if rid in self.session_errors:
            if error_type == "broken": self.session_errors[rid]["broken"] += 1
            elif error_type == "no_upd": self.session_errors[rid]["no_upd"] += 1
            elif error_type == "lost": self.session_errors[rid]["lost"] += 1

        # (2) 同步更新「歷史存摺」(讓 JSON 紀錄歷史)
        for r in self.rules_data:
            if r.get("id") == rid:
                field_name = f"count_{error_type.replace('no_upd', 'no_update').replace('lost', 'missing')}"
                r[field_name] = r.get(field_name, 0) + 1
                break
        
        # (3) 立即刷新畫面與存檔
        self._refresh_tree()
        self.config_mgr.save_config(self.rules_data)

    def _on_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        idx = self.tree.item(selected)["values"][0]
        RuleEditor(self, self.rules_data[idx-1], self._update_callback)

    def _add_rule_btn_click(self):
        tid = simpledialog.askinteger(
            "設定", "輸入規則編號 (1-256):", minvalue=1, maxvalue=256)
        if tid:
            RuleEditor(self, self.rules_data[tid-1], self._update_callback)

    def _update_callback(self, rid, data):
        # (1) 更新小帳本 (UI 顯示用)
        if rid in self.session_errors:
            self.session_errors[rid]["broken"] += data.get('new_broken', 0)
            self.session_errors[rid]["no_upd"] += data.get('new_no_upd', 0)
            self.session_errors[rid]["lost"] += data.get('new_lost', 0)

        # (2) 更新 rules_data 並處理狀態更新
        for r in self.rules_data:
            if r.get("id") == rid:
                # 歷史計數累加
                r["count_broken"] = r.get("count_broken", 0) + data.get('new_broken', 0)
                r["count_no_update"] = r.get("count_no_update", 0) + data.get('new_no_upd', 0)
                r["count_missing"] = r.get("count_missing", 0) + data.get('new_lost', 0)
                
                # 更新其他欄位 (從編輯器回傳的 data)
                r.update(data)
                r["enabled"] = True
                r["status"] = "正常"
                break
        
        # (3) 存檔與刷新
        self.config_mgr.save_config(self.rules_data)
        self._refresh_tree()

    def _save_all(self):
        """儲存目前所有規則狀態與 Treeview 欄位寬度"""
        # 1. 抓取目前 Treeview 每個欄位的寬度
        current_widths = {}
        columns = ("id", "loc", "file", "status",
                   "broken", "no_upd", "lost", "enable")
        for col in columns:
            current_widths[col] = self.tree.column(col, "width")

        # 2. 將寬度資訊存入 rules_data 的第一筆規則中 (作為全域介面設定)
        if self.rules_data:
            self.rules_data[0]["ui_widths"] = current_widths

        # 3. 呼叫 config_mgr 寫入 JSON
        self.config_mgr.save_config(self.rules_data)

        # 4. 記錄日誌
        if self.logger:
            self.logger.write_log("已儲存當前配置與欄位寬度設定。")
