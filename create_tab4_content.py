
import datetime
import os
import re
import tkinter as tk
from tkinter import Image, ttk
from tkinter import messagebox
from tkinter import filedialog

from utils import calculate_file_hash


# ====== 新增：創建TAB4照片處理介面 ======
def create_tab4_content(self):
    """創建第四個標籤頁 - 照片處理的介面"""
    # 頂部：全局控制面板
    control_frame = ttk.LabelFrame(self.tab4, text="全局輪巡控制", padding=(10, 5))
    control_frame.pack(fill=tk.X, padx=5, pady=(5, 2))

    # 定時間隔設定
    interval_frame = ttk.Frame(control_frame)
    interval_frame.pack(fill=tk.X, pady=2)

    ttk.Label(interval_frame, text="輪巡間隔:").pack(side=tk.LEFT, padx=(0, 5))
    self.timer_interval_var = tk.StringVar(
        value=str(self.global_timer_interval_minutes))
    interval_spinbox = tk.Spinbox(
        interval_frame,
        from_=0.1,
        to=1440,
        increment=1,
        textvariable=self.timer_interval_var,
        width=8,
        justify='right'
    )
    interval_spinbox.pack(side=tk.LEFT, padx=(0, 5))
    interval_spinbox.bind('<FocusOut>', self.on_timer_interval_changed)
    ttk.Label(interval_frame, text="分鐘").pack(side=tk.LEFT)

    # 定時器控制按鈕
    button_frame = ttk.Frame(control_frame)
    button_frame.pack(fill=tk.X, pady=5)

    ttk.Button(button_frame, text="啟動定時器",
               command=self.start_global_timer).pack(side=tk.LEFT, padx=2)
    ttk.Button(button_frame, text="停止定時器",
               command=self.stop_global_timer).pack(side=tk.LEFT, padx=2)
    ttk.Button(button_frame, text="立即執行一輪",
               command=self.manual_process_cycle).pack(side=tk.LEFT, padx=2)

    # 狀態顯示
    self.timer_status_var = tk.StringVar(value="狀態: 定時器未啟動")
    status_label = ttk.Label(
        control_frame, textvariable=self.timer_status_var, font=('Arial', 9))
    status_label.pack(pady=2)

    # 中間：處理原則列表 (Treeview)
    list_frame = ttk.LabelFrame(self.tab4, text="處理原則列表", padding=(5, 5))
    list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # 創建Treeview
    columns = ("編號", "標註", "來源檔案", "最終目的地", "狀態", "異常原因", "啟用")
    self.rule_tree = ttk.Treeview(
        list_frame, columns=columns, show="headings", height=12)

    # 設定欄位寬度
    column_widths = {"編號": 50, "標註": 120, "來源檔案": 150,
                     "最終目的地": 200, "狀態": 80, "異常原因": 150, "啟用": 60}
    for col in columns:
        self.rule_tree.heading(col, text=col)
        self.rule_tree.column(col, width=column_widths.get(col, 100))

    # 垂直滾動條
    v_scrollbar = ttk.Scrollbar(
        list_frame, orient=tk.VERTICAL, command=self.rule_tree.yview)
    self.rule_tree.configure(yscrollcommand=v_scrollbar.set)

    # 水平滾動條
    h_scrollbar = ttk.Scrollbar(
        list_frame, orient=tk.HORIZONTAL, command=self.rule_tree.xview)
    self.rule_tree.configure(xscrollcommand=h_scrollbar.set)

    # 使用grid佈局
    self.rule_tree.grid(row=0, column=0, sticky="nsew")
    v_scrollbar.grid(row=0, column=1, sticky="ns")
    h_scrollbar.grid(row=1, column=0, sticky="ew")

    # 配置權重
    list_frame.grid_rowconfigure(0, weight=1)
    list_frame.grid_columnconfigure(0, weight=1)

    # 底部：規則操作按鈕
    rule_button_frame = ttk.Frame(self.tab4)
    rule_button_frame.pack(fill=tk.X, padx=5, pady=(2, 5))

    ttk.Button(rule_button_frame, text="新增處理原則",
               command=self.add_processing_rule).pack(side=tk.LEFT, padx=2)
    ttk.Button(rule_button_frame, text="編輯選中原則",
               command=self.edit_selected_rule).pack(side=tk.LEFT, padx=2)
    ttk.Button(rule_button_frame, text="刪除選中原則",
               command=self.delete_selected_rule).pack(side=tk.LEFT, padx=2)
    ttk.Button(rule_button_frame, text="啟用/停用選中",
               command=self.toggle_rule_enable).pack(side=tk.LEFT, padx=2)

    # ====== Tab4 事件處理方法（最小化實現，避免錯誤）=====


#def _on_schedule_mode_changed(self, event=None):
    # 還未建立 #


def add_processing_rule(self):
    """新增一個處理原則 - 修正編號生成邏輯版"""
    # 檢查是否已達到64個原則的限制
    if len(self.processing_rules) >= 64:
        messagebox.showwarning("達到限制", "已達到最大處理原則數量 (64個)。\n請刪除不必要的原則後再新增。", )
        return

    # 【修正核心】先將當前編號儲存到一個變數中，供本規則所有地方使用
    current_rule_number = self.next_rule_number

    # 創建新規則，統一使用 current_rule_number
    rule_id = f"rule_{current_rule_number}"
    self.processing_rules[rule_id] = {
        "id": current_rule_number,  # 規則ID
        "name": f"處理原則 {current_rule_number}",
        "source_path": "",  # 具體檔案路徑，由用戶稍後設定
        # "source_file": f"Cam{current_rule_number}.jpg",  # 預設檔案名稱，與ID一致
        "source_file": "",  # 新邏輯：初始化為空，將從用戶選擇的路徑自動提取檔名
        "output_path": "",
        "backup_path": "./IMG",
        "resolution": "800x600",
        "timer_interval": self.global_timer_interval_minutes,
        "enabled": True,
        "status": "等待中",
        "last_error": "",
        "error_counter": 0,
    }

    # 【修正核心】規則建立完成後，再將下一個可用編號加1，供下一次新增使用
    self.next_rule_number += 1

    # 更新Treeview顯示
    self.refresh_rule_treeview()

    # 自動選中新添加的規則（可選，提升體驗）
    for child in self.rule_tree.get_children():
        values = self.rule_tree.item(child, "values")
        if int(values[0]) == current_rule_number:  # 使用 current_rule_number 來匹配
            self.rule_tree.selection_set(child)
            self.rule_tree.see(child)
            break

    self.log_message(f"已新增處理原則 #{current_rule_number}")  # 日誌也使用正確編號
    self.save_tab4_config()


def edit_selected_rule(self):
    """編輯選中的處理原則 - 完整實現（修正檔案選擇版）"""
    selected_items = self.rule_tree.selection()
    if not selected_items:
        messagebox.showinfo("提示", "請先選擇一個處理原則")
        return

    # 獲取選中的項目
    item = selected_items[0]
    values = self.rule_tree.item(item, "values")
    rule_id_num = int(values[0])  # 第一列是編號

    # 根據編號找到規則ID
    target_rule_id = None
    for rule_id, rule_data in self.processing_rules.items():
        if rule_data["id"] == rule_id_num:
            target_rule_id = rule_id
            break

    if target_rule_id is None:
        messagebox.showerror("錯誤", "找不到對應的規則")
        return

    rule_data = self.processing_rules[target_rule_id]

    # 創建編輯對話框
    edit_window = tk.Toplevel(self.root)
    edit_window.title(f"編輯處理原則 #{rule_id_num}")
    edit_window.geometry("500x450")
    edit_window.resizable(False, False)

    # 設置對話框為模態
    edit_window.transient(self.root)
    edit_window.grab_set()

    # 對話框框架
    main_frame = ttk.Frame(edit_window, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)

    row = 0

    # 1. 標註（名稱）
    ttk.Label(main_frame, text="標註名稱:").grid(
        row=row, column=0, sticky=tk.W, padx=5, pady=5
    )
    name_var = tk.StringVar(value=rule_data["name"])
    name_entry = ttk.Entry(main_frame, textvariable=name_var, width=40)
    name_entry.grid(
        row=row, column=1, columnspan=2, sticky=tk.W + tk.E, padx=5, pady=5
    )
    row += 1

    # 2. 來源檔案路徑 (關鍵修改點：選擇單一檔案)
    ttk.Label(main_frame, text="來源檔案:").grid(
        row=row, column=0, sticky=tk.W, padx=5, pady=5
    )
    source_path_var = tk.StringVar(value=rule_data.get("source_path", ""))
    source_path_entry = ttk.Entry(
        main_frame, textvariable=source_path_var, width=35
    )
    source_path_entry.grid(
        row=row, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

    def browse_source_path():
        # 使用 askopenfilename 來選擇單個圖片檔案
        file_path = filedialog.askopenfilename(
            title="選擇來源圖片檔案",
            filetypes=[("圖片檔案", "*.jpg *.jpeg *.png"), ("所有檔案", "*.*")],
        )
        if file_path:  # 用戶可能取消選擇，所以要判斷
            source_path_var.set(file_path)

    ttk.Button(main_frame, text="瀏覽", command=browse_source_path, width=8).grid(
        row=row, column=2, padx=(5, 0), pady=5
    )
    row += 1

    # 3. 最終目的地路徑 (仍然是資料夾)
    ttk.Label(main_frame, text="最終目的地:").grid(
        row=row, column=0, sticky=tk.W, padx=5, pady=5
    )
    output_path_var = tk.StringVar(value=rule_data.get("output_path", ""))
    output_path_entry = ttk.Entry(
        main_frame, textvariable=output_path_var, width=35
    )
    output_path_entry.grid(
        row=row, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

    def browse_output_path():
        path = filedialog.askdirectory(title="選擇最終目的地資料夾")
        if path:
            output_path_var.set(path)

    ttk.Button(main_frame, text="瀏覽", command=browse_output_path, width=8).grid(
        row=row, column=2, padx=(5, 0), pady=5
    )
    row += 1

    # 4. 備份路徑 (仍然是資料夾)
    ttk.Label(main_frame, text="備份路徑:").grid(
        row=row, column=0, sticky=tk.W, padx=5, pady=5
    )
    backup_path_var = tk.StringVar(value=rule_data.get("backup_path", "./IMG"))
    backup_path_entry = ttk.Entry(
        main_frame, textvariable=backup_path_var, width=35
    )
    backup_path_entry.grid(
        row=row, column=1, sticky=tk.W + tk.E, padx=5, pady=5)

    def browse_backup_path():
        path = filedialog.askdirectory(title="選擇備份資料夾")
        if path:
            backup_path_var.set(path)

    ttk.Button(main_frame, text="瀏覽", command=browse_backup_path, width=8).grid(
        row=row, column=2, padx=(5, 0), pady=5
    )
    row += 1

    # 5. 縮放解析度
    ttk.Label(main_frame, text="縮放解析度:").grid(
        row=row, column=0, sticky=tk.W, padx=5, pady=5
    )
    resolution_var = tk.StringVar(value=rule_data.get("resolution", "800x600"))
    resolution_entry = ttk.Entry(
        main_frame, textvariable=resolution_var, width=15)
    resolution_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    ttk.Label(main_frame, text="(格式: 寬x高, 如: 800x600)").grid(
        row=row, column=2, sticky=tk.W, padx=5, pady=5
    )
    row += 1

    # 6. 啟用/停用狀態
    enabled_var = tk.BooleanVar(value=rule_data.get("enabled", True))
    ttk.Checkbutton(main_frame, text="啟用此處理原則", variable=enabled_var).grid(
        row=row, column=1, columnspan=2, sticky=tk.W, padx=5, pady=10
    )
    row += 1

    # 按鈕區域
    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=row, column=0, columnspan=3, pady=20)

    def save_changes():
        """儲存變更"""
        # 驗證輸入
        if not name_var.get().strip():
            messagebox.showerror("錯誤", "標註名稱不能為空")
            return

        if not re.match(r"^\d+x\d+$", resolution_var.get().strip()):
            messagebox.showerror("錯誤", "解析度格式錯誤，請使用 寬x高 格式，如: 800x600")
            return

        # 更新規則數據
        rule_data["name"] = name_var.get().strip()
        rule_data["source_path"] = source_path_var.get().strip()
        rule_data["output_path"] = output_path_var.get().strip()
        rule_data["backup_path"] = backup_path_var.get().strip()
        rule_data["resolution"] = resolution_var.get().strip()
        rule_data["enabled"] = enabled_var.get()

        # 刷新Treeview
        self.refresh_rule_treeview()
        edit_window.destroy()
        self.log_message(f"已更新處理原則 #{rule_id_num}: {rule_data['name']}")

    ttk.Button(button_frame, text="儲存變更", command=save_changes,
               width=12).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="取消", command=edit_window.destroy,
               width=12).pack(side=tk.LEFT, padx=5)
    self.save_tab4_config()

    # 配置網格權重
    main_frame.grid_columnconfigure(1, weight=1)

    # 將焦點設置到名稱輸入框
    name_entry.focus_set()


def delete_selected_rule(self):
    """刪除選中的處理原則 - 完整實現"""
    selected_items = self.rule_tree.selection()
    if not selected_items:
        messagebox.showinfo("提示", "請先選擇一個處理原則")
        return

    item = selected_items[0]
    values = self.rule_tree.item(item, "values")
    rule_id_num = int(values[0])
    rule_name = values[1]

    # 確認刪除
    confirm = messagebox.askyesno(
        "確認刪除",
        f"確定要刪除處理原則 #{rule_id_num} - {rule_name} 嗎？\n\n此操作無法復原！",
    )

    if not confirm:
        return

    # 根據編號找到規則ID
    target_rule_id = None
    for rule_id, rule_data in self.processing_rules.items():
        if rule_data["id"] == rule_id_num:
            target_rule_id = rule_id
            break

    if target_rule_id is None:
        messagebox.showerror("錯誤", "找不到對應的規則")
        return

    # 刪除規則
    del self.processing_rules[target_rule_id]

    # 重新編號以保持連續性
    self.renumber_rules()

    # 刷新Treeview
    self.refresh_rule_treeview()
    self.log_message(f"已刪除處理原則 #{rule_id_num}: {rule_name}")
    self.save_tab4_config()


def renumber_rules(self):
    """重新編號規則以保持連續性"""
    sorted_rules = sorted(self.processing_rules.items(),
                          key=lambda x: x[1]["id"])

    new_rules = {}
    new_number = 1

    for rule_id, rule_data in sorted_rules:
        rule_data["id"] = new_number
        rule_data["source_file"] = f"Cam{new_number}.jpg"
        new_rule_id = f"rule_{new_number}"
        new_rules[new_rule_id] = rule_data
        new_number += 1

    self.processing_rules = new_rules
    self.next_rule_number = new_number


def toggle_rule_enable(self):
    """切換選中處理原則的啟用/停用狀態 - 完整實現"""
    selected_items = self.rule_tree.selection()
    if not selected_items:
        messagebox.showinfo("提示", "請先選擇一個處理原則")
        return

    item = selected_items[0]
    values = self.rule_tree.item(item, "values")
    rule_id_num = int(values[0])
    rule_name = values[1]

    # 根據編號找到規則ID
    target_rule_id = None
    for rule_id, rule_data in self.processing_rules.items():
        if rule_data["id"] == rule_id_num:
            target_rule_id = rule_id
            break

    if target_rule_id is None:
        messagebox.showerror("錯誤", "找不到對應的規則")
        return

    # 切換狀態
    rule_data = self.processing_rules[target_rule_id]
    new_state = not rule_data["enabled"]
    rule_data["enabled"] = new_state

    # 更新狀態顯示
    if new_state:
        rule_data["status"] = "等待中"
        rule_data["last_error"] = ""
        status_text = "啟用"
    else:
        rule_data["status"] = "已停用"
        status_text = "停用"

    # 刷新Treeview
    self.refresh_rule_treeview()
    self.log_message(f"處理原則 #{rule_id_num}: {rule_name} 已{status_text}")
    self.save_tab4_config()

    # 增加參數設定檔 將參數 寫入 此檔案中 以便喚回所有參數


def refresh_rule_treeview(self):
    """刷新Treeview顯示，僅顯示來源檔案的名稱（非完整路徑）"""
    # 刪除現有項目
    for item in self.rule_tree.get_children():
        self.rule_tree.delete(item)

    # 添加所有規則
    for rule_id, rule_data in self.processing_rules.items():
        # 核心邏輯：決定在列表中顯示什麼
        display_source = rule_data.get(
            "source_file", f"Cam{rule_data['id']}.jpg"
        )  # 預設為 CamX.jpg

        # 如果用戶已經選擇了具體檔案路徑，則從路徑中提取純檔名來顯示
        actual_path = rule_data.get("source_path", "")
        if actual_path:
            # # 直接從使用者選擇的路徑中取檔名顯示
            display_source = os.path.basename(actual_path)
        # 注意：如果路徑不存在或為空，則繼續使用上面的預設名稱

        values = (
            rule_data["id"],
            rule_data["name"],
            display_source,  # 現在這裡顯示的是乾淨的檔案名稱，如 "Cam1.jpg" 或 "我的照片.png"
            rule_data.get("output_path", ""),
            rule_data.get("status", "等待中"),
            rule_data.get("last_error", ""),
            "✓" if rule_data.get("enabled", False) else "✗",
        )
        self.rule_tree.insert("", tk.END, values=values)

    # ====== 新增：全局定時器控制方法 ======


def start_global_timer(self):
    """啟動或重啟全局定時器"""
    # 取消現有的定時器
    if self.global_timer_id:
        self.root.after_cancel(self.global_timer_id)

    # 獲取設定的間隔（分鐘）並轉換為毫秒
    try:
        minutes = float(self.timer_interval_var.get())
        if minutes < 0.1 or minutes > 1440:
            raise ValueError("間隔時間應在0.1到1440分鐘之間")
        self.global_timer_interval_minutes = minutes

    except ValueError as e:
        messagebox.showerror("輸入錯誤", f"請輸入有效的分鐘數(0.1-1440)\n錯誤: {e}")
        return

    interval_ms = int(self.global_timer_interval_minutes * 60 * 1000)

    # 設置新的定時器
    self.global_timer_id = self.root.after(
        interval_ms, self.process_all_rules_cycle
    )

    # 更新狀態顯示
    next_time = datetime.now() + datetime.timedelta(
        minutes=self.global_timer_interval_minutes
    )
    next_str = next_time.strftime("%H:%M:%S")
    self.timer_status_var.set(f"狀態: 定時器已啟動 - 下一輪於 {next_str} 開始")
    self.log_message(
        f"全局定時器已啟動，間隔: {self.global_timer_interval_minutes} 分鐘"
    )


def stop_global_timer(self):
    """停止全局定時器"""
    if self.global_timer_id:
        self.root.after_cancel(self.global_timer_id)
        self.global_timer_id = None
        self.timer_status_var.set("狀態: 定時器已停止")
        self.log_message("全局定時器已停止")


def _on_global_timer(self):


def _reschedule_timer(self):


def _check_specific_minute(self):


def manual_process_cycle(self):
    """手動觸發一輪處理（立即執行）"""
    if self.is_processing_cycle:
        messagebox.showinfo("處理中", "當前正在執行處理循環，請等待完成。")
        return

    self.timer_status_var.set("狀態: 手動執行處理循環中...")
    self.process_all_rules_cycle()


def process_all_rules_cycle(self):
    """執行一輪完整的處理（按順序處理所有啟用中的原則）"""
    if self.is_processing_cycle:
        self.log_message("警告: 上一輪處理尚未完成，跳過本次觸發。")
        self.start_global_timer()  # 直接重啟定時器
        return

    self.is_processing_cycle = True
    self.log_message("=== 開始新一輪圖片處理循環 ===")

    # 重置全局異常旗標（為本輪做準備）
    self.photo_check_failed = False

    # 獲取所有啟用中的規則並按編號排序
    enabled_rules = []
    for rule_id, rule_data in self.processing_rules.items():
        if rule_data.get("enabled", False):
            enabled_rules.append((rule_id, rule_data))

    # 按編號排序
    enabled_rules.sort(key=lambda x: x[1].get("id", 0))

    # 依序處理每個規則
    total_rules = len(enabled_rules)
    for idx, (rule_id, rule_data) in enumerate(enabled_rules, 1):
        # 更新狀態顯示
        self.timer_status_var.set(
            f"狀態: 處理中 ({idx}/{total_rules}) - {rule_data.get('name', '未命名')}"
        )
        self.root.update()  # 更新UI顯示

        # 處理單個規則
        self.process_single_rule(rule_id, rule_data)

    self.log_message(f"=== 本輪圖片處理循環結束，共處理 {total_rules} 個規則 ===")

    # 更新狀態顯示
    if self.photo_check_failed:
        self.timer_status_var.set("狀態: 處理完成（發現異常，已設置旗標）")
    else:
        self.timer_status_var.set("狀態: 處理完成（一切正常）")

    self.is_processing_cycle = False

    # 本輪結束後，重啟定時器進入下一個週期
    self.start_global_timer()


def process_single_rule(self, rule_id, rule_data):
    """處理單個規則 - 實現：檔案驗證模組"""
    rule_num = rule_data["id"]
    rule_name = rule_data["name"]
    source_path = rule_data.get("source_path", "")

    # 初始化本輪的錯誤訊息
    current_error = ""

    # ====== 1. 檢查檔案是否存在 ======
    if not source_path or not os.path.exists(source_path):
        current_error = "檔案不存在"
        self.log_message(
            f"規則 #{rule_num}: 來源檔案不存在。路徑: {source_path}", level="ERROR"
        )
        # 後續將交給異常處理模組
        self._handle_processing_error(rule_data, current_error)
        return  # 檔案不存在，後續步驟無法進行，直接結束本次處理

    # ====== 2. 檢查是否為有效圖片檔案 ======
    is_valid_image = False
    try:
        # 使用PIL嘗試開啟並驗證圖片
        with Image.open(source_path) as img:
            img.verify()  # 驗證檔案完整性，損壞的檔案會在此拋出異常
            # 如果驗證通過，再重新打開以供後續操作（verify()會關閉檔案）
            img = Image.open(source_path)
            img.load()  # 確保可以完全載入
            is_valid_image = True
            # 可以在此取得圖片資訊供後續使用，例如：
            rule_data["_last_image_size"] = img.size  # 儲存尺寸供比對
            img.close()
    except Exception as img_error:
        current_error = f"檔案破損 ({img_error})"
        self.log_message(
            f"規則 #{rule_num}: 圖片檔案損毀或格式不支持。錯誤: {img_error}",
            level="ERROR",
        )
        self._handle_processing_error(rule_data, current_error)
        return

    # ====== 3. 檢查檔案是否重複（與前次處理的內容比對） ======
    if is_valid_image:
        current_hash = calculate_file_hash(source_path)
        last_hash = rule_data.get("_last_valid_hash", None)

        if current_hash == last_hash and last_hash is not None:
            current_error = "檔案重複"
            self.log_message(
                f"規則 #{rule_num}: 檔案內容與上次處理時相同（重複）。",
                level="WARNING",
            )
            self._handle_processing_error(rule_data, current_error)
            return

        # 如果是不重複的有效檔案，更新哈希值記錄
        rule_data["_last_valid_hash"] = current_hash
        self.log_message(f"規則 #{rule_num}: 檔案驗證通過。")
        # *** 注意：這裡通過驗證，但尚未執行備份等操作 ***
        # 我們將在下一個模組（合格檔案處理）中接續這裡的邏輯
        # 目前先將狀態標記為正常，但實際的複製、移動操作還未進行
        rule_data["status"] = "正常"
        rule_data["last_error"] = ""
        # 重置錯誤計數器（因為本次拿到了有效的新檔案）
        rule_data["error_counter"] = 0
        self.refresh_rule_treeview()

    # *** 接續在「檔案驗證通過」的日誌輸出之後 ***
    # ====== 4. 合格檔案處理流程（備份、縮放、移動） ======
    self.log_message(f"規則 #{rule_num}: 開始執行檔案備份與處理...")

    # 準備路徑
    source_dir = os.path.dirname(source_path)
    source_filename = os.path.basename(source_path)  # 取得實際檔名，如 'ABC.jpg'
    filename_without_ext = os.path.splitext(source_filename)[
        0
    ]  # 去掉副檔名，例如 "Cam1"
    file_ext = os.path.splitext(source_filename)[1]  # 包含點的副檔名，例如 ".jpg"

    backup_path = rule_data.get("backup_path", "./IMG")
    output_path = rule_data.get("output_path", "")

    # 確保備份和輸出目錄存在
    os.makedirs(backup_path, exist_ok=True)
    if output_path:
        os.makedirs(output_path, exist_ok=True)

    try:
        import shutil  # 用於檔案複製和移動

        # 4.1 建立原始檔副本 (xxx-o.jpg)
        backup_base_name = os.path.splitext(rule_data["source_file"])[
            0
        ]  # 例如 'Cam2'
        backup_o = os.path.join(
            backup_path, f"{filename_without_ext}-o{file_ext}")
        shutil.copy2(source_path, backup_o)
        self.log_message(f"規則 #{rule_num}: 已建立原始備份 -> {backup_o}")

        # 4.2 建立縮放版本 (xxx-s.jpg)
        # 獲取設定的解析度
        resolution = rule_data.get("resolution", "800x600")
        try:
            target_width, target_height = map(int, resolution.split("x"))
        except:
            target_width, target_height = 800, 600  # 預設值
            self.log_message(
                f"規則 #{rule_num}: 解析度格式無效，使用預設 800x600", "WARNING"
            )

        # 打開圖片並進行縮放
        img = Image.open(source_path)
        # 保持寬高比的縮放（可選，這裡使用最簡單的強制縮放）
        img_resized = img.resize(
            (target_width, target_height), Image.Resampling.LANCZOS
        )
        backup_s = os.path.join(
            backup_path, f"{filename_without_ext}-s{file_ext}"
        )  # 儲存xxx-s.jpg
        img_resized.save(backup_s, quality=95)
        img.close()
        self.log_message(f"規則 #{rule_num}: 已建立縮放備份 -> {backup_s}")

        # 4.3 將原始檔案“複製”到最終目的地（關鍵修正：保留來源檔）
        if output_path:
            final_dest = os.path.join(output_path, source_filename)
            # 如果目的地已有同名檔案，可選擇覆蓋或跳過（這裡選擇覆蓋）
            if os.path.exists(final_dest):
                self.log_message(
                    f"規則 #{rule_num}: 目的地檔案已存在，將被覆蓋。", "WARNING"
                )
            # ========== 核心修正線：將 shutil.move 改為 shutil.copy2 ==========
            shutil.copy2(source_path, final_dest)  # 複製並保留元數據
            # =================================================================
            self.log_message(f"規則 #{rule_num}: 已複製原始檔至 -> {final_dest}")
            # *** 重要：不再更新 rule_data['source_path']，來源路徑保持不變 ***
        else:
            self.log_message(
                f"規則 #{rule_num}: 未設定最終目的地，跳過複製。", "INFO"
            )

        # 4.4 更新規則狀態
        rule_data["status"] = "正常 (已處理)"
        rule_data["last_error"] = ""
        rule_data["error_counter"] = 0  # 重置錯誤計數器
        self.photo_check_failed = False  # 重置全域錯誤旗標（如果本輪成功）
        self.failed_rule_id = -1

        self.log_message(f"規則 #{rule_num}: 檔案處理流程完成。")

    except Exception as e:
        # 如果在處理過程中發生任何錯誤（如磁碟滿、權限不足）
        error_msg = f"處理過程中發生錯誤: {str(e)}"
        self.log_message(f"規則 #{rule_num}: {error_msg}", "ERROR")
        self._handle_processing_error(rule_data, error_msg)
        return

    finally:
        # 無論成功與否，都刷新界面顯示
        self.refresh_rule_treeview()


def _handle_processing_error(self, rule_data, error_msg):
    """集中處理錯誤狀態更新（異常處理模組的初步實現）"""
    rule_id = rule_data["id"]
    rule_data["status"] = "異常"
    rule_data["last_error"] = error_msg
    # 錯誤計數器增加
    rule_data["error_counter"] = rule_data.get("error_counter", 0) + 1
    self.log_message(
        f"規則 #{rule_id} 錯誤計數器增加至: {rule_data['error_counter']}"
    )

    # 設定全域旗標（供Tab1-3讀取）
    self.photo_check_failed = True
    self.failed_rule_id = rule_id

    # ====== 關鍵修正：立即嘗試從備份還原檔案 ======
    # 先執行還原操作
    restore_success = self._restore_from_backup(rule_data)

    # 根據還原結果，可以微調狀態訊息（可選）
    if restore_success:
        rule_data["status"] = "異常 (已嘗試還原)"
    # ============================================

    # 最後刷新介面
    self.refresh_rule_treeview()

    # 注意：這個方法不再需要返回值，因為呼叫者會在呼叫後直接 `return`


def _restore_from_backup(self, rule_data):
    """從備份資料夾還原檔案到最終目的地（根據錯誤計數器奇偶性）"""
    rule_id = rule_data["id"]

    # ====== 核心修復：更精確的備份路徑計算 ======
    # 1. 檢查最終目的地
    output_path = rule_data.get("output_path", "").strip()
    if not output_path:
        self.log_message(
            f"[還原] 規則 #{rule_id}: 跳過。原因：「最終目的地」為空。",
            level="WARNING",
        )
        return False

    # 2. 獲取並標準化備份路徑 (將相對路徑 ./IMG 轉為絕對路徑)
    raw_backup_path = rule_data.get("backup_path", "./IMG")
    # 如果使用者輸入的是相對路徑，則基於主程式檔案位置進行解析
    if not os.path.isabs(raw_backup_path):
        # 取得當前 .pyw 檔案所在的目錄
        base_dir = os.path.dirname(os.path.abspath(__file__))
        backup_path = os.path.normpath(os.path.join(base_dir, raw_backup_path))
    else:
        backup_path = raw_backup_path

    if not os.path.isdir(backup_path):
        self.log_message(
            f"[還原] 規則 #{rule_id}: 跳過。原因：備份資料夾不存在「{backup_path}」。",
            level="ERROR",
        )
        return False

    # 3. 構建備份檔名
    # ====== 【關鍵修正開始】決定用於尋找備份和還原的“基礎檔案名” ======
    # 優先使用 source_path 中的實際名稱，如果沒有則使用記錄的 source_file
    source_path = rule_data.get("source_path", "")
    if source_path and os.path.basename(source_path):
        # 從完整來源路徑提取實際檔名，如 'ABC.jpg'
        actual_filename = os.path.basename(source_path)
    else:
        # 降級方案：使用規則中記錄的檔案名
        actual_filename = rule_data.get("source_file", f"Cam{rule_id}.jpg")

    filename_without_ext = os.path.splitext(actual_filename)[0]  # 如 'ABC'
    file_ext = os.path.splitext(actual_filename)[1] or ".jpg"
    # ====== 【關鍵修正結束】 ======

    error_counter = rule_data.get("error_counter", 0)
    # 根據奇偶性決定首要嘗試的備份後綴
    primary_suffix = "-s" if (error_counter % 2 == 1) else "-o"
    secondary_suffix = "-o" if primary_suffix == "-s" else "-s"  # 備用後綴

    # 4. 嘗試尋找備份檔案 (首選 -> 備用)
    backup_found = None
    for suffix in [primary_suffix, secondary_suffix]:
        test_filename = f"{filename_without_ext}{suffix}{file_ext}"
        test_path = os.path.join(backup_path, test_filename)
        if os.path.exists(test_path):
            backup_found = (test_path, suffix)
            break

    if not backup_found:
        self.log_message(
            f"[還原] 規則 #{rule_id}: 跳過。原因：在「{backup_path}」下找不到任何備份檔案 (*-o.jpg 或 *-s.jpg)。",
            level="ERROR",
        )
        return False

    backup_file_path, used_suffix = backup_found
    backup_type = "縮放版(-s)" if used_suffix == "-s" else "原始版(-o)"

    # 5. 執行還原 (複製)
    target_file_path = os.path.join(
        output_path, actual_filename
    )  # 使用 actual_filename
    try:
        import shutil

        # 確保目的資料夾存在
        os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
        shutil.copy2(backup_file_path, target_file_path)
        self.log_message(
            f"[還原] 規則 #{rule_id}: 成功！已將「{backup_type}」備份還原至「{target_file_path}」",
            level="INFO",
        )
        # 還原成功後，可更新狀態為“已還原”，但保留錯誤計數器
        rule_data["status"] = "已從備份還原"
        return True
    except Exception as e:
        self.log_message(
            f"[還原] 規則 #{rule_id}: 失敗。原因：複製檔案時出錯「{e}」。",
            level="ERROR",
        )
        return False


def save_tab4_config(self):
    """將當前處理原則、排程設定與 UI 狀態保存到 Pic_Process.dat"""
    import json

    config_path = "Pic_Process.dat"
    try:
        # 準備要保存的資料
        data_to_save = {
            "processing_rules": self.processing_rules,
            "schedule_minutes": getattr(
                self, "schedule_minutes", []
            ),  # 安全地获取，如果属性不存在则返回空列表
            "global_timer_interval_minutes": getattr(
                self, "global_timer_interval_minutes", 10
            ),  # ====== 新增：保存全局定時器間隔 ======
            "ui_state": {
                # 保存TAB4規則列表的欄位寬度
                "tab4_column_widths": self._get_tab4_column_widths()
            },
            "_metadata": {
                "save_time": datetime.now().isoformat(),
                "version": "1.0",
            },
        }
        # 使用 json.dump 寫入
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        self.log_message(f"設定已保存至 {config_path}")
    except Exception as e:
        self.log_message(f"保存設定檔時發生錯誤: {e}", level="ERROR")


def load_tab4_config(self):
    """從 Pic_Process.dat 載入處理原則、排程設定與 UI 狀態"""
    import json

    config_path = "Pic_Process.dat"
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 1. 載入處理原則
            loaded_rules = data.get("processing_rules", {})
            self.processing_rules = loaded_rules

            # 2. 載入排程分鐘列表
            self.schedule_minutes = data.get("schedule_minutes", [])
            self.global_timer_interval_minutes = data.get(
                "global_timer_interval_minutes", 10
            )  # ====== 新增：載入全局定時器間隔 ======

            # ====== 新增：更新TAB4介面上的輸入框顯示 ======
            # 檢查UI輸入框元件和其關聯的變數是否存在
            if (
                hasattr(self, "timer_interval_var")
                and self.timer_interval_var is not None
            ):
                # 將載入的數值（浮點數）轉為字串，設定給輸入框變數
                self.timer_interval_var.set(
                    str(self.global_timer_interval_minutes))

            self.log_message(
                f"[設定載入] 定時器間隔已設為: {self.global_timer_interval_minutes} 分鐘",
                level="DEBUG",
            )
            # ==========================================

            # 3. 載入UI狀態（Treeview欄位寬度）
            if "ui_state" in data and hasattr(self, "rule_tree"):
                ui_state = data["ui_state"]
                # 載入TAB4規則列表的欄寬
                saved_widths = ui_state.get("tab4_column_widths", {})
                columns = self.rule_tree["columns"]
                for col in columns:
                    if col in saved_widths:
                        self.rule_tree.column(col, width=saved_widths[col])

            # 4. 計算下一個可用的規則編號
            if self.processing_rules:
                try:
                    max_id = max(
                        rule["id"]
                        for rule in self.processing_rules.values()
                        if isinstance(rule, dict) and "id" in rule
                    )
                    self.next_rule_number = max_id + 1
                except ValueError:
                    self.next_rule_number = len(self.processing_rules) + 1
            else:
                self.next_rule_number = 1

            # 5. 刷新Treeview顯示
            if hasattr(self, "rule_tree") and self.rule_tree.winfo_exists():
                self.refresh_rule_treeview()
            self.log_message(
                f"設定檔載入成功：{len(self.processing_rules)} 個處理原則。"
            )
        else:
            self.log_message(
                "未找到設定檔 Pic_Process.dat，將使用初始設定。", level="INFO"
            )
    except json.JSONDecodeError:
        self.log_message(
            "錯誤：設定檔 Pic_Process.dat 格式損壞，無法讀取。", level="ERROR"
        )
    except Exception as e:
        self.log_message(f"載入設定檔時發生未知錯誤: {e}", level="ERROR")


def _get_tab4_column_widths(self):
    """ 獲取TAB4規則列表Treeview當前的欄位寬度 """
    if not hasattr(self, "rule_tree"):
        return {}
    widths = {}
    for col in self.rule_tree["columns"]:
        widths[col] = self.rule_tree.column(col, "width")
    return widths
