import tkinter as tk
from tkinter import ttk, scrolledtext, Menu, filedialog, messagebox
import uuid
import configparser
import os
import re
from datetime import datetime, timedelta  # 修改：增加timedelta
import time         # 新增：用于time.sleep
import threading    # 新增：用于线程安全
import hashlib      # 用于计算文件哈希值
from PIL import Image  # 确保PIL（Pillow库）已导入，用于图片处理
from utils import calculate_file_hash


class BatchLikeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("設備管理程式")
        self.root.geometry("800x600")
        
        # 設定樣式
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TButton', padding=3)
        self.style.configure('TLabel', background='#f0f0f0')
        self.style.configure('Border.TFrame', background='#e0e0e0')  # 深灰色背景
        
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
            "啟用/停止": 80
        }
        
        # 編輯狀態變數
        self.edit_mode = False  # 是否處於編輯模式
        self.editing_item = None  # 正在編輯的項目ID
        self.ui_mode = "normal"  # normal, add, edit

        # 創建下拉選單變數
        self.function_var = tk.StringVar()

        # ====== 新增：TAB4相關變數（必須在create_widgets之前定義）======
        # Tab4：照片處理原則相關變數
        self.processing_rules = {}      # 儲存所有處理原則，key為rule_id
        self.next_rule_number = 1       # 用於生成連續編號
        self.rule_name_set = set()      # 儲存所有原則名稱，用於檢查重複

        # 全局定時器變數
        self.global_timer_interval_minutes = 10  # 全局定時器間隔（分鐘），默認10分鐘
        self.global_timer_id = None              # 用於控制tkinter的定時器ID
        self.is_processing_cycle = False         # 標誌當前是否正在執行一輪處理

        # RAM日誌系統變數
        self.ram_log_buffer = []                 # 儲存Log條目的列表（在RAM中）
        self.max_log_buffer_size = 100 * 1024    # 最大 100 KB (您指定的值)
        self.current_buffer_size = 0             # 當前緩衝區佔用字節數
        self.log_ui_buffer = []                  # UI更新緩衝（用於批次更新）
        self.log_batch_delay = 100               # UI批次更新延遲(毫秒)
        self.pending_ui_update = False           # 防止重複排程標誌

        # 全域狀態旗標
        self.photo_check_failed = False          # 照片檢查失敗旗標
        self.failed_rule_id = -1                 # 記錄觸發異常的原則編號
                # ====== 新增：排程設定 ======
        self.schedule_minutes = []  # 用於儲存每小時執行的分鐘列表，例如 [2, 7, 11, 19]
        # ====== TAB4變數定義結束 ======

        self.create_widgets()
        self.load_config()
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
                    self.log_to_file(f"Log檔案超過 {self.max_log_size/1024}KB，已備份並重新開始")
        except Exception as e:
            print(f"初始化log檔案時發生錯誤: {e}")
    
    def create_widgets(self):
        # 創建Notebook（標籤頁容器）放在最頂部
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
        
        # 創建第一個標籤頁 - 設備列表
        self.tab1 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text="設備列表")
        self.create_tab1_content()
        
        # 創建第二個標籤頁 - 通訊設定
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab2, text="通訊設定")
        self.create_tab2_content()
        
        # 創建第三個標籤頁 - 系統設定
        self.tab3 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab3, text="系統設定")
        self.create_tab3_content()
        
        # 創建第四個標籤頁 - 照片處理
        self.tab4 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab4, text="照片處理")
        self.create_tab4_content()  
        
        # 綁定Tab切換事件
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # 第三個框架 - 系統日誌（全局，在Notebook下方）
        self.log_frame = ttk.Frame(self.root, height=150)
        self.log_frame.pack(fill=tk.X, padx=10, pady=10)
        self.log_frame.pack_propagate(False)
        
        self.create_log_frame()
    
    def create_tab1_content(self):
        """創建設備列表Tab的內容"""
        # Treeview框架 - 最大化空間
        treeview_frame = ttk.Frame(self.tab1)
        treeview_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=(1, 0))
        
        # 建立Treeview來顯示設備列表
        columns = ("站名", "RTU ID", "UUID", "類型", "延遲(mS)", "啟用/停止")
        self.device_tree = ttk.Treeview(treeview_frame, columns=columns, show="headings")
        
        # 設定列標題
        for col in columns:
            self.device_tree.heading(col, text=col)
            self.device_tree.column(col, width=self.column_widths.get(col, 100))
        
        # 設定啟用/停止的標籤顏色
        self.device_tree.tag_configure('enabled', foreground='green')
        self.device_tree.tag_configure('disabled', foreground='gray')
        
        # 綁定Treeview事件
        self.device_tree.bind('<<TreeviewSelect>>', self.on_treeview_select)
        self.device_tree.bind('<Double-1>', self.on_treeview_double_click)
        self.device_tree.bind('<Button-1>', self.on_treeview_click)  # 新增點擊事件
        
        # 添加垂直滾軸
        v_scrollbar = ttk.Scrollbar(treeview_frame, orient=tk.VERTICAL, command=self.device_tree.yview)
        self.device_tree.configure(yscrollcommand=v_scrollbar.set)
        
        # 添加水平滾軸
        h_scrollbar = ttk.Scrollbar(treeview_frame, orient=tk.HORIZONTAL, command=self.device_tree.xview)
        self.device_tree.configure(xscrollcommand=h_scrollbar.set)
        
        # 使用grid佈局
        self.device_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # 配置網格權重
        treeview_frame.grid_rowconfigure(0, weight=1)
        treeview_frame.grid_columnconfigure(0, weight=1)
        
        # 操作區域框架（深灰色背景，在Treeview下方）
        self.operation_frame = ttk.Frame(self.tab1, style='Border.TFrame', height=80)
        self.operation_frame.pack(fill=tk.X, padx=1, pady=(5, 1))
        
        # 創建操作區域的內容（初始為正常模式）
        self.create_normal_operation()
        
        # 初始化時顯示正常模式
        self.show_normal_operation()
    
    def create_normal_operation(self):
        """創建正常模式的操作區域"""
        # 正常模式的框架
        self.normal_op_frame = ttk.Frame(self.operation_frame)
        
        # 左側：標題
        title_label = ttk.Label(
            self.normal_op_frame, 
            text="設備屬性列表", 
            background='#e0e0e0', 
            font=('Arial', 9, 'bold')
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
        self.rtu_hex_label = ttk.Label(row1_frame, text="十六進位: -", foreground="blue")
        self.rtu_hex_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 綁定RTU ID輸入變化事件
        self.rtu_id_entry.bind('<KeyRelease>', self.update_rtu_hex_display)
        
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
        self.type_combo = ttk.Combobox(row2_frame, textvariable=self.type_var, 
                                      values=["水位", "雨量", "圖片"], 
                                      width=8, state="readonly")
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
        self.enable_check = ttk.Checkbutton(row2_frame, text="啟用", variable=self.enable_var)
        self.enable_check.pack(side=tk.LEFT, padx=(0, 10))
        
        # 第三行：按鈕
        row3_frame = ttk.Frame(self.edit_op_frame)
        row3_frame.pack(fill=tk.X, padx=5, pady=(5, 5))
        
        # 更新/新增確定按鈕
        self.edit_confirm_btn = ttk.Button(row3_frame, text="更新確定", 
                                          command=self.add_or_update_device, width=10)
        self.edit_confirm_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 取消編輯按鈕
        self.edit_cancel_btn = ttk.Button(row3_frame, text="取消編輯", 
                                         command=self.cancel_edit, width=10)
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

    def start_add_device(self):
        """最小化实现，仅用于保证程序启动"""
        print("DEBUG: start_add_device 占位方法被调用")
        # 暂无实际功能，后续可替换
        
    
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
                values = list(self.device_tree.item(item, 'values'))
                current_display = values[5]
                
                # 切換狀態
                if "✓" in current_display:  # 目前是啟用，切換為停止
                    new_display = "[ ] 停止"
                    new_tag = 'disabled'
                    new_status = "停止"
                else:  # 目前是停止，切換為啟用
                    new_display = "[✓] 啟用"
                    new_tag = 'enabled'
                    new_status = "啟用"
                
                # 更新Treeview
                values[5] = new_display
                self.device_tree.item(item, values=values, tags=(new_tag,))
                
                # 記錄日誌
                station_name = values[0]
                self.log(f"設備 {station_name} 狀態已切換為 {new_status}")
    
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
            ("關閉功能表", self.close_function_menu)  # 使用專用函數處理
        ]
        
        # 創建下拉選單
        function_names = [name for name, _ in functions]
        self.function_combo = ttk.Combobox(
            parent_frame, 
            textvariable=self.function_var,
            values=function_names,
            state="readonly",
            width=12
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
    
    def create_tab2_content(self):
        """創建通訊設定Tab的內容"""
        main_frame = ttk.Frame(self.tab2)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 通訊協定設定
        protocol_frame = ttk.LabelFrame(main_frame, text="通訊協定設定", padding=10)
        protocol_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(protocol_frame, text="通訊協定:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.protocol_var = tk.StringVar(value="MODBUS RTU")
        protocol_combo = ttk.Combobox(protocol_frame, textvariable=self.protocol_var, 
                                      values=["MODBUS RTU", "MODBUS TCP", "OPC UA", "MQTT"], width=15)
        protocol_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 通訊參數設定
        comm_frame = ttk.LabelFrame(main_frame, text="通訊參數", padding=10)
        comm_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(comm_frame, text="通訊埠:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.port_entry = ttk.Entry(comm_frame, width=15)
        self.port_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.port_entry.insert(0, "COM1")
        
        ttk.Label(comm_frame, text="鮑率:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.baudrate_var = tk.StringVar(value="9600")
        baudrate_combo = ttk.Combobox(comm_frame, textvariable=self.baudrate_var, 
                                      values=["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"], width=15)
        baudrate_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 測試通訊按鈕
        test_button = ttk.Button(main_frame, text="測試通訊連線", command=self.test_communication)
        test_button.pack(pady=10)
    
    def create_tab3_content(self):
        """創建系統設定Tab的內容"""
        main_frame = ttk.Frame(self.tab3)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 儲存設定
        save_frame = ttk.LabelFrame(main_frame, text="儲存設定", padding=10)
        save_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(save_frame, text="自動儲存間隔(分鐘):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.auto_save_var = tk.StringVar(value="5")
        auto_save_entry = ttk.Entry(save_frame, textvariable=self.auto_save_var, width=10)
        auto_save_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 日誌設定
        log_frame = ttk.LabelFrame(main_frame, text="日誌設定", padding=10)
        log_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.log_level_var = tk.StringVar(value="INFO")
        ttk.Radiobutton(log_frame, text="DEBUG", variable=self.log_level_var, value="DEBUG").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Radiobutton(log_frame, text="INFO", variable=self.log_level_var, value="INFO").grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Radiobutton(log_frame, text="WARNING", variable=self.log_level_var, value="WARNING").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Radiobutton(log_frame, text="ERROR", variable=self.log_level_var, value="ERROR").grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Log檔案大小設定
        log_size_frame = ttk.LabelFrame(main_frame, text="Log檔案大小設定", padding=10)
        log_size_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(log_size_frame, text="最大Log檔案大小:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.log_size_var = tk.StringVar(value="100")
        log_size_combo = ttk.Combobox(log_size_frame, textvariable=self.log_size_var, 
                                      values=["50", "100", "200", "300", "500", "1024", "5120"], width=10)
        log_size_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(log_size_frame, text="KB").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Log檔案管理按鈕
        log_manage_button = ttk.Button(log_size_frame, text="管理Log檔案", command=self.manage_log_file)
        log_manage_button.grid(row=0, column=3, sticky=tk.W, padx=(20, 5), pady=5)
        
        # 立即儲存按鈕
        save_button = ttk.Button(main_frame, text="立即儲存設定", command=self.save_config)
        save_button.pack(pady=10)
        
        # 載入設定按鈕
        load_button = ttk.Button(main_frame, text="載入設定", command=self.load_config)
        load_button.pack(pady=5)

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
        self.timer_interval_var = tk.StringVar(value=str(self.global_timer_interval_minutes))
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
        
        ttk.Button(button_frame, text="啟動定時器", command=self.start_global_timer).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="停止定時器", command=self.stop_global_timer).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="立即執行一輪", command=self.manual_process_cycle).pack(side=tk.LEFT, padx=2)
        
        # 狀態顯示
        self.timer_status_var = tk.StringVar(value="狀態: 定時器未啟動")
        status_label = ttk.Label(control_frame, textvariable=self.timer_status_var, font=('Arial', 9))
        status_label.pack(pady=2)
        
        # 中間：處理原則列表 (Treeview)
        list_frame = ttk.LabelFrame(self.tab4, text="處理原則列表", padding=(5, 5))
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 創建Treeview
        columns = ("編號", "標註", "來源檔案", "最終目的地", "狀態", "異常原因", "啟用")
        self.rule_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        
        # 設定欄位寬度
        column_widths = {"編號": 50, "標註": 120, "來源檔案": 150, "最終目的地": 200, "狀態": 80, "異常原因": 150, "啟用": 60}
        for col in columns:
            self.rule_tree.heading(col, text=col)
            self.rule_tree.column(col, width=column_widths.get(col, 100))
        
        # 垂直滾動條
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.rule_tree.yview)
        self.rule_tree.configure(yscrollcommand=v_scrollbar.set)
        
        # 水平滾動條
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.rule_tree.xview)
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
        
        ttk.Button(rule_button_frame, text="新增處理原則", command=self.add_processing_rule).pack(side=tk.LEFT, padx=2)
        ttk.Button(rule_button_frame, text="編輯選中原則", command=self.edit_selected_rule).pack(side=tk.LEFT, padx=2)
        ttk.Button(rule_button_frame, text="刪除選中原則", command=self.delete_selected_rule).pack(side=tk.LEFT, padx=2)
        ttk.Button(rule_button_frame, text="啟用/停用選中", command=self.toggle_rule_enable).pack(side=tk.LEFT, padx=2)

        # ====== Tab4 事件處理方法（最小化實現，避免錯誤）=====
    
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
        if hasattr(self, 'tab4_status_var'):
            self.tab4_status_var.set("已載入 0 條處理原則")

        
    def create_log_frame(self):
        """創建日誌框架"""
        # 建立日誌文字框
        self.log_text = scrolledtext.ScrolledText(
            self.log_frame, 
            wrap=tk.WORD, 
            width=80, 
            height=8
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 加入右鍵選單
        self.context_menu = Menu(self.log_text, tearoff=0)
        self.context_menu.add_command(label="全選", command=self.select_all)
        self.context_menu.add_command(label="複製", command=self.copy_text)
        self.context_menu.add_command(label="清除", command=self.clear_log)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="匯出Log到檔案", command=self.export_log_to_file)
        self.context_menu.add_command(label="查看Log檔案", command=self.view_log_file)
        
        # 綁定右鍵事件
        self.log_text.bind("<Button-3>", self.show_context_menu)
        
        # 初始日誌訊息
        self.log("系統啟動成功")
    
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
        """顯示編輯模式的操作區域
        mode: "edit" 編輯模式, "add" 新增模式
        values: 編輯時的數據
        """
        # 如果正常模式框架存在，先隱藏
        if hasattr(self, 'normal_op_frame') and self.normal_op_frame:
            self.normal_op_frame.pack_forget()
        
        # 如果編輯模式框架不存在，先創建
        if not hasattr(self, 'edit_op_frame') or not self.edit_op_frame:
            self.create_edit_operation()
        
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
            self.clear_edit_inputs()
        
        # 顯示編輯模式框架
        self.edit_op_frame.pack(fill=tk.X, expand=True)
        self.ui_mode = mode
    
    def fill_edit_inputs(self, values):
        """將Treeview中的值填入編輯輸入欄位 - 更新為新的欄位順序"""
        # 清空輸入欄位
        self.clear_edit_inputs()
        
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
            match = re.match(r'^(\d+)\s*\(', display_str)
            if match:
                return int(match.group(1))
            
            # 如果沒有括號，嘗試直接轉換
            return int(display_str)
        except (ValueError, AttributeError):
            return None
    
    def clear_edit_inputs(self):
        """清除編輯輸入欄位"""
        if hasattr(self, 'station_name_entry'):
            self.station_name_entry.delete(0, tk.END)
        if hasattr(self, 'rtu_id_entry'):
            self.rtu_id_entry.delete(0, tk.END)
        if hasattr(self, 'uuid_entry'):
            self.uuid_entry.delete(0, tk.END)
        if hasattr(self, 'delay_entry'):
            self.delay_entry.delete(0, tk.END)
            self.delay_entry.insert(0, "50")  # 重置時設為50
        
        # 重置十六進位顯示
        if hasattr(self, 'rtu_hex_label'):
            self.rtu_hex_label.config(text="十六進位: -", foreground="blue")
        
        # 重置類型選擇
        if hasattr(self, 'type_var'):
            self.type_var.set("")
        
        if hasattr(self, 'enable_var'):
            self.enable_var.set(True)
    
    def on_tab_changed(self, event):
        """處理Tab切換事件"""
        current_tab = self.notebook.index(self.notebook.select())
        
        # 如果切換到非設備列表Tab，確保回到正常模式
        if current_tab != 0:
            if self.ui_mode != "normal":
                self.show_normal_operation()
                self.log(f"已切換到Tab{current_tab + 1}，操作區域恢復正常模式")
    
    def start_add_device(self):
        """開始新增設備模式"""
        self.show_edit_operation(mode="add")
        self.log("進入新增設備模式")
    
    def validate_hex(self, value):
        """驗證16進位字串"""
        try:
            int(value, 16)
            return True
        except ValueError:
            return False
    
    def validate_uuid(self, value):
        """驗證UUID - 接受兩種格式"""
        # 轉為大寫並去除空白
        value = value.strip().upper()
        
        # 檢查是否為標準格式（帶連字號）
        standard_pattern = r'^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$'
        
        # 檢查是否為連續32位十六進位
        continuous_pattern = r'^[0-9A-F]{32}$'
        
        if re.match(standard_pattern, value):
            # 標準格式，驗證通過
            return True
        elif re.match(continuous_pattern, value):
            # 連續32位格式，驗證通過
            return True
        else:
            # 兩種格式都不符合
            return False
    
    def normalize_uuid(self, uuid_str):
        """將UUID統一轉換為標準格式"""
        if not uuid_str:
            return ""
        
        # 轉為大寫並去除空白
        uuid_str = uuid_str.strip().upper()
        
        # 如果已經是標準格式，直接返回
        standard_pattern = r'^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$'
        if re.match(standard_pattern, uuid_str):
            return uuid_str
        
        # 如果是連續32位，轉換為標準格式
        continuous_pattern = r'^[0-9A-F]{32}$'
        if re.match(continuous_pattern, uuid_str):
            # 轉換為標準格式：8-4-4-4-12
            return f"{uuid_str[0:8]}-{uuid_str[8:12]}-{uuid_str[12:16]}-{uuid_str[16:20]}-{uuid_str[20:32]}"
        
        # 如果都不符合，返回原值（將在驗證時被拒絕）
        return uuid_str
    
    def format_rtu_id(self, decimal_value):
        """格式化RTU ID顯示：十進位 (十六進位參考) - 接受十進位整數"""
        try:
            # 檢查輸入是否為整數
            if not isinstance(decimal_value, int):
                # 如果是字串，嘗試轉換
                decimal_value = int(decimal_value)
            
            # 檢查範圍
            if decimal_value < 0 or decimal_value > 65535:
                return f"{decimal_value} (超出範圍)"
            
            # 根據數值大小決定十六進位顯示位數
            if decimal_value <= 0xFF:  # 0-255
                hex_str = f"0x{decimal_value:02X}"
            else:  # 256-65535
                hex_str = f"0x{decimal_value:04X}"
            
            # 返回顯示格式：十進位 (十六進位參考)
            return f"{decimal_value} ({hex_str})"
        except (ValueError, TypeError):
            # 如果轉換失敗，返回原始值
            return str(decimal_value)
    
    def add_or_update_device(self):
        """新增或更新設備（根據編輯模式）"""
        if self.ui_mode == "add":
            self.add_device()
        elif self.ui_mode == "edit":
            self.update_device()
    
    def add_device(self):
        """新增設備 - 更新為新的欄位順序和類型選擇"""
        if not hasattr(self, 'station_name_entry'):
            self.log("錯誤: 輸入欄位未初始化")
            return
        
        station_name = self.station_name_entry.get()
        rtu_id_dec_str = self.rtu_id_entry.get()
        uuid_val = self.uuid_entry.get().upper()
        selected_type = self.type_var.get()  # 獲取選擇的類型
        delay_val = self.delay_entry.get()
        is_enabled = self.enable_var.get()
        
        # 驗證輸入
        validation_result = self.validate_input(station_name, rtu_id_dec_str, uuid_val, selected_type, delay_val)
        if not validation_result["valid"]:
            self.log(validation_result["message"])
            return
        
        # 轉換RTU ID為整數
        rtu_id_decimal = int(rtu_id_dec_str)
        
        # 格式化RTU ID顯示
        rtu_display = self.format_rtu_id(rtu_id_decimal)
        
        # UUID格式化為標準格式
        uuid_formatted = self.normalize_uuid(uuid_val)
        
        # 格式化啟用/停止顯示
        if is_enabled:
            status_display = "[✓] 啟用"
            status_tag = 'enabled'
            status_log = "啟用"
        else:
            status_display = "[ ] 停止"
            status_tag = 'disabled'
            status_log = "停止"
        
        # 加入到設備列表（新的欄位順序）
        self.device_tree.insert("", tk.END, values=(
            station_name, 
            rtu_display,
            uuid_formatted,
            selected_type,
            delay_val, 
            status_display
        ), tags=(status_tag,))
        
        self.log(f"已新增設備: 站名={station_name}, RTU ID={rtu_id_decimal}, 類型={selected_type}, 狀態={status_log}")
        
        # 清空輸入欄位並回到正常模式
        self.clear_edit_inputs()
        self.show_normal_operation()
    
    def update_device(self):
        """更新現有設備 - 更新為新的欄位順序和類型選擇"""
        if not self.editing_item:
            self.log("錯誤: 沒有選擇要編輯的項目")
            return
        
        if not hasattr(self, 'station_name_entry'):
            self.log("錯誤: 輸入欄位未初始化")
            return
        
        station_name = self.station_name_entry.get()
        rtu_id_dec_str = self.rtu_id_entry.get()
        uuid_val = self.uuid_entry.get().upper()
        selected_type = self.type_var.get()  # 獲取選擇的類型
        delay_val = self.delay_entry.get()
        is_enabled = self.enable_var.get()
        
        # 驗證輸入
        validation_result = self.validate_input(station_name, rtu_id_dec_str, uuid_val, selected_type, delay_val)
        if not validation_result["valid"]:
            self.log(validation_result["message"])
            return
        
        # 轉換RTU ID為整數
        rtu_id_decimal = int(rtu_id_dec_str)
        
        # 格式化RTU ID顯示
        rtu_display = self.format_rtu_id(rtu_id_decimal)
        
        # UUID格式化為標準格式
        uuid_formatted = self.normalize_uuid(uuid_val)
        
        # 格式化啟用/停止顯示
        if is_enabled:
            status_display = "[✓] 啟用"
            status_tag = 'enabled'
            status_log = "啟用"
        else:
            status_display = "[ ] 停止"
            status_tag = 'disabled'
            status_log = "停止"
        
        # 更新設備列表中的項目（新的欄位順序）
        self.device_tree.item(self.editing_item, values=(
            station_name, 
            rtu_display,
            uuid_formatted,
            selected_type,
            delay_val, 
            status_display
        ), tags=(status_tag,))
        
        self.log(f"已更新設備: 站名={station_name}, RTU ID={rtu_id_decimal}, 類型={selected_type}, 狀態={status_log}")
        
        # 清空輸入欄位並回到正常模式
        self.clear_edit_inputs()
        self.show_normal_operation()
    
    def validate_input(self, station_name, rtu_id_dec_str, uuid_val, selected_type, delay_val):
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
        if not self.validate_uuid(uuid_val):
            return {"valid": False, "message": "錯誤: UUID 格式不正確\n可接受: 32位十六進位 或 標準格式 (8-4-4-4-12)"}
        
        if delay_val and not delay_val.isdigit():
            return {"valid": False, "message": "錯誤: 延遲時間必須為數字"}
        
        return {"valid": True, "message": ""}
    
    def on_treeview_select(self, event):
        """處理Treeview選擇事件"""
        selection = self.device_tree.selection()
        if selection:
            item = self.device_tree.item(selection[0])
            values = item['values']
            if values:
                self.log(f"選中設備: {values[0]} (RTU ID: {values[1]})")
    
    def on_treeview_double_click(self, event):
        """處理Treeview雙擊事件"""
        selection = self.device_tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        item = self.device_tree.item(item_id)
        values = item['values']
        
        if not values:
            return
        
        # 進入編輯模式
        self.editing_item = item_id
        self.show_edit_operation(mode="edit", values=values)
        
        self.log(f"進入編輯模式: {values[0]}")
    
    def cancel_edit(self):
        """取消編輯模式"""
        if self.ui_mode != "normal":
            self.log("已取消編輯")
            self.clear_edit_inputs()
            self.show_normal_operation()
    
    def save_config(self):
        """儲存設定到INI檔案 - 更新為新的欄位順序"""
        try:
            config = configparser.ConfigParser()
            
            # 儲存欄位寬度
            config['COLUMN_WIDTHS'] = {}
            for col in self.device_tree['columns']:
                width = self.device_tree.column(col, 'width')
                config['COLUMN_WIDTHS'][col] = str(width)
            
            # 儲存設備數據（新的欄位順序）
            config['DEVICE_COUNT'] = {'count': str(len(self.device_tree.get_children()))}
            
            for i, item_id in enumerate(self.device_tree.get_children()):
                item = self.device_tree.item(item_id)
                values = item['values']
                
                # 從顯示文本中提取啟用/停止狀態
                status_display = values[5]
                if "✓" in status_display:
                    enabled = "啟用"
                else:
                    enabled = "停止"
                
                section = f'DEVICE_{i+1:03d}'
                config[section] = {
                    'station_name': values[0] if len(values) > 0 else '',
                    'rtu_id': values[1] if len(values) > 1 else '',
                    'uuid': values[2] if len(values) > 2 else '',
                    'type': values[3] if len(values) > 3 else '',  # 類型
                    'delay': values[4] if len(values) > 4 else '',
                    'enabled': enabled
                }
            
            # 儲存通訊設定（如果存在）
            if hasattr(self, 'protocol_var'):
                config['COMMUNICATION'] = {
                    'protocol': self.protocol_var.get(),
                    'port': self.port_entry.get() if hasattr(self, 'port_entry') else 'COM1',
                    'baudrate': self.baudrate_var.get() if hasattr(self, 'baudrate_var') else '9600'
                }
            
            # 儲存系統設定（如果存在）
            if hasattr(self, 'auto_save_var'):
                config['SYSTEM'] = {
                    'auto_save': self.auto_save_var.get(),
                    'log_level': self.log_level_var.get() if hasattr(self, 'log_level_var') else 'INFO'
                }
            
            # 儲存Log設定
            config['LOG_SETTINGS'] = {
                'max_log_size_kb': self.log_size_var.get() if hasattr(self, 'log_size_var') else '100'
            }
            
            # 寫入檔案
            with open(self.config_file, 'w', encoding='utf-8') as f:
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
            config.read(self.config_file, encoding='utf-8')
            
            # 清空現有設備列表
            for item in self.device_tree.get_children():
                self.device_tree.delete(item)
            
            # 載入設備數據
            if 'DEVICE_COUNT' in config:
                device_count = int(config['DEVICE_COUNT']['count'])
                
                for i in range(1, device_count + 1):
                    section = f'DEVICE_{i:03d}'
                    if section in config:
                        device_data = config[section]
                        
                        # 處理舊格式轉換（如果有water_level、rainfall、image欄位）
                        device_type = device_data.get('type', '')
                        
                        # 如果沒有type欄位，檢查舊的三個布林欄位
                        if not device_type and ('water_level' in device_data or 'rainfall' in device_data or 'image' in device_data):
                            # 舊格式轉換
                            if device_data.get('water_level', '').lower() == '是':
                                device_type = '水位'
                            elif device_data.get('rainfall', '').lower() == '是':
                                device_type = '雨量'
                            elif device_data.get('image', '').lower() == '是':
                                device_type = '圖片'
                        
                        # RTU ID顯示格式轉換（如果有需要）
                        rtu_id_display = device_data.get('rtu_id', '')
                        if rtu_id_display.startswith('0x'):
                            try:
                                # 轉換舊格式到新格式
                                hex_str = rtu_id_display[2:]
                                decimal_value = int(hex_str, 16)
                                rtu_id_display = self.format_rtu_id(decimal_value)
                            except:
                                pass  # 如果轉換失敗，保持原樣
                        
                        # 啟用/停止狀態處理
                        enabled = device_data.get('enabled', '啟用')
                        if enabled == '啟用':
                            status_display = "[✓] 啟用"
                            status_tag = 'enabled'
                        else:
                            status_display = "[ ] 停止"
                            status_tag = 'disabled'
                        
                        # 添加到Treeview（新的欄位順序）
                        self.device_tree.insert("", tk.END, values=(
                            device_data.get('station_name', ''),
                            rtu_id_display,
                            device_data.get('uuid', ''),
                            device_type,  # 類型
                            device_data.get('delay', ''),
                            status_display
                        ), tags=(status_tag,))
            
            # 載入欄位寬度
            if 'COLUMN_WIDTHS' in config:
                for col in self.device_tree['columns']:
                    if col in config['COLUMN_WIDTHS']:
                        width = int(config['COLUMN_WIDTHS'][col])
                        self.device_tree.column(col, width=width)
                        self.column_widths[col] = width
            
            # 載入通訊設定
            if 'COMMUNICATION' in config and hasattr(self, 'protocol_var'):
                self.protocol_var.set(config['COMMUNICATION'].get('protocol', 'MODBUS RTU'))
                if hasattr(self, 'port_entry'):
                    self.port_entry.delete(0, tk.END)
                    self.port_entry.insert(0, config['COMMUNICATION'].get('port', 'COM1'))
                if hasattr(self, 'baudrate_var'):
                    self.baudrate_var.set(config['COMMUNICATION'].get('baudrate', '9600'))
            
            # 載入系統設定
            if 'SYSTEM' in config and hasattr(self, 'auto_save_var'):
                self.auto_save_var.set(config['SYSTEM'].get('auto_save', '5'))
                if hasattr(self, 'log_level_var'):
                    self.log_level_var.set(config['SYSTEM'].get('log_level', 'INFO'))
            
            # 載入Log設定
            if 'LOG_SETTINGS' in config and hasattr(self, 'log_size_var'):
                log_size = config['LOG_SETTINGS'].get('max_log_size_kb', '100')
                self.log_size_var.set(log_size)
                self.max_log_size = int(log_size) * 1024
            
            self.log(f"設定已從 {self.config_file} 載入")
            
        except Exception as e:
            self.log(f"載入設定時發生錯誤: {str(e)}")
    
    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)
    
    def select_all(self):
        self.log_text.tag_add(tk.SEL, "1.0", tk.END)
        self.log_text.mark_set(tk.INSERT, "1.0")
        self.log_text.see(tk.INSERT)
        return 'break'
    
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
            with open(self.log_file, 'a', encoding='utf-8') as f:
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
                        with open(backup_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        # 保留最後1000行
                        keep_lines = lines[-1000:] if len(lines) > 1000 else lines
                        
                        with open(self.log_file, 'w', encoding='utf-8') as f:
                            f.writelines(keep_lines)
                        
                        self.log_text.insert(tk.END, f"[系統] Log檔案超過 {self.max_log_size/1024}KB，已壓縮並備份\n")
                        self.log_to_file(f"Log檔案超過 {self.max_log_size/1024}KB，已壓縮並備份為 {backup_file}")
                    except:
                        # 如果讀取失敗，創建新檔案
                        with open(self.log_file, 'w', encoding='utf-8') as f:
                            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Log檔案重新開始\n")
        except Exception as e:
            print(f"檢查log檔案大小時發生錯誤: {e}")
    
    def export_log_to_file(self):
        """匯出當前log到檔案"""
        file_path = filedialog.asksaveasfilename(
            title="儲存Log檔案",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"log_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if file_path:
            try:
                log_content = self.log_text.get(1.0, tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.log(f"Log已匯出至 {file_path}")
            except Exception as e:
                messagebox.showerror("錯誤", f"匯出Log時發生錯誤:\n{str(e)}")
    
    def view_log_file(self):
        """查看log檔案內容"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
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
                close_btn = ttk.Button(log_window, text="關閉", command=log_window.destroy)
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
                f"超過限制時會自動壓縮並備份"
            )
        except Exception as e:
            messagebox.showerror("錯誤", f"管理Log檔案時發生錯誤:\n{str(e)}")
    
    def import_config(self):
        file_path = filedialog.askopenfilename(
            title="選擇要匯入的設定檔",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")]
        )
        if file_path:
            self.config_file = file_path
            self.load_config()
            self.log(f"已從 {file_path} 匯入設定")
    
    def export_config(self):
        file_path = filedialog.asksaveasfilename(
            title="儲存設定檔",
            defaultextension=".ini",
            filetypes=[("INI files", "*.ini"), ("All files", "*.*")],
            initialfile="Iow_item_config_backup.ini"
        )
        if file_path:
            self.config_file = file_path
            self.save_config()
    
    def delete_device(self):
        selected = self.device_tree.selection()
        if selected:
            for item in selected:
                device_name = self.device_tree.item(item)['values'][0]
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
        if hasattr(self, 'protocol_var'):
            protocol = self.protocol_var.get()
            port = self.port_entry.get() if hasattr(self, 'port_entry') else "COM1"
            baudrate = self.baudrate_var.get() if hasattr(self, 'baudrate_var') else "9600"
            
            self.log(f"測試通訊連線: 協定={protocol}, 埠={port}, 鮑率={baudrate}")
            messagebox.showinfo("通訊測試", f"正在測試 {protocol} 通訊...\n埠: {port}\n鮑率: {baudrate}")

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
        self.global_timer_id = self.root.after(interval_ms, self.process_all_rules_cycle)
        
        # 更新狀態顯示
        next_time = datetime.now() + timedelta(minutes=self.global_timer_interval_minutes)
        next_str = next_time.strftime("%H:%M:%S")
        self.timer_status_var.set(f"狀態: 定時器已啟動 - 下一輪於 {next_str} 開始")
        self.log_message(f"全局定時器已啟動，間隔: {self.global_timer_interval_minutes} 分鐘")

    def stop_global_timer(self):
        """停止全局定時器"""
        if self.global_timer_id:
            self.root.after_cancel(self.global_timer_id)
            self.global_timer_id = None
            self.timer_status_var.set("狀態: 定時器已停止")
            self.log_message("全局定時器已停止")

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
            self.timer_status_var.set(f"狀態: 處理中 ({idx}/{total_rules}) - {rule_data.get('name', '未命名')}")
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

    # ====== 新增：RAM日誌系統方法 ======
    def log_message(self, message, level="INFO"):
        """將日誌訊息存入RAM緩衝區並安排UI批次更新"""
        # 1. 建立時間戳記
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} [{level}] - {message}"
        
        # 2. 存入RAM緩衝區（計算字節大小）
        entry_size = len(log_entry.encode('utf-8'))
        self.ram_log_buffer.append(log_entry)
        self.current_buffer_size += entry_size
        
        # 3. 限制緩衝區大小（100KB限制）
        while self.current_buffer_size > self.max_log_buffer_size and self.ram_log_buffer:
            removed_entry = self.ram_log_buffer.pop(0)
            self.current_buffer_size -= len(removed_entry.encode('utf-8'))
        
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
        if hasattr(self, 'log_text') and self.log_text.winfo_exists():
            self.log_text.insert(tk.END, text_to_insert)
            
            # 限制顯示行數（最多500行）
            line_count = int(self.log_text.index('end-1c').split('.')[0])
            if line_count > 500:
                excess = line_count - 500
                self.log_text.delete(1.0, f"{excess+1}.0")
            
            self.log_text.see(tk.END)  # 自動滾動到最新
        
        self.log_ui_buffer.clear()
        self.pending_ui_update = False

    def process_single_rule(self, rule_id, rule_data):
        """處理單個規則 - 實現：檔案驗證模組"""
        rule_num = rule_data['id']
        rule_name = rule_data['name']
        source_path = rule_data.get('source_path', '')
        
        # 初始化本輪的錯誤訊息
        current_error = ""
        
        # ====== 1. 檢查檔案是否存在 ======
        if not source_path or not os.path.exists(source_path):
            current_error = "檔案不存在"
            self.log_message(f"規則 #{rule_num}: 來源檔案不存在。路徑: {source_path}", level="ERROR")
            # 後續將交給異常處理模組
            self._handle_processing_error(rule_data, current_error)
            return # 檔案不存在，後續步驟無法進行，直接結束本次處理
        
        # ====== 2. 檢查是否為有效圖片檔案 ======
        is_valid_image = False
        try:
            # 使用PIL嘗試開啟並驗證圖片
            with Image.open(source_path) as img:
                img.verify()  # 驗證檔案完整性，損壞的檔案會在此拋出異常
                # 如果驗證通過，再重新打開以供後續操作（verify()會關閉檔案）
                img = Image.open(source_path)
                img.load() # 確保可以完全載入
                is_valid_image = True
                # 可以在此取得圖片資訊供後續使用，例如：
                rule_data['_last_image_size'] = img.size # 儲存尺寸供比對
                img.close()
        except Exception as img_error:
            current_error = f"檔案破損 ({img_error})"
            self.log_message(f"規則 #{rule_num}: 圖片檔案損毀或格式不支持。錯誤: {img_error}", level="ERROR")
            self._handle_processing_error(rule_data, current_error)
            return
        
        # ====== 3. 檢查檔案是否重複（與前次處理的內容比對） ======
        if is_valid_image:
            current_hash = calculate_file_hash(source_path)
            last_hash = rule_data.get('_last_valid_hash', None)
            
            if current_hash == last_hash and last_hash is not None:
                current_error = "檔案重複"
                self.log_message(f"規則 #{rule_num}: 檔案內容與上次處理時相同（重複）。", level="WARNING")
                self._handle_processing_error(rule_data, current_error)
                return
            
            # 如果是不重複的有效檔案，更新哈希值記錄
            rule_data['_last_valid_hash'] = current_hash
            self.log_message(f"規則 #{rule_num}: 檔案驗證通過。")
            # *** 注意：這裡通過驗證，但尚未執行備份等操作 ***
            # 我們將在下一個模組（合格檔案處理）中接續這裡的邏輯
            # 目前先將狀態標記為正常，但實際的複製、移動操作還未進行
            rule_data['status'] = "正常"
            rule_data['last_error'] = ""
            # 重置錯誤計數器（因為本次拿到了有效的新檔案）
            rule_data['error_counter'] = 0
            self.refresh_rule_treeview()

        # *** 接續在「檔案驗證通過」的日誌輸出之後 ***
        # ====== 4. 合格檔案處理流程（備份、縮放、移動） ======
        self.log_message(f"規則 #{rule_num}: 開始執行檔案備份與處理...")
        
        # 準備路徑
        source_dir = os.path.dirname(source_path)
        source_filename = os.path.basename(source_path)     # 取得實際檔名，如 'ABC.jpg'
        filename_without_ext = os.path.splitext(source_filename)[0]  # 去掉副檔名，例如 "Cam1"
        file_ext = os.path.splitext(source_filename)[1]  # 包含點的副檔名，例如 ".jpg"
        
        backup_path = rule_data.get('backup_path', './IMG')
        output_path = rule_data.get('output_path', '')
        
        # 確保備份和輸出目錄存在
        os.makedirs(backup_path, exist_ok=True)
        if output_path:
            os.makedirs(output_path, exist_ok=True)
        
        try:
            import shutil  # 用於檔案複製和移動
            
            # 4.1 建立原始檔副本 (xxx-o.jpg)
            backup_base_name = os.path.splitext(rule_data['source_file'])[0]  # 例如 'Cam2'
            backup_o = os.path.join(backup_path, f"{filename_without_ext}-o{file_ext}")
            shutil.copy2(source_path, backup_o)
            self.log_message(f"規則 #{rule_num}: 已建立原始備份 -> {backup_o}")
            
            # 4.2 建立縮放版本 (xxx-s.jpg)
            # 獲取設定的解析度
            resolution = rule_data.get('resolution', '800x600')
            try:
                target_width, target_height = map(int, resolution.split('x'))
            except:
                target_width, target_height = 800, 600  # 預設值
                self.log_message(f"規則 #{rule_num}: 解析度格式無效，使用預設 800x600", "WARNING")
            
            # 打開圖片並進行縮放
            img = Image.open(source_path)
            # 保持寬高比的縮放（可選，這裡使用最簡單的強制縮放）
            img_resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            backup_s = os.path.join(backup_path, f"{filename_without_ext}-s{file_ext}")  # 儲存xxx-s.jpg
            img_resized.save(backup_s, quality=95)
            img.close()
            self.log_message(f"規則 #{rule_num}: 已建立縮放備份 -> {backup_s}")
            
            # 4.3 將原始檔案“複製”到最終目的地（關鍵修正：保留來源檔）
            if output_path:
                final_dest = os.path.join(output_path, source_filename)
                # 如果目的地已有同名檔案，可選擇覆蓋或跳過（這裡選擇覆蓋）
                if os.path.exists(final_dest):
                    self.log_message(f"規則 #{rule_num}: 目的地檔案已存在，將被覆蓋。", "WARNING")
                # ========== 核心修正線：將 shutil.move 改為 shutil.copy2 ==========
                shutil.copy2(source_path, final_dest)  # 複製並保留元數據
                # =================================================================
                self.log_message(f"規則 #{rule_num}: 已複製原始檔至 -> {final_dest}")
                # *** 重要：不再更新 rule_data['source_path']，來源路徑保持不變 ***
            else:
                self.log_message(f"規則 #{rule_num}: 未設定最終目的地，跳過複製。", "INFO")
            
            # 4.4 更新規則狀態
            rule_data['status'] = "正常 (已處理)"
            rule_data['last_error'] = ""
            rule_data['error_counter'] = 0  # 重置錯誤計數器
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
        rule_id = rule_data['id']
        rule_data['status'] = "異常"
        rule_data['last_error'] = error_msg
        # 錯誤計數器增加
        rule_data['error_counter'] = rule_data.get('error_counter', 0) + 1
        self.log_message(f"規則 #{rule_id} 錯誤計數器增加至: {rule_data['error_counter']}")
        
        # 設定全域旗標（供Tab1-3讀取）
        self.photo_check_failed = True
        self.failed_rule_id = rule_id
        
        # ====== 關鍵修正：立即嘗試從備份還原檔案 ======
        # 先執行還原操作
        restore_success = self._restore_from_backup(rule_data)
        
        # 根據還原結果，可以微調狀態訊息（可選）
        if restore_success:
            rule_data['status'] = "異常 (已嘗試還原)"
        # ============================================
        
        # 最後刷新介面
        self.refresh_rule_treeview()
        
        # 注意：這個方法不再需要返回值，因為呼叫者會在呼叫後直接 `return`


    def _restore_from_backup(self, rule_data):
        """從備份資料夾還原檔案到最終目的地（根據錯誤計數器奇偶性）"""
        rule_id = rule_data['id']
        
        # ====== 核心修復：更精確的備份路徑計算 ======
        # 1. 檢查最終目的地
        output_path = rule_data.get('output_path', '').strip()
        if not output_path:
            self.log_message(f"[還原] 規則 #{rule_id}: 跳過。原因：「最終目的地」為空。", level="WARNING")
            return False
        
        # 2. 獲取並標準化備份路徑 (將相對路徑 ./IMG 轉為絕對路徑)
        raw_backup_path = rule_data.get('backup_path', './IMG')
        # 如果使用者輸入的是相對路徑，則基於主程式檔案位置進行解析
        if not os.path.isabs(raw_backup_path):
            # 取得當前 .pyw 檔案所在的目錄
            base_dir = os.path.dirname(os.path.abspath(__file__))
            backup_path = os.path.normpath(os.path.join(base_dir, raw_backup_path))
        else:
            backup_path = raw_backup_path
            
        if not os.path.isdir(backup_path):
            self.log_message(f"[還原] 規則 #{rule_id}: 跳過。原因：備份資料夾不存在「{backup_path}」。", level="ERROR")
            return False
        
        # 3. 構建備份檔名
        # ====== 【關鍵修正開始】決定用於尋找備份和還原的“基礎檔案名” ======
        # 優先使用 source_path 中的實際名稱，如果沒有則使用記錄的 source_file
        source_path = rule_data.get('source_path', '')
        if source_path and os.path.basename(source_path):
            # 從完整來源路徑提取實際檔名，如 'ABC.jpg'
            actual_filename = os.path.basename(source_path)
        else:
            # 降級方案：使用規則中記錄的檔案名
            actual_filename = rule_data.get('source_file', f"Cam{rule_id}.jpg")
        
        filename_without_ext = os.path.splitext(actual_filename)[0]  # 如 'ABC'
        file_ext = os.path.splitext(actual_filename)[1] or '.jpg'
        # ====== 【關鍵修正結束】 ======
        
        error_counter = rule_data.get('error_counter', 0)
        # 根據奇偶性決定首要嘗試的備份後綴
        primary_suffix = '-s' if (error_counter % 2 == 1) else '-o'
        secondary_suffix = '-o' if primary_suffix == '-s' else '-s'  # 備用後綴
        
        # 4. 嘗試尋找備份檔案 (首選 -> 備用)
        backup_found = None
        for suffix in [primary_suffix, secondary_suffix]:
            test_filename = f"{filename_without_ext}{suffix}{file_ext}"
            test_path = os.path.join(backup_path, test_filename)
            if os.path.exists(test_path):
                backup_found = (test_path, suffix)
                break
        
        if not backup_found:
            self.log_message(f"[還原] 規則 #{rule_id}: 跳過。原因：在「{backup_path}」下找不到任何備份檔案 (*-o.jpg 或 *-s.jpg)。", level="ERROR")
            return False
        
        backup_file_path, used_suffix = backup_found
        backup_type = "縮放版(-s)" if used_suffix == '-s' else "原始版(-o)"
        
        # 5. 執行還原 (複製)
        target_file_path = os.path.join(output_path, actual_filename)  # 使用 actual_filename
        try:
            import shutil
            # 確保目的資料夾存在
            os.makedirs(os.path.dirname(target_file_path), exist_ok=True)
            shutil.copy2(backup_file_path, target_file_path)
            self.log_message(f"[還原] 規則 #{rule_id}: 成功！已將「{backup_type}」備份還原至「{target_file_path}」", level="INFO")
            # 還原成功後，可更新狀態為“已還原”，但保留錯誤計數器
            rule_data['status'] = "已從備份還原"
            return True
        except Exception as e:
            self.log_message(f"[還原] 規則 #{rule_id}: 失敗。原因：複製檔案時出錯「{e}」。", level="ERROR")
            return False
            

    def refresh_rule_treeview(self):
        """刷新Treeview顯示，僅顯示來源檔案的名稱（非完整路徑）"""
        # 刪除現有項目
        for item in self.rule_tree.get_children():
            self.rule_tree.delete(item)
        
        # 添加所有規則
        for rule_id, rule_data in self.processing_rules.items():
            # 核心邏輯：決定在列表中顯示什麼
            display_source = rule_data.get('source_file', f"Cam{rule_data['id']}.jpg") # 預設為 CamX.jpg
            
            # 如果用戶已經選擇了具體檔案路徑，則從路徑中提取純檔名來顯示
            actual_path = rule_data.get('source_path', '')
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
                "✓" if rule_data.get("enabled", False) else "✗"
            )
            self.rule_tree.insert("", tk.END, values=values)

    def add_processing_rule(self):
        """新增一個處理原則 - 修正編號生成邏輯版"""
        # 檢查是否已達到64個原則的限制
        if len(self.processing_rules) >= 64:
            messagebox.showwarning(
                "達到限制",
                "已達到最大處理原則數量 (64個)。\n請刪除不必要的原則後再新增。"
            )
            return
        
        # 【修正核心】先將當前編號儲存到一個變數中，供本規則所有地方使用
        current_rule_number = self.next_rule_number
        
        # 創建新規則，統一使用 current_rule_number
        rule_id = f"rule_{current_rule_number}"
        self.processing_rules[rule_id] = {
            "id": current_rule_number,  # 規則ID
            "name": f"處理原則 {current_rule_number}",
            "source_path": "",  # 具體檔案路徑，由用戶稍後設定
            #"source_file": f"Cam{current_rule_number}.jpg",  # 預設檔案名稱，與ID一致
            "source_file": "",  # 新邏輯：初始化為空，將從用戶選擇的路徑自動提取檔名
            "output_path": "",
            "backup_path": "./IMG",
            "resolution": "800x600",
            "timer_interval": self.global_timer_interval_minutes,
            "enabled": True,
            "status": "等待中",
            "last_error": "",
            "error_counter": 0
        }
        
        # 【修正核心】規則建立完成後，再將下一個可用編號加1，供下一次新增使用
        self.next_rule_number += 1
        
        # 更新Treeview顯示
        self.refresh_rule_treeview()
        
        # 自動選中新添加的規則（可選，提升體驗）
        for child in self.rule_tree.get_children():
            values = self.rule_tree.item(child, 'values')
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
        values = self.rule_tree.item(item, 'values')
        rule_id_num = int(values[0])  # 第一列是編號

        # 根據編號找到規則ID
        target_rule_id = None
        for rule_id, rule_data in self.processing_rules.items():
            if rule_data['id'] == rule_id_num:
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
        ttk.Label(main_frame, text="標註名稱:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        name_var = tk.StringVar(value=rule_data['name'])
        name_entry = ttk.Entry(main_frame, textvariable=name_var, width=40)
        name_entry.grid(row=row, column=1, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=5)
        row += 1

        # 2. 來源檔案路徑 (關鍵修改點：選擇單一檔案)
        ttk.Label(main_frame, text="來源檔案:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        source_path_var = tk.StringVar(value=rule_data.get('source_path', ''))
        source_path_entry = ttk.Entry(main_frame, textvariable=source_path_var, width=35)
        source_path_entry.grid(row=row, column=1, sticky=tk.W+tk.E, padx=5, pady=5)

        def browse_source_path():
            # 使用 askopenfilename 來選擇單個圖片檔案
            file_path = filedialog.askopenfilename(
                title="選擇來源圖片檔案",
                filetypes=[("圖片檔案", "*.jpg *.jpeg *.png"), ("所有檔案", "*.*")]
            )
            if file_path:  # 用戶可能取消選擇，所以要判斷
                source_path_var.set(file_path)

        ttk.Button(main_frame, text="瀏覽", command=browse_source_path, width=8).grid(
            row=row, column=2, padx=(5, 0), pady=5
        )
        row += 1

        # 3. 最終目的地路徑 (仍然是資料夾)
        ttk.Label(main_frame, text="最終目的地:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        output_path_var = tk.StringVar(value=rule_data.get('output_path', ''))
        output_path_entry = ttk.Entry(main_frame, textvariable=output_path_var, width=35)
        output_path_entry.grid(row=row, column=1, sticky=tk.W+tk.E, padx=5, pady=5)

        def browse_output_path():
            path = filedialog.askdirectory(title="選擇最終目的地資料夾")
            if path:
                output_path_var.set(path)

        ttk.Button(main_frame, text="瀏覽", command=browse_output_path, width=8).grid(
            row=row, column=2, padx=(5, 0), pady=5
        )
        row += 1

        # 4. 備份路徑 (仍然是資料夾)
        ttk.Label(main_frame, text="備份路徑:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        backup_path_var = tk.StringVar(value=rule_data.get('backup_path', './IMG'))
        backup_path_entry = ttk.Entry(main_frame, textvariable=backup_path_var, width=35)
        backup_path_entry.grid(row=row, column=1, sticky=tk.W+tk.E, padx=5, pady=5)

        def browse_backup_path():
            path = filedialog.askdirectory(title="選擇備份資料夾")
            if path:
                backup_path_var.set(path)

        ttk.Button(main_frame, text="瀏覽", command=browse_backup_path, width=8).grid(
            row=row, column=2, padx=(5, 0), pady=5
        )
        row += 1

        # 5. 縮放解析度
        ttk.Label(main_frame, text="縮放解析度:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        resolution_var = tk.StringVar(value=rule_data.get('resolution', '800x600'))
        resolution_entry = ttk.Entry(main_frame, textvariable=resolution_var, width=15)
        resolution_entry.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(main_frame, text="(格式: 寬x高, 如: 800x600)").grid(
            row=row, column=2, sticky=tk.W, padx=5, pady=5
        )
        row += 1

        # 6. 啟用/停用狀態
        enabled_var = tk.BooleanVar(value=rule_data.get('enabled', True))
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

            if not re.match(r'^\d+x\d+$', resolution_var.get().strip()):
                messagebox.showerror("錯誤", "解析度格式錯誤，請使用 寬x高 格式，如: 800x600")
                return

            # 更新規則數據
            rule_data['name'] = name_var.get().strip()
            rule_data['source_path'] = source_path_var.get().strip()  # 現在是完整檔案路徑
            rule_data['output_path'] = output_path_var.get().strip()
            rule_data['backup_path'] = backup_path_var.get().strip()
            rule_data['resolution'] = resolution_var.get().strip()
            rule_data['enabled'] = enabled_var.get()

            # 刷新Treeview
            self.refresh_rule_treeview()
            edit_window.destroy()
            self.log_message(f"已更新處理原則 #{rule_id_num}: {rule_data['name']}")

        ttk.Button(button_frame, text="儲存變更", command=save_changes, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=edit_window.destroy, width=12).pack(side=tk.LEFT, padx=5)
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
        values = self.rule_tree.item(item, 'values')
        rule_id_num = int(values[0])
        rule_name = values[1]
        
        # 確認刪除
        confirm = messagebox.askyesno(
            "確認刪除",
            f"確定要刪除處理原則 #{rule_id_num} - {rule_name} 嗎？\n\n此操作無法復原！"
        )
        
        if not confirm:
            return
        
        # 根據編號找到規則ID
        target_rule_id = None
        for rule_id, rule_data in self.processing_rules.items():
            if rule_data['id'] == rule_id_num:
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
                             key=lambda x: x[1]['id'])
        
        new_rules = {}
        new_number = 1
        
        for rule_id, rule_data in sorted_rules:
            rule_data['id'] = new_number
            rule_data['source_file'] = f"Cam{new_number}.jpg"
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
        values = self.rule_tree.item(item, 'values')
        rule_id_num = int(values[0])
        rule_name = values[1]
        
        # 根據編號找到規則ID
        target_rule_id = None
        for rule_id, rule_data in self.processing_rules.items():
            if rule_data['id'] == rule_id_num:
                target_rule_id = rule_id
                break
        
        if target_rule_id is None:
            messagebox.showerror("錯誤", "找不到對應的規則")
            return
        
        # 切換狀態
        rule_data = self.processing_rules[target_rule_id]
        new_state = not rule_data['enabled']
        rule_data['enabled'] = new_state
        
        # 更新狀態顯示
        if new_state:
            rule_data['status'] = "等待中"
            rule_data['last_error'] = ""
            status_text = "啟用"
        else:
            rule_data['status'] = "已停用"
            status_text = "停用"
        
        # 刷新Treeview
        self.refresh_rule_treeview()
        self.log_message(f"處理原則 #{rule_id_num}: {rule_name} 已{status_text}")
        self.save_tab4_config()


        #增加參數設定檔 將參數 寫入 此檔案中 以便喚回所有參數 
    def load_tab4_config(self):
        """從 Pic_Process.dat 載入處理原則、排程設定與 UI 狀態"""
        import json
        config_path = "Pic_Process.dat"
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 1. 載入處理原則
                loaded_rules = data.get('processing_rules', {})
                self.processing_rules = loaded_rules
                
                # 2. 載入排程分鐘列表
                self.schedule_minutes = data.get('schedule_minutes', [])
                self.global_timer_interval_minutes = data.get('global_timer_interval_minutes', 10)  # ====== 新增：載入全局定時器間隔 ======



                # ====== 新增：更新TAB4介面上的輸入框顯示 ======
                # 檢查UI輸入框元件和其關聯的變數是否存在
                if hasattr(self, 'timer_interval_var') and self.timer_interval_var is not None:
                    # 將載入的數值（浮點數）轉為字串，設定給輸入框變數
                    self.timer_interval_var.set(str(self.global_timer_interval_minutes))
 
                self.log_message(f"[設定載入] 定時器間隔已設為: {self.global_timer_interval_minutes} 分鐘", level="DEBUG")
                # ==========================================



                
     
                # 3. 載入UI狀態（Treeview欄位寬度）
                if 'ui_state' in data and hasattr(self, 'rule_tree'):
                    ui_state = data['ui_state']
                    # 載入TAB4規則列表的欄寬
                    saved_widths = ui_state.get('tab4_column_widths', {})
                    columns = self.rule_tree['columns']
                    for col in columns:
                        if col in saved_widths:
                            self.rule_tree.column(col, width=saved_widths[col])
                
                # 4. 計算下一個可用的規則編號
                if self.processing_rules:
                    try:
                        max_id = max(rule['id'] for rule in self.processing_rules.values() if isinstance(rule, dict) and 'id' in rule)
                        self.next_rule_number = max_id + 1
                    except ValueError:
                        self.next_rule_number = len(self.processing_rules) + 1
                else:
                    self.next_rule_number = 1
                
                # 5. 刷新Treeview顯示
                if hasattr(self, 'rule_tree') and self.rule_tree.winfo_exists():
                    self.refresh_rule_treeview()
                self.log_message(f"設定檔載入成功：{len(self.processing_rules)} 個處理原則。")
            else:
                self.log_message("未找到設定檔 Pic_Process.dat，將使用初始設定。", level="INFO")
        except json.JSONDecodeError:
            self.log_message("錯誤：設定檔 Pic_Process.dat 格式損壞，無法讀取。", level="ERROR")
        except Exception as e:
            self.log_message(f"載入設定檔時發生未知錯誤: {e}", level="ERROR")


    def save_tab4_config(self):
        """將當前處理原則、排程設定與 UI 狀態保存到 Pic_Process.dat"""
        import json
        config_path = "Pic_Process.dat"
        try:
            # 準備要保存的資料
            data_to_save = {
                'processing_rules': self.processing_rules,
                'schedule_minutes': getattr(self, 'schedule_minutes', []),  # 安全地获取，如果属性不存在则返回空列表
                'global_timer_interval_minutes': getattr(self, 'global_timer_interval_minutes', 10),  # ====== 新增：保存全局定時器間隔 ======
                'ui_state': {
                    # 保存TAB4規則列表的欄位寬度
                    'tab4_column_widths': self._get_tab4_column_widths()
                },
                '_metadata': {
                    'save_time': datetime.now().isoformat(),
                    'version': '1.0'
                }
            }
            # 使用 json.dump 寫入
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            self.log_message(f"設定已保存至 {config_path}")
        except Exception as e:
            self.log_message(f"保存設定檔時發生錯誤: {e}", level="ERROR")
    
    def _get_tab4_column_widths(self):
        """獲取TAB4規則列表Treeview當前的欄位寬度"""
        if not hasattr(self, 'rule_tree'):
            return {}
        widths = {}
        for col in self.rule_tree['columns']:
            widths[col] = self.rule_tree.column(col, 'width')
        return widths

    def on_timer_interval_changed(self, event=None):
        """
        當定時器間隔輸入框內容改變且失去焦點時，更新變數並儲存設定。
        """
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
                self.log_message(f"定時器間隔已從 {old_interval} 分鐘更改為 {new_interval} 分鐘")
            
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
