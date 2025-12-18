import tkinter as tk
from tkinter import ttk, scrolledtext, Menu, filedialog, messagebox
import os
from datetime import datetime  # 修改：增加timedelta
import threading  # 新增：用于线程安全
from PIL import Image  # 确保PIL（Pillow库）已导入，用于图片处理
import create_tab1_content
import create_tab2_content
import create_tab3_content
import create_tab4_content
from device_manager import (
    clear_edit_inputs,
    load_config,
    save_config,
    show_normal_operation,
)

class BatchLikeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("設備管理程式")
        self.root.geometry("800x600")

        # 設定樣式
        self.style = ttk.Style()
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TButton", padding=3)
        self.style.configure("TLabel", background="#f0f0f0")
        self.style.configure("Border.TFrame", background="#e0e0e0")  # 深灰色背景

        # 配置檔路徑
        self.config_file = "Iow_item_config.ini"

        # Log檔案設定
        self.log_file = "system_log.txt"
        self.max_log_size = 100 * 1024  # 100KB (可調整為 100K, 300K, 5MB 等)

        # 欄位寬度記憶
        self.column_widths = {
            "站名": 120,
            "RTU ID": 80,
            "UUID": 300,
            "類型": 70,
            "延遲(mS)": 80,
            "啟用/停止": 80,
        }

        # 編輯狀態變數
        self.edit_mode = False  # 是否處於編輯模式
        self.editing_item = None  # 正在編輯的項目ID
        self.ui_mode = "normal"  # normal, add, edit

        # 創建下拉選單變數
        self.function_var = tk.StringVar()

        # ====== 新增：TAB4相關變數（必須在create_widgets之前定義）======
        # Tab4：照片處理原則相關變數
        self.processing_rules = {}  # 儲存所有處理原則，key為rule_id
        self.next_rule_number = 1  # 用於生成連續編號
        self.rule_name_set = set()  # 儲存所有原則名稱，用於檢查重複

        # 全局定時器變數
        self.global_timer_interval_minutes = 10  # 全局定時器間隔（分鐘），默認10分鐘
        self.global_timer_id = None  # 用於控制tkinter的定時器ID
        self.is_processing_cycle = False  # 標誌當前是否正在執行一輪處理

        # RAM日誌系統變數
        self.ram_log_buffer = []  # 儲存Log條目的列表（在RAM中）
        self.max_log_buffer_size = 100 * 1024  # 最大 100 KB (您指定的值)
        self.current_buffer_size = 0  # 當前緩衝區佔用字節數
        self.log_ui_buffer = []  # UI更新緩衝（用於批次更新）
        self.log_batch_delay = 100  # UI批次更新延遲(毫秒)
        self.pending_ui_update = False  # 防止重複排程標誌

        # 全域狀態旗標
        self.photo_check_failed = False  # 照片檢查失敗旗標
        self.failed_rule_id = -1  # 記錄觸發異常的原則編號
        # ====== 新增：排程設定 ======
        self.schedule_minutes = []  # 用於儲存每小時執行的分鐘列表，例如 [2, 7, 11, 19]
        # ====== TAB4變數定義結束 ======

        self.create_widgets()
        load_config()
        self.load_tab4_config()

        # 初始化log檔案
        self.init_log_file()

    def init_log_file(self):
        """初始化log檔案"""
        try:
            # 檢查log檔案大小，如果超過限制則清空
            if os.path.exists(self.log_file):
                file_size = os.path.getsize(self.log_file)
                if file_size > self.max_log_size:
                    # 備份舊log檔案
                    backup_file = f"{self.log_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.rename(self.log_file, backup_file)
                    self.log_to_file(
                        f"Log檔案超過 {self.max_log_size/1024}KB，已備份並重新開始"
                    )
        except Exception as e:
            print(f"初始化log檔案時發生錯誤: {e}")

    def create_widgets(self):
        # 創建Notebook（標籤頁容器）放在最頂部
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        # 創建第一個標籤頁 - 設備列表
        self.tab1 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text="設備列表")
        create_tab1_content()

        # 創建第二個標籤頁 - 通訊設定
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab2, text="通訊設定")
        create_tab2_content()

        # 創建第三個標籤頁 - 系統設定
        self.tab3 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab3, text="系統設定")
        create_tab3_content()

        # 創建第四個標籤頁 - 照片處理
        self.tab4 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab4, text="照片處理")
        create_tab4_content()

        # 綁定Tab切換事件
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # 第三個框架 - 系統日誌（全局，在Notebook下方）
        self.log_frame = ttk.Frame(self.root, height=150)
        self.log_frame.pack(fill=tk.X, padx=10, pady=10)
        self.log_frame.pack_propagate(False)

        self.create_log_frame()

    def start_add_device(self):
        """最小化实现，仅用于保证程序启动"""
        print("DEBUG: start_add_device 占位方法被调用")
        # 暂无实际功能，后续可替换

    def create_function_menu(self, parent_frame):
        """創建功能選單 - 已增加關閉功能表選項"""
        # 功能選項
        functions = [
            ("新增設備", self.start_add_device),
            ("匯入設定", self.import_config),
            ("匯出設定", self.export_config),
            ("刪除設備", self.delete_device),
            ("清空列表", self.clear_list),
            ("測試連線", self.test_connection),
            ("儲存設定", self.save_config),
            ("關閉功能表", self.close_function_menu),  # 使用專用函數處理
        ]

        # 創建下拉選單
        function_names = [name for name, _ in functions]
        self.function_combo = ttk.Combobox(
            parent_frame,
            textvariable=self.function_var,
            values=function_names,
            state="readonly",
            width=12,
        )
        self.function_combo.pack(side=tk.RIGHT)
        self.function_combo.set("功能選單")

        # 綁定選擇事件
        self.function_combo.bind("<<ComboboxSelected>>", self.on_function_selected)

        # 存儲功能映射
        self.function_map = dict(functions)

    def close_function_menu(self):
        """關閉功能表的專用處理函數"""
        # 如果當前是編輯模式，恢復到正常模式
        if self.ui_mode != "normal":
            self.cancel_edit()
        # 不執行其他操作，只記錄日誌
        self.log("功能表已關閉")

    def on_function_selected(self, event):
        """處理功能選單選擇事件 - 已修正關閉功能表行為"""
        selected = self.function_var.get()

        # 檢查是否為有效選擇
        if selected not in self.function_map:
            self.function_combo.set("功能選單")
            return

        func = self.function_map[selected]

        if callable(func):
            try:
                func()
            except Exception as e:
                self.log(f"執行功能 '{selected}' 時發生錯誤: {str(e)}")
                messagebox.showerror("錯誤", f"執行功能時發生錯誤:\n{str(e)}")
        else:
            self.log(f"錯誤: 功能 '{selected}' 未實現")

        # 重置選單顯示
        self.function_combo.set("功能選單")

        # 移除下拉選單的焦點，避免持續顯示選項
        self.root.focus_set()

        # 取消下拉選單的綁定狀態
        self.root.after(50, lambda: self.function_combo.selection_clear())


    def on_rule_tree_click(self, event):
        """
        處理規則Treeview的點擊事件
        主要用於點擊「狀態」欄位時切換啟用/停用
        """
        # 獲取點擊位置
        region = self.rule_tree.identify_region(event.x, event.y)

        if region == "cell":
            # 獲取點擊的列和行
            column = self.rule_tree.identify_column(event.x)
            item = self.rule_tree.identify_row(event.y)

            # 如果點擊的是第3列（狀態欄）
            if item and column == "#3":
                # 這裡可以實現狀態切換邏輯
                # 暫時先記錄到日誌，後續完善
                self.log("點擊了規則狀態欄位（功能待實現）")

    def on_rule_tree_double_click(self, event):
        """
        處理規則Treeview的雙擊事件
        用於編輯選中的規則
        """
        selection = self.rule_tree.selection()
        if selection:
            # 暫時先記錄到日誌，後續完善
            self.log("雙擊了規則（編輯功能待實現）")

    def add_photo_rule(self):
        """新增照片處理規則"""
        self.log("新增規則功能待實現")

    def export_rules(self):
        """匯出規則設定"""
        self.log("匯出規則功能待實現")

    def import_rules(self):
        """匯入規則設定"""
        self.log("匯入規則功能待實現")

    def load_rules_from_config(self):
        """
        從設定檔載入處理規則
        目前為空實現，後續完善
        """
        # 這裡先不實際載入，僅初始化空字典
        self.processing_rules = {}
        self.next_rule_number = 1
        self.rule_name_set = set()

        # 更新Treeview顯示（目前為空）
        for item in self.rule_tree.get_children():
            self.rule_tree.delete(item)

        # 更新狀態標籤
        if hasattr(self, "tab4_status_var"):
            self.tab4_status_var.set("已載入 0 條處理原則")

    def create_log_frame(self):
        """創建日誌框架"""
        # 建立日誌文字框
        self.log_text = scrolledtext.ScrolledText(
            self.log_frame, wrap=tk.WORD, width=80, height=8
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 加入右鍵選單
        self.context_menu = Menu(self.log_text, tearoff=0)
        self.context_menu.add_command(label="全選", command=self.select_all)
        self.context_menu.add_command(label="複製", command=self.copy_text)
        self.context_menu.add_command(label="清除", command=self.clear_log)
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="匯出Log到檔案", command=self.export_log_to_file
        )
        self.context_menu.add_command(label="查看Log檔案", command=self.view_log_file)

        # 綁定右鍵事件
        self.log_text.bind("<Button-3>", self.show_context_menu)

        # 初始日誌訊息
        self.log("系統啟動成功")

    def fill_edit_inputs(self, values):
        """將Treeview中的值填入編輯輸入欄位 - 更新為新的欄位順序"""
        # 清空輸入欄位
        clear_edit_inputs()

        # 新的欄位順序：站名, RTU ID, UUID, 類型, 延遲(mS), 啟用/停止
        if len(values) > 0:
            self.station_name_entry.insert(0, values[0])

        if len(values) > 1:
            # 從Treeview的顯示格式中提取十進位值
            rtu_display = values[1]
            dec_value = self.extract_decimal_from_display(rtu_display)
            if dec_value is not None:
                self.rtu_id_entry.insert(0, str(dec_value))
                self.update_rtu_hex_display()

        if len(values) > 2:
            uuid_val = values[2]
            self.uuid_entry.insert(0, uuid_val)

        if len(values) > 3:
            # 設置類型
            self.type_var.set(values[3])

        if len(values) > 4 and values[4]:
            self.delay_entry.delete(0, tk.END)
            self.delay_entry.insert(0, values[4])

        if len(values) > 5:
            # 從顯示文本中提取啟用/停止狀態
            status_display = values[5]
            if "✓" in status_display:  # 如果顯示文本中有✓，表示啟用
                self.enable_var.set(True)
            else:
                self.enable_var.set(False)

    def extract_decimal_from_display(self, display_str):
        """從顯示字串中提取十進位值"""
        if not display_str:
            return None

        try:
            # 顯示格式為 "十進位 (十六進位參考)"
            # 提取括號前的數字部分
            import re

            match = re.match(r"^(\d+)\s*\(", display_str)
            if match:
                return int(match.group(1))

            # 如果沒有括號，嘗試直接轉換
            return int(display_str)
        except (ValueError, AttributeError):
            return None

    def on_tab_changed(self, event):
        """處理Tab切換事件"""
        current_tab = self.notebook.index(self.notebook.select())

        # 如果切換到非設備列表Tab，確保回到正常模式
        if current_tab != 0:
            if self.ui_mode != "normal":
                show_normal_operation()
                self.log(f"已切換到Tab{current_tab + 1}，操作區域恢復正常模式")

    def start_add_device(self):
        """開始新增設備模式"""
        self.show_edit_operation(mode="add")
        self.log("進入新增設備模式")

    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def select_all(self):
        self.log_text.tag_add(tk.SEL, "1.0", tk.END)
        self.log_text.mark_set(tk.INSERT, "1.0")
        self.log_text.see(tk.INSERT)
        return "break"

    def copy_text(self):
        try:
            self.root.clipboard_clear()
            text = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_append(text)
        except tk.TclError:
            pass

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"

        # 顯示在GUI中
        self.log_text.insert(tk.END, f"{log_message}\n")
        self.log_text.see(tk.END)

        # 儲存到檔案
        self.log_to_file(log_message)

    def log_to_file(self, message):
        """將log訊息寫入檔案"""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{message}\n")

            # 檢查檔案大小，如果超過限制則壓縮
            self.check_log_file_size()
        except Exception as e:
            print(f"寫入log檔案時發生錯誤: {e}")

    def check_log_file_size(self):
        """檢查log檔案大小，如果超過限制則壓縮"""
        try:
            if os.path.exists(self.log_file):
                file_size = os.path.getsize(self.log_file)
                if file_size > self.max_log_size:
                    # 備份舊log檔案
                    backup_file = f"{self.log_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.rename(self.log_file, backup_file)

                    # 保留最近的部分內容
                    try:
                        with open(backup_file, "r", encoding="utf-8") as f:
                            lines = f.readlines()

                        # 保留最後1000行
                        keep_lines = lines[-1000:] if len(lines) > 1000 else lines

                        with open(self.log_file, "w", encoding="utf-8") as f:
                            f.writelines(keep_lines)

                        self.log_text.insert(
                            tk.END,
                            f"[系統] Log檔案超過 {self.max_log_size/1024}KB，已壓縮並備份\n",
                        )
                        self.log_to_file(
                            f"Log檔案超過 {self.max_log_size/1024}KB，已壓縮並備份為 {backup_file}"
                        )
                    except:
                        # 如果讀取失敗，創建新檔案
                        with open(self.log_file, "w", encoding="utf-8") as f:
                            f.write(
                                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Log檔案重新開始\n"
                            )
        except Exception as e:
            print(f"檢查log檔案大小時發生錯誤: {e}")

    def export_log_to_file(self):
        """匯出當前log到檔案"""
        file_path = filedialog.asksaveasfilename(
            title="儲存Log檔案",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"log_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if file_path:
            try:
                log_content = self.log_text.get(1.0, tk.END)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(log_content)
                self.log(f"Log已匯出至 {file_path}")
            except Exception as e:
                messagebox.showerror("錯誤", f"匯出Log時發生錯誤:\n{str(e)}")

    def view_log_file(self):
        """查看log檔案內容"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 在新視窗中顯示log檔案內容
                log_window = tk.Toplevel(self.root)
                log_window.title(f"Log檔案內容 - {self.log_file}")
                log_window.geometry("800x600")

                text_widget = scrolledtext.ScrolledText(log_window, wrap=tk.WORD)
                text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                text_widget.insert(1.0, content)
                text_widget.config(state=tk.DISABLED)

                # 添加關閉按鈕
                close_btn = ttk.Button(
                    log_window, text="關閉", command=log_window.destroy
                )
                close_btn.pack(pady=10)
            else:
                messagebox.showinfo("資訊", "Log檔案不存在")
        except Exception as e:
            messagebox.showerror("錯誤", f"讀取Log檔案時發生錯誤:\n{str(e)}")

    def manage_log_file(self):
        """管理log檔案"""
        try:
            file_size = 0
            if os.path.exists(self.log_file):
                file_size = os.path.getsize(self.log_file)

            # 更新最大log大小
            try:
                new_size = int(self.log_size_var.get()) * 1024
                self.max_log_size = new_size
                self.log(f"Log檔案大小限制已設定為 {self.log_size_var.get()}KB")
            except:
                pass

            messagebox.showinfo(
                "Log檔案資訊",
                f"Log檔案: {self.log_file}\n"
                f"目前大小: {file_size/1024:.2f}KB\n"
                f"限制大小: {self.max_log_size/1024}KB\n"
                f"超過限制時會自動壓縮並備份",
            )
        except Exception as e:
            messagebox.showerror("錯誤", f"管理Log檔案時發生錯誤:\n{str(e)}")

    def import_config(self):
        file_path = filedialog.askopenfilename(
            title="選擇要匯入的設定檔",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
        )
        if file_path:
            self.config_file = file_path
            load_config()
            self.log(f"已從 {file_path} 匯入設定")

    def export_config(self):
        file_path = filedialog.asksaveasfilename(
            title="儲存設定檔",
            defaultextension=".ini",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
            initialfile="Iow_item_config_backup.ini",
        )
        if file_path:
            self.config_file = file_path
            save_config()

    def delete_device(self):
        selected = self.device_tree.selection()
        if selected:
            for item in selected:
                device_name = self.device_tree.item(item)["values"][0]
                self.device_tree.delete(item)
                self.log(f"已刪除設備: {device_name}")
        else:
            self.log("請先選擇要刪除的設備")

    def clear_list(self):
        for item in self.device_tree.get_children():
            self.device_tree.delete(item)
        self.log("已清空設備列表")

    def test_connection(self):
        self.log("測試連線功能（待實現）")

    def test_communication(self):
        """測試通訊連線"""
        if hasattr(self, "protocol_var"):
            protocol = self.protocol_var.get()
            port = self.port_entry.get() if hasattr(self, "port_entry") else "COM1"
            baudrate = (
                self.baudrate_var.get() if hasattr(self, "baudrate_var") else "9600"
            )

            self.log(f"測試通訊連線: 協定={protocol}, 埠={port}, 鮑率={baudrate}")
            messagebox.showinfo(
                "通訊測試", f"正在測試 {protocol} 通訊...\n埠: {port}\n鮑率: {baudrate}"
            )



    # ====== 新增：RAM日誌系統方法 ======
    def log_message(self, message, level="INFO"):
        """將日誌訊息存入RAM緩衝區並安排UI批次更新"""
        # 1. 建立時間戳記
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} [{level}] - {message}"

        # 2. 存入RAM緩衝區（計算字節大小）
        entry_size = len(log_entry.encode("utf-8"))
        self.ram_log_buffer.append(log_entry)
        self.current_buffer_size += entry_size

        # 3. 限制緩衝區大小（100KB限制）
        while (
            self.current_buffer_size > self.max_log_buffer_size and self.ram_log_buffer
        ):
            removed_entry = self.ram_log_buffer.pop(0)
            self.current_buffer_size -= len(removed_entry.encode("utf-8"))

        # 4. 加入UI更新緩衝
        self.log_ui_buffer.append(log_entry)

        # 5. 觸發批次UI更新（防抖動）
        if not self.pending_ui_update:
            self.pending_ui_update = True
            self.root.after(self.log_batch_delay, self.flush_log_to_ui)

    def flush_log_to_ui(self):
        """將緩衝的日誌批次更新到UI顯示"""
        if not self.log_ui_buffer:
            self.pending_ui_update = False
            return

        # 單次操作更新所有緩衝內容
        text_to_insert = "\n".join(self.log_ui_buffer) + "\n"

        # 檢查日誌文字元件是否存在
        if hasattr(self, "log_text") and self.log_text.winfo_exists():
            self.log_text.insert(tk.END, text_to_insert)

            # 限制顯示行數（最多500行）
            line_count = int(self.log_text.index("end-1c").split(".")[0])
            if line_count > 500:
                excess = line_count - 500
                self.log_text.delete(1.0, f"{excess+1}.0")

            self.log_text.see(tk.END)  # 自動滾動到最新

        self.log_ui_buffer.clear()
        self.pending_ui_update = False


    def on_timer_interval_changed(self, event=None):
        """ 當定時器間隔輸入框內容改變且失去焦點時，更新變數並儲存設定。"""
        try:
            # 1. 從介面取得新值
            input_value = self.timer_interval_var.get().strip()
            if not input_value:
                return  # 如果為空則不處理

            # 2. 轉換並驗證輸入值
            new_interval = float(input_value)
            if new_interval <= 0:
                messagebox.showerror("輸入錯誤", "定時器間隔必須大於0分鐘。")
                # 恢復為原值
                self.timer_interval_var.set(str(self.global_timer_interval_minutes))
                return

            # 3. 更新內部變數
            old_interval = self.global_timer_interval_minutes
            self.global_timer_interval_minutes = new_interval

            # 4. 儲存到檔案
            self.save_tab4_config()

            # 5. 記錄日誌（可選）
            if old_interval != new_interval:
                self.log_message(
                    f"定時器間隔已從 {old_interval} 分鐘更改為 {new_interval} 分鐘"
                )

        except ValueError:
            # 如果輸入的不是有效數字，恢復為原值
            messagebox.showerror("輸入錯誤", "請輸入有效的數字（例如：5、10.5）。")
            self.timer_interval_var.set(str(self.global_timer_interval_minutes))


if __name__ == "__main__":
    root = tk.Tk()
    app = BatchLikeApp(root)

    # 關閉視窗時自動儲存設定
    def on_closing():
        app.save_config()
        app.save_tab4_config()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
