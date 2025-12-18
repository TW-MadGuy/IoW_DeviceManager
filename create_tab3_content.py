import tkinter as tk
from tkinter import ttk


def create_tab3_content(self):
    """創建系統設定Tab的內容"""
    main_frame = ttk.Frame(self.tab3)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    # 儲存設定
    save_frame = ttk.LabelFrame(main_frame, text="儲存設定", padding=10)
    save_frame.pack(fill=tk.X, pady=(0, 10))

    ttk.Label(save_frame, text="自動儲存間隔(分鐘):").grid(
        row=0, column=0, sticky=tk.W, padx=5, pady=5
    )
    self.auto_save_var = tk.StringVar(value="5")
    auto_save_entry = ttk.Entry(
        save_frame, textvariable=self.auto_save_var, width=10
    )
    auto_save_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

    # 日誌設定
    log_frame = ttk.LabelFrame(main_frame, text="日誌設定", padding=10)
    log_frame.pack(fill=tk.X, pady=(0, 10))

    self.log_level_var = tk.StringVar(value="INFO")
    ttk.Radiobutton(
        log_frame, text="DEBUG", variable=self.log_level_var, value="DEBUG"
    ).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    ttk.Radiobutton(
        log_frame, text="INFO", variable=self.log_level_var, value="INFO"
    ).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
    ttk.Radiobutton(
        log_frame, text="WARNING", variable=self.log_level_var, value="WARNING"
    ).grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
    ttk.Radiobutton(
        log_frame, text="ERROR", variable=self.log_level_var, value="ERROR"
    ).grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)

    # Log檔案大小設定
    log_size_frame = ttk.LabelFrame(main_frame, text="Log檔案大小設定", padding=10)
    log_size_frame.pack(fill=tk.X, pady=(0, 10))

    ttk.Label(log_size_frame, text="最大Log檔案大小:").grid(
        row=0, column=0, sticky=tk.W, padx=5, pady=5
    )
    self.log_size_var = tk.StringVar(value="100")
    log_size_combo = ttk.Combobox(
        log_size_frame,
        textvariable=self.log_size_var,
        values=["50", "100", "200", "300", "500", "1024", "5120"],
        width=10,
    )
    log_size_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
    ttk.Label(log_size_frame, text="KB").grid(
        row=0, column=2, sticky=tk.W, padx=5, pady=5
    )

    # Log檔案管理按鈕
    log_manage_button = ttk.Button(
        log_size_frame, text="管理Log檔案", command=self.manage_log_file
    )
    log_manage_button.grid(row=0, column=3, sticky=tk.W, padx=(20, 5), pady=5)

    # 立即儲存按鈕
    save_button = ttk.Button(
        main_frame, text="立即儲存設定", command=self.save_config
    )
    save_button.pack(pady=10)

    # 載入設定按鈕
    load_button = ttk.Button(main_frame, text="載入設定", command=self.load_config)
    load_button.pack(pady=5)