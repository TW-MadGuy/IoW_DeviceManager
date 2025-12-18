from device_manager import show_normal_operation


import tkinter as tk
from tkinter import ttk


def create_tab1_content(self):
    """創建設備列表Tab的內容"""
    # Treeview框架 - 最大化空間
    treeview_frame = ttk.Frame(self.tab1)
    treeview_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=(1, 0))

    # 建立Treeview來顯示設備列表
    columns = ("站名", "RTU ID", "UUID", "類型", "延遲(mS)", "啟用/停止")
    self.device_tree = ttk.Treeview(
        treeview_frame, columns=columns, show="headings")

    # 設定列標題
    for col in columns:
        self.device_tree.heading(col, text=col)
        self.device_tree.column(col, width=self.column_widths.get(col, 100))

    # 設定啟用/停止的標籤顏色
    self.device_tree.tag_configure("enabled", foreground="green")
    self.device_tree.tag_configure("disabled", foreground="gray")

    # 綁定Treeview事件
    self.device_tree.bind("<<TreeviewSelect>>", self.on_treeview_select)
    self.device_tree.bind("<Double-1>", self.on_treeview_double_click)
    self.device_tree.bind("<Button-1>", self.on_treeview_click)  # 新增點擊事件

    # 添加垂直滾軸
    v_scrollbar = ttk.Scrollbar(
        treeview_frame, orient=tk.VERTICAL, command=self.device_tree.yview
    )
    self.device_tree.configure(yscrollcommand=v_scrollbar.set)

    # 添加水平滾軸
    h_scrollbar = ttk.Scrollbar(
        treeview_frame, orient=tk.HORIZONTAL, command=self.device_tree.xview
    )
    self.device_tree.configure(xscrollcommand=h_scrollbar.set)

    # 使用grid佈局
    self.device_tree.grid(row=0, column=0, sticky="nsew")
    v_scrollbar.grid(row=0, column=1, sticky="ns")
    h_scrollbar.grid(row=1, column=0, sticky="ew")

    # 配置網格權重
    treeview_frame.grid_rowconfigure(0, weight=1)
    treeview_frame.grid_columnconfigure(0, weight=1)

    # 操作區域框架（深灰色背景，在Treeview下方）
    self.operation_frame = ttk.Frame(
        self.tab1, style="Border.TFrame", height=80)
    self.operation_frame.pack(fill=tk.X, padx=1, pady=(5, 1))

    # 創建操作區域的內容（初始為正常模式）
    self.create_normal_operation()

    # 初始化時顯示正常模式
    show_normal_operation()