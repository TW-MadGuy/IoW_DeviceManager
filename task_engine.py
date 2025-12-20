import os
import time
import hashlib
import threading
import shutil
from datetime import datetime
from PIL import Image

class TaskEngine:
    def __init__(self, tab4_ui, logger):
        self.ui = tab4_ui
        self.logger = logger
        self.is_running = True
        self.last_triggered_minute = -1
        self.next_run_time = 0
        
        # 啟動背景執行緒 (守護進程)
        self.thread = threading.Thread(target=self._main_loop, daemon=True)
        self.thread.start()

    def _get_hash(self, filepath):
        """計算檔案 MD5 (F3 關卡)"""
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except:
            return "hash_error"

    def _process_rule(self, rule):
        """三關卡邏輯判定 (F1 -> F2 -> F3)"""
        src_path = os.path.join(rule['source_dir'], rule['source_filename'])
        
        # --- F1: 檔案存在檢查 ---
        if not os.path.exists(src_path):
            rule['count_missing'] += 1
            rule['status'] = "異常"  # 標註異常
            self._handle_restore(rule)
            return

        try:
            # --- F2: 結構完整檢查 ---
            with Image.open(src_path) as img:
                img.verify()
            
            # --- F3: 內容變化檢查 ---
            current_hash = self._get_hash(src_path)
            if current_hash == rule['last_hash']:
                rule['count_no_update'] += 1
                rule['status'] = "異常"  # 標註異常
                self._handle_restore(rule)
                return
            
            # --- 合格路徑 ---
            rule['last_hash'] = current_hash
            rule['status'] = "正常"  # 通過檢查
            self._save_images(rule, src_path)

        except Exception:
            rule['count_broken'] += 1
            rule['status'] = "異常"  # 標註異常
            self._handle_restore(rule)

    def _save_images(self, rule, src_path):
        """生成備份檔 -o 與 -s"""
        out_dir = rule['output_dir']
        if not os.path.exists(out_dir): os.makedirs(out_dir)
        
        base_name = os.path.splitext(rule['source_filename'])[0]
        
        try:
            with Image.open(src_path) as img:
                # 儲存原始尺寸檔 (-o)
                img.save(os.path.join(out_dir, f"{base_name}-o.jpg"))
                
                # 儲4儲存縮放檔 (-s)
                img_s = img.resize((rule['target_x'], rule['target_y']))
                img_s.save(os.path.join(out_dir, f"{base_name}-s.jpg"))
                
            self.logger.write_log(f"規則 {rule['id']} ({rule['location']}) 檢查通過，備份完成。")
        except Exception as e:
            self.logger.write_log(f"規則 {rule['id']} 儲存失敗: {e}")

    def _handle_restore(self, rule):
        """執行還原：從 output_dir 搬移到 restore_dir"""
        # 計算總異常次數
        total_errors = rule['count_broken'] + rule['count_no_update'] + rule['count_missing']
        
        # 決定還原目的地 (如果沒設 restore_dir，就用來源目錄或輸出目錄)
        restore_dest = rule.get('restore_dir') or rule['output_dir']
        if not os.path.exists(restore_dest): os.makedirs(restore_dest)

        base_name = os.path.splitext(rule['source_filename'])[0]
        
        # 奇數次還原 -s, 偶數次還原 -o
        restore_suffix = "-s.jpg" if total_errors % 2 != 0 else "-o.jpg"
        source_file = os.path.join(rule['output_dir'], f"{base_name}{restore_suffix}")
        target_file = os.path.join(restore_dest, f"{base_name}.jpg")

        if os.path.exists(source_file):
            shutil.copy(source_file, target_file)
            self.logger.write_log(f"規則 {rule['id']} 異常! 已還原備份檔 {restore_suffix} 至目的地。")
        else:
            self.logger.write_log(f"規則 {rule['id']} 嚴重錯誤: 找不到備份檔可還原。")

    def _main_loop(self):
        """計時器核心循環"""
        while self.is_running:
            mode = self.ui.timer_mode.get()
            setting = self.ui.timer_setting.get()
            now = time.time()

            if mode == "固定秒數":
                try:
                    interval = float(setting)
                    if self.next_run_time == 0: self.next_run_time = now + interval
                    
                    remaining = self.next_run_time - now
                    if remaining <= 0:
                        self._trigger_scan()
                        self.next_run_time = now + interval
                    else:
                        self.ui.countdown_text.set(f"下次掃描倒數: {int(remaining)} 秒")
                except: pass

            elif mode == "指定分鐘":
                try:
                    target_minutes = [int(m.strip()) for m in setting.split(',')]
                    curr_time = datetime.now()
                    curr_min = curr_time.minute
                    
                    if curr_min in target_minutes and curr_min != self.last_triggered_minute:
                        self._trigger_scan()
                        self.last_triggered_minute = curr_min
                    
                    self.ui.countdown_text.set(f"定時掃描: {setting} 分")
                except: pass

            time.sleep(1)

    def _trigger_scan(self):
        """全域掃描動作"""
        self.logger.write_log(">>> [全域輪詢啟動] <<<")
        for rule in self.ui.rules_data:
            if rule['enabled'] and rule['source_filename']:
                self._process_rule(rule)
        
        # 掃描完後，叫 UI 更新畫面
        self.ui.after(0, self.ui._refresh_tree)