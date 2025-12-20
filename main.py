# main.py
import customtkinter as ctk
import tkinter as tk
from ram_logger import RAMLogger  # 呼叫您剛剛建立的 Log 模組
# from tabs.tab1_uuid import Tab1UUID  # 等我們寫好這兩個檔案再取消註解
from tabs.tab4_backup import Tab4Backup


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. 主視窗設定
        self.title("IoW 設備與檔案管理器 (重構版)")
        self.geometry("800x600")

        # 3. 上方功能分頁 (Tabview)
        self.tabview = ctk.CTkTabview(self, width=780, height=380)
        self.tabview.pack(padx=10, pady=5, fill="both", expand=True)

        self.tab1 = self.tabview.add("UUID傳送 (Tab1)")
        self.tab2 = self.tabview.add("預留 (Tab2)")
        self.tab3 = self.tabview.add("預留 (Tab3)")
        self.tab4 = self.tabview.add("檔案備份 (Tab4)")

        # 4. [修正處] 下方 RAM Log 視窗 (先建立 Logger，因為 Tab4 需要用到它)
        self.log_label = ctk.CTkLabel(self, text="系統執行紀錄 (RAM LOG):", anchor="w")
        self.log_label.pack(padx=15, pady=(5, 0), fill="x")

        # 正確的初始化：傳入 self 作為 master
        self.logger = RAMLogger(self, max_lines=2000, height=150)
        self.logger.pack(padx=10, pady=(0, 10), fill="x")

        # 5. [關鍵順序] 有了 logger 之後，再建立 Tab4 的內容
        self.tab4_content = Tab4Backup(master=self.tab4, logger=self.logger)
        self.tab4_content.pack(fill="both", expand=True)

        # 6. 建立引用供引擎使用
        self.tab4_ref = self.tab4_content

        # 7. 初始化背景任務與分頁內容
        self.init_tabs()

        # 測試一下 Log 功能
        self.logger.write_log("系統初始化完成，準備就緒。")

    def init_tabs(self):
            # 原本的 tab1 暫時保留 label
        ctk.CTkLabel(self.tab1, text="Tab 1: UUID 配置介面預留區").pack(pady=20)

        # 實例化真正的 Tab 4 並傳入 logger
        self.t4_content = Tab4Backup(master=self.tab4, logger=self.logger)
        self.t4_content.pack(fill="both", expand=True)

        # 等檔案建立後，改用以下寫法：
        # self.t1_content = Tab1UUID(master=self.tab1, logger=self.logger)
        # self.t1_content.pack(fill="both", expand=True)


if __name__ == "__main__":
    # 設定外觀風格
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = MainApp()
    app.mainloop()
