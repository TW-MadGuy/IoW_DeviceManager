import hashlib
import os


def calculate_file_hash(file_path, algorithm='md5'):
    """
    計算檔案的哈希值，用於判斷內容是否變更
    這是一個獨立工具函數，不屬於任何類。
    """
    hash_func = hashlib.new(algorithm)
    try:
        with open(file_path, 'rb') as f:
            # 以較大的塊讀取檔案，避免記憶體問題
            for chunk in iter(lambda: f.read(4096), b''):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        # 在獨立工具函數中，我們只拋出異常或返回None，由呼叫者處理日誌
        # 可以選擇打印簡單信息，或直接拋出異常
        print(f"[Utils] 計算檔案哈希值時出錯 {file_path}: {e}")
        return None
    

