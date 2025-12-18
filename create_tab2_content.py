import tkinter as tk
from tkinter import ttk


def create_tab2_content(self):
    """創建通訊設定Tab的內容"""
    main_frame = ttk.Frame(self.tab2)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    # 通訊協定設定
    protocol_frame = ttk.LabelFrame(main_frame, text="通訊協定設定", padding=10)
    protocol_frame.pack(fill=tk.X, pady=(0, 10))

    ttk.Label(protocol_frame, text="通訊協定:").grid(
        row=0, column=0, sticky=tk.W, padx=5, pady=5
    )
    self.protocol_var = tk.StringVar(value="MODBUS RTU")
    protocol_combo = ttk.Combobox(
        protocol_frame,
        textvariable=self.protocol_var,
        values=["MODBUS RTU", "MODBUS TCP", "OPC UA", "MQTT"],
        width=15,
    )
    protocol_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

    # 通訊參數設定
    comm_frame = ttk.LabelFrame(main_frame, text="通訊參數", padding=10)
    comm_frame.pack(fill=tk.X, pady=(0, 10))

    ttk.Label(comm_frame, text="通訊埠:").grid(
        row=0, column=0, sticky=tk.W, padx=5, pady=5
    )
    self.port_entry = ttk.Entry(comm_frame, width=15)
    self.port_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
    self.port_entry.insert(0, "COM1")

    ttk.Label(comm_frame, text="鮑率:").grid(
        row=1, column=0, sticky=tk.W, padx=5, pady=5
    )
    self.baudrate_var = tk.StringVar(value="9600")
    baudrate_combo = ttk.Combobox(
        comm_frame,
        textvariable=self.baudrate_var,
        values=[
            "1200",
            "2400",
            "4800",
            "9600",
            "19200",
            "38400",
            "57600",
            "115200",
        ],
        width=15,
    )
    baudrate_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

    # 測試通訊按鈕
    test_button = ttk.Button(
        main_frame, text="測試通訊連線", command=self.test_communication
    )
    test_button.pack(pady=10)