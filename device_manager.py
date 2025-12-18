import configparser
import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from utils import format_rtu_id, normalize_uuid, validate_uuid

def create_normal_operation(self):
    """創建正常模式的操作區域"""
    # 正常模式的框架
    self.normal_op_frame = ttk.Frame(self.operation_frame)

    # 左側：標題
    title_label = ttk.Label(
        self.normal_op_frame,
        text="設備屬性列表",
        background="#e0e0e0",
        font=("Arial", 9, "bold"),
    )
    title_label.pack(side=tk.LEFT, padx=5, pady=10)

    # 右側：功能選單
    self.create_function_menu(self.normal_op_frame)


def create_edit_operation(self):
    """創建編輯模式的操作區域 - 已修改為類型下拉選單和加長UUID欄位"""
    # 編輯模式的框架
    self.edit_op_frame = ttk.Frame(self.operation_frame)

    # 第一行：主要輸入控件
    row1_frame = ttk.Frame(self.edit_op_frame)
    row1_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

    # 站名輸入
    ttk.Label(row1_frame, text="站名:").pack(side=tk.LEFT, padx=(0, 2))
    self.station_name_entry = ttk.Entry(row1_frame, width=12)
    self.station_name_entry.pack(side=tk.LEFT, padx=(0, 10))

    # RTU ID 輸入 - 十進位輸入
    ttk.Label(row1_frame, text="RTU ID (Dec):").pack(side=tk.LEFT, padx=(0, 2))
    self.rtu_id_entry = ttk.Entry(row1_frame, width=6)
    self.rtu_id_entry.pack(side=tk.LEFT, padx=(0, 10))

    # 十六進位顯示標籤
    self.rtu_hex_label = ttk.Label(
        row1_frame, text="十六進位: -", foreground="blue")
    self.rtu_hex_label.pack(side=tk.LEFT, padx=(0, 10))

    # 綁定RTU ID輸入變化事件
    self.rtu_id_entry.bind("<KeyRelease>", self.update_rtu_hex_display)

    # UUID 輸入 - 增加寬度到40字元
    ttk.Label(row1_frame, text="UUID:").pack(side=tk.LEFT, padx=(0, 2))
    self.uuid_entry = ttk.Entry(row1_frame, width=40)
    self.uuid_entry.pack(side=tk.LEFT, padx=(0, 10))

    # 第二行：類型選擇和延遲
    row2_frame = ttk.Frame(self.edit_op_frame)
    row2_frame.pack(fill=tk.X, padx=5, pady=(2, 0))

    # 類型選擇（取代三個勾選框）
    ttk.Label(row2_frame, text="類型:").pack(side=tk.LEFT, padx=(0, 2))
    self.type_var = tk.StringVar()
    self.type_combo = ttk.Combobox(
        row2_frame,
        textvariable=self.type_var,
        values=["水位", "雨量", "圖片"],
        width=8,
        state="readonly",
    )
    self.type_combo.pack(side=tk.LEFT, padx=(0, 10))

    # 延遲輸入框
    ttk.Label(row2_frame, text="延遲").pack(side=tk.LEFT, padx=(0, 2))
    self.delay_entry = ttk.Entry(row2_frame, width=4)
    self.delay_entry.insert(0, "50")  # 設定預設值50
    self.delay_entry.pack(side=tk.LEFT, padx=(0, 2))
    ttk.Label(row2_frame, text="mS").pack(side=tk.LEFT, padx=(0, 10))

    # 啟用/停止選項 - 保留選擇框在編輯模式中
    self.enable_var = tk.BooleanVar(value=True)
    ttk.Label(row2_frame, text="狀態:").pack(side=tk.LEFT, padx=(0, 2))
    self.enable_check = ttk.Checkbutton(
        row2_frame, text="啟用", variable=self.enable_var
    )
    self.enable_check.pack(side=tk.LEFT, padx=(0, 10))

    # 第三行：按鈕
    row3_frame = ttk.Frame(self.edit_op_frame)
    row3_frame.pack(fill=tk.X, padx=5, pady=(5, 5))

    # 更新/新增確定按鈕
    self.edit_confirm_btn = ttk.Button(
        row3_frame, text="更新確定", command=self.add_or_update_device, width=10
    )
    self.edit_confirm_btn.pack(side=tk.LEFT, padx=(0, 5))

    # 取消編輯按鈕
    self.edit_cancel_btn = ttk.Button(
        row3_frame, text="取消編輯", command=self.cancel_edit, width=10
    )
    self.edit_cancel_btn.pack(side=tk.LEFT, padx=(0, 10))

    # 功能選單
    self.create_function_menu(row3_frame)


def update_rtu_hex_display(self, event=None):
    """更新RTU ID的十六進位顯示（輸入十進位，顯示十六進位參考）"""
    try:
        dec_str = self.rtu_id_entry.get().strip()
        if not dec_str:
            self.rtu_hex_label.config(text="十六進位: -", foreground="blue")
            return

        # 檢查是否為有效十進位
        if not dec_str.isdigit():
            self.rtu_hex_label.config(text="十六進位: 無效", foreground="red")
            return

        # 轉換為整數
        decimal_value = int(dec_str)

        # 檢查範圍
        if decimal_value < 0 or decimal_value > 65535:
            self.rtu_hex_label.config(text="十六進位: 超出範圍", foreground="red")
            return

        # 轉換為十六進位顯示
        if decimal_value <= 0xFF:  # 0-255
            hex_str = f"0x{decimal_value:02X}"
        else:  # 256-65535
            hex_str = f"0x{decimal_value:04X}"

        self.rtu_hex_label.config(text=f"十六進位: {hex_str}", foreground="green")
    except ValueError:
        self.rtu_hex_label.config(text="十六進位: 無效", foreground="red")


def add_or_update_device(self):
    """新增或更新設備（根據編輯模式）"""
    if self.ui_mode == "add":
        self.add_device()
    elif self.ui_mode == "edit":
        self.update_device()


def add_device(self):
    """新增設備 - 更新為新的欄位順序和類型選擇"""
    if not hasattr(self, "station_name_entry"):
        self.log("錯誤: 輸入欄位未初始化")
        return

    station_name = self.station_name_entry.get()
    rtu_id_dec_str = self.rtu_id_entry.get()
    uuid_val = self.uuid_entry.get().upper()
    selected_type = self.type_var.get()  # 獲取選擇的類型
    delay_val = self.delay_entry.get()
    is_enabled = self.enable_var.get()

    # 驗證輸入
    validation_result = self.validate_input(
        station_name, rtu_id_dec_str, uuid_val, selected_type, delay_val
    )
    if not validation_result["valid"]:
        self.log(validation_result["message"])
        return

    # 轉換RTU ID為整數
    rtu_id_decimal = int(rtu_id_dec_str)

    # 格式化RTU ID顯示
    rtu_display = format_rtu_id(rtu_id_decimal)

    # UUID格式化為標準格式
    uuid_formatted = normalize_uuid(uuid_val)

    # 格式化啟用/停止顯示
    if is_enabled:
        status_display = "[✓] 啟用"
        status_tag = "enabled"
        status_log = "啟用"
    else:
        status_display = "[ ] 停止"
        status_tag = "disabled"
        status_log = "停止"

    # 加入到設備列表（新的欄位順序）
    self.device_tree.insert(
        "",
        tk.END,
        values=(
            station_name,
            rtu_display,
            uuid_formatted,
            selected_type,
            delay_val,
            status_display,
        ),
        tags=(status_tag,),
    )

    self.log(
        f"已新增設備: 站名={station_name}, RTU ID={rtu_id_decimal}, 類型={selected_type}, 狀態={status_log}"
    )

    # 清空輸入欄位並回到正常模式
    self.clear_edit_inputs()
    show_normal_operation()


def update_device(self):
    """更新現有設備 - 更新為新的欄位順序和類型選擇"""
    if not self.editing_item:
        self.log("錯誤: 沒有選擇要編輯的項目")
        return

    if not hasattr(self, "station_name_entry"):
        self.log("錯誤: 輸入欄位未初始化")
        return

    station_name = self.station_name_entry.get()
    rtu_id_dec_str = self.rtu_id_entry.get()
    uuid_val = self.uuid_entry.get().upper()
    selected_type = self.type_var.get()  # 獲取選擇的類型
    delay_val = self.delay_entry.get()
    is_enabled = self.enable_var.get()

    # 驗證輸入
    validation_result = self.validate_input(
        station_name, rtu_id_dec_str, uuid_val, selected_type, delay_val
    )
    if not validation_result["valid"]:
        self.log(validation_result["message"])
        return

    # 轉換RTU ID為整數
    rtu_id_decimal = int(rtu_id_dec_str)

    # 格式化RTU ID顯示
    rtu_display = format_rtu_id(rtu_id_decimal)

    # UUID格式化為標準格式
    uuid_formatted = normalize_uuid(uuid_val)

    # 格式化啟用/停止顯示
    if is_enabled:
        status_display = "[✓] 啟用"
        status_tag = "enabled"
        status_log = "啟用"
    else:
        status_display = "[ ] 停止"
        status_tag = "disabled"
        status_log = "停止"

    # 更新設備列表中的項目（新的欄位順序）
    self.device_tree.item(
        self.editing_item,
        values=(
            station_name,
            rtu_display,
            uuid_formatted,
            selected_type,
            delay_val,
            status_display,
        ),
        tags=(status_tag,),
    )

    self.log(
        f"已更新設備: 站名={station_name}, RTU ID={rtu_id_decimal}, 類型={selected_type}, 狀態={status_log}"
    )

    # 清空輸入欄位並回到正常模式
    self.clear_edit_inputs()
    show_normal_operation()


def validate_input(
    self, station_name, rtu_id_dec_str, uuid_val, selected_type, delay_val
):
    """驗證輸入數據 - 更新為包含類型驗證"""
    if not station_name or not rtu_id_dec_str or not uuid_val:
        return {"valid": False, "message": "錯誤: 站名、RTU ID 和 UUID 不能為空"}

    # RTU ID 驗證（十進位）
    if not rtu_id_dec_str.isdigit():
        return {"valid": False, "message": "錯誤: RTU ID 必須為有效的十進位數字"}

    try:
        rtu_id = int(rtu_id_dec_str)
        if rtu_id < 0 or rtu_id > 65535:
            return {"valid": False, "message": "錯誤: RTU ID 必須在 0-65535 範圍內"}
    except ValueError:
        return {"valid": False, "message": "錯誤: RTU ID 必須為有效的數字"}

    # 類型驗證
    if not selected_type or selected_type not in ["水位", "雨量", "圖片"]:
        return {"valid": False, "message": "錯誤: 必須選擇一個類型（水位、雨量或圖片）"}

    # UUID 驗證
    if not validate_uuid(uuid_val):
        return {
            "valid": False,
            "message": "錯誤: UUID 格式不正確\n可接受: 32位十六進位 或 標準格式 (8-4-4-4-12)",
        }

    if delay_val and not delay_val.isdigit():
        return {"valid": False, "message": "錯誤: 延遲時間必須為數字"}

    return {"valid": True, "message": ""}


def on_treeview_select(self, event):
    """處理Treeview選擇事件"""
    selection = self.device_tree.selection()
    if selection:
        item = self.device_tree.item(selection[0])
        values = item["values"]
        if values:
            self.log(f"選中設備: {values[0]} (RTU ID: {values[1]})")


def on_treeview_double_click(self, event):
    """處理Treeview雙擊事件"""
    selection = self.device_tree.selection()
    if not selection:
        return

    item_id = selection[0]
    item = self.device_tree.item(item_id)
    values = item["values"]

    if not values:
        return

    # 進入編輯模式
    self.editing_item = item_id
    self.show_edit_operation(mode="edit", values=values)

    self.log(f"進入編輯模式: {values[0]}")


def on_treeview_click(self, event):
    """處理Treeview點擊事件 - 用於切換啟用/停止狀態"""
    # 獲取點擊位置
    region = self.device_tree.identify_region(event.x, event.y)

    if region == "cell":
        # 獲取點擊的列和行
        column = self.device_tree.identify_column(event.x)
        item = self.device_tree.identify_row(event.y)

        if item and column == "#6":  # 第6列是"啟用/停止"
            # 獲取當前值
            values = list(self.device_tree.item(item, "values"))
            current_display = values[5]

            # 切換狀態
            if "✓" in current_display:  # 目前是啟用，切換為停止
                new_display = "[ ] 停止"
                new_tag = "disabled"
                new_status = "停止"
            else:  # 目前是停止，切換為啟用
                new_display = "[✓] 啟用"
                new_tag = "enabled"
                new_status = "啟用"

            # 更新Treeview
            values[5] = new_display
            self.device_tree.item(item, values=values, tags=(new_tag,))

            # 記錄日誌
            station_name = values[0]
            self.log(f"設備 {station_name} 狀態已切換為 {new_status}")


def cancel_edit(self):
    """取消編輯模式"""
    if self.ui_mode != "normal":
        self.log("已取消編輯")
        self.clear_edit_inputs()
        show_normal_operation()


def clear_edit_inputs(self):
    """清除編輯輸入欄位"""
    if hasattr(self, "station_name_entry"):
        self.station_name_entry.delete(0, tk.END)
    if hasattr(self, "rtu_id_entry"):
        self.rtu_id_entry.delete(0, tk.END)
    if hasattr(self, "uuid_entry"):
        self.uuid_entry.delete(0, tk.END)
    if hasattr(self, "delay_entry"):
        self.delay_entry.delete(0, tk.END)
        self.delay_entry.insert(0, "50")  # 重置時設為50

    # 重置十六進位顯示
    if hasattr(self, "rtu_hex_label"):
        self.rtu_hex_label.config(text="十六進位: -", foreground="blue")

    # 重置類型選擇
    if hasattr(self, "type_var"):
        self.type_var.set("")

    if hasattr(self, "enable_var"):


def show_normal_operation(self):
    """顯示正常模式的操作區域"""
    # 如果編輯模式框架存在，先隱藏
    if hasattr(self, 'edit_op_frame') and self.edit_op_frame:
        self.edit_op_frame.pack_forget()

    # 顯示正常模式框架
    self.normal_op_frame.pack(fill=tk.X, expand=True)
    self.ui_mode = "normal"
    self.edit_mode = False
    self.editing_item = None


def show_edit_operation(self, mode="edit", values=None):
    """顯示編輯模式的操作區域  mode: "edit" 編輯模式, "add" 新增模式  values: 編輯時的數據 """
    # 如果正常模式框架存在，先隱藏
    if hasattr(self, 'normal_op_frame') and self.normal_op_frame:
        self.normal_op_frame.pack_forget()

    # 如果編輯模式框架不存在，先創建
    if not hasattr(self, 'edit_op_frame') or not self.edit_op_frame:
        create_edit_operation()

    # 根據模式設定按鈕文字
    if mode == "add":
        self.edit_confirm_btn.config(text="新增確定")
        self.edit_mode = False
        self.editing_item = None
    else:
        self.edit_confirm_btn.config(text="更新確定")
        self.edit_mode = True

    # 填充數據（如果是編輯模式）
    if values:
        self.fill_edit_inputs(values)
    else:
        clear_edit_inputs()

    # 顯示編輯模式框架
    self.edit_op_frame.pack(fill=tk.X, expand=True)
    self.ui_mode = mode

def save_config(self):
    """儲存設定到INI檔案 - 更新為新的欄位順序"""
    try:
        config = configparser.ConfigParser()

        # 儲存欄位寬度
        config["COLUMN_WIDTHS"] = {}
        for col in self.device_tree["columns"]:
            width = self.device_tree.column(col, "width")
            config["COLUMN_WIDTHS"][col] = str(width)

        # 儲存設備數據（新的欄位順序）
        config["DEVICE_COUNT"] = {
            "count": str(len(self.device_tree.get_children()))
        }

        for i, item_id in enumerate(self.device_tree.get_children()):
            item = self.device_tree.item(item_id)
            values = item["values"]

            # 從顯示文本中提取啟用/停止狀態
            status_display = values[5]
            if "✓" in status_display:
                enabled = "啟用"
            else:
                enabled = "停止"

            section = f"DEVICE_{i+1:03d}"
            config[section] = {
                "station_name": values[0] if len(values) > 0 else "",
                "rtu_id": values[1] if len(values) > 1 else "",
                "uuid": values[2] if len(values) > 2 else "",
                "type": values[3] if len(values) > 3 else "",  # 類型
                "delay": values[4] if len(values) > 4 else "",
                "enabled": enabled,
            }

        # 儲存通訊設定（如果存在）
        if hasattr(self, "protocol_var"):
            config["COMMUNICATION"] = {
                "protocol": self.protocol_var.get(),
                "port": (
                    self.port_entry.get() if hasattr(self, "port_entry") else "COM1"
                ),
                "baudrate": (
                    self.baudrate_var.get()
                    if hasattr(self, "baudrate_var")
                    else "9600"
                ),
            }

        # 儲存系統設定（如果存在）
        if hasattr(self, "auto_save_var"):
            config["SYSTEM"] = {
                "auto_save": self.auto_save_var.get(),
                "log_level": (
                    self.log_level_var.get()
                    if hasattr(self, "log_level_var")
                    else "INFO"
                ),
            }

        # 儲存Log設定
        config["LOG_SETTINGS"] = {
            "max_log_size_kb": (
                self.log_size_var.get() if hasattr(self, "log_size_var") else "100"
            )
        }

        # 寫入檔案
        with open(self.config_file, "w", encoding="utf-8") as f:
            config.write(f)

        self.log(f"設定已儲存至 {self.config_file}")
        messagebox.showinfo("成功", f"設定已成功儲存至\n{self.config_file}")

    except Exception as e:
        self.log(f"儲存設定時發生錯誤: {str(e)}")
        messagebox.showerror("錯誤", f"儲存設定時發生錯誤:\n{str(e)}")


def load_config(self):
    """從INI檔案載入設定 - 更新為新的欄位順序並支援舊格式轉換"""
    try:
        if not os.path.exists(self.config_file):
            self.log(f"設定檔案 {self.config_file} 不存在，使用預設設定")
            return

        config = configparser.ConfigParser()
        config.read(self.config_file, encoding="utf-8")

        # 清空現有設備列表
        for item in self.device_tree.get_children():
            self.device_tree.delete(item)

        # 載入設備數據
        if "DEVICE_COUNT" in config:
            device_count = int(config["DEVICE_COUNT"]["count"])

            for i in range(1, device_count + 1):
                section = f"DEVICE_{i:03d}"
                if section in config:
                    device_data = config[section]

                    # 處理舊格式轉換（如果有water_level、rainfall、image欄位）
                    device_type = device_data.get("type", "")

                    # 如果沒有type欄位，檢查舊的三個布林欄位
                    if not device_type and (
                        "water_level" in device_data
                        or "rainfall" in device_data
                        or "image" in device_data
                    ):
                        # 舊格式轉換
                        if device_data.get("water_level", "").lower() == "是":
                            device_type = "水位"
                        elif device_data.get("rainfall", "").lower() == "是":
                            device_type = "雨量"
                        elif device_data.get("image", "").lower() == "是":
                            device_type = "圖片"

                    # RTU ID顯示格式轉換（如果有需要）
                    rtu_id_display = device_data.get("rtu_id", "")
                    if rtu_id_display.startswith("0x"):
                        try:
                            # 轉換舊格式到新格式
                            hex_str = rtu_id_display[2:]
                            decimal_value = int(hex_str, 16)
                            rtu_id_display = format_rtu_id(decimal_value)
                        except:
                            pass  # 如果轉換失敗，保持原樣

                    # 啟用/停止狀態處理
                    enabled = device_data.get("enabled", "啟用")
                    if enabled == "啟用":
                        status_display = "[✓] 啟用"
                        status_tag = "enabled"
                    else:
                        status_display = "[ ] 停止"
                        status_tag = "disabled"

                    # 添加到Treeview（新的欄位順序）
                    self.device_tree.insert(
                        "",
                        tk.END,
                        values=(
                            device_data.get("station_name", ""),
                            rtu_id_display,
                            device_data.get("uuid", ""),
                            device_type,  # 類型
                            device_data.get("delay", ""),
                            status_display,
                        ),
                        tags=(status_tag,),
                    )

        # 載入欄位寬度
        if "COLUMN_WIDTHS" in config:
            for col in self.device_tree["columns"]:
                if col in config["COLUMN_WIDTHS"]:
                    width = int(config["COLUMN_WIDTHS"][col])
                    self.device_tree.column(col, width=width)
                    self.column_widths[col] = width

        # 載入通訊設定
        if "COMMUNICATION" in config and hasattr(self, "protocol_var"):
            self.protocol_var.set(
                config["COMMUNICATION"].get("protocol", "MODBUS RTU")
            )
            if hasattr(self, "port_entry"):
                self.port_entry.delete(0, tk.END)
                self.port_entry.insert(
                    0, config["COMMUNICATION"].get("port", "COM1")
                )
            if hasattr(self, "baudrate_var"):
                self.baudrate_var.set(
                    config["COMMUNICATION"].get("baudrate", "9600")
                )

        # 載入系統設定
        if "SYSTEM" in config and hasattr(self, "auto_save_var"):
            self.auto_save_var.set(config["SYSTEM"].get("auto_save", "5"))
            if hasattr(self, "log_level_var"):
                self.log_level_var.set(
                    config["SYSTEM"].get("log_level", "INFO"))

        # 載入Log設定
        if "LOG_SETTINGS" in config and hasattr(self, "log_size_var"):
            log_size = config["LOG_SETTINGS"].get("max_log_size_kb", "100")
            self.log_size_var.set(log_size)
            self.max_log_size = int(log_size) * 1024

        self.log(f"設定已從 {self.config_file} 載入")

    except Exception as e:
        self.log(f"載入設定時發生錯誤: {str(e)}")



