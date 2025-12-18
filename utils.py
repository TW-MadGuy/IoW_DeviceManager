import hashlib
import re


def calculate_file_hash(file_path, algorithm="md5"):
    """
    計算檔案的哈希值，用於判斷內容是否變更
    這是一個獨立工具函數，不屬於任何類。
    """
    hash_func = hashlib.new(algorithm)
    try:
        with open(file_path, "rb") as f:
            # 以較大的塊讀取檔案，避免記憶體問題
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        # 在獨立工具函數中，我們只拋出異常或返回None，由呼叫者處理日誌
        # 可以選擇打印簡單信息，或直接拋出異常
        print(f"[Utils] 計算檔案哈希值時出錯 {file_path}: {e}")
        return None


def validate_hex(value):
    """驗證16進位字串"""
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def validate_uuid(value):
    """驗證UUID - 接受兩種格式"""
    # 轉為大寫並去除空白
    value = value.strip().upper()

    # 檢查是否為標準格式（帶連字號）
    standard_pattern = r"^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$"

    # 檢查是否為連續32位十六進位
    continuous_pattern = r"^[0-9A-F]{32}$"

    if re.match(standard_pattern, value):
        # 標準格式，驗證通過
        return True
    elif re.match(continuous_pattern, value):
        # 連續32位格式，驗證通過
        return True
    else:
        # 兩種格式都不符合
        return False


def normalize_uuid(uuid_str):
    """將UUID統一轉換為標準格式"""
    if not uuid_str:
        return ""

    # 轉為大寫並去除空白
    uuid_str = uuid_str.strip().upper()

    # 如果已經是標準格式，直接返回
    standard_pattern = r"^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$"
    if re.match(standard_pattern, uuid_str):
        return uuid_str

    # 如果是連續32位，轉換為標準格式
    continuous_pattern = r"^[0-9A-F]{32}$"
    if re.match(continuous_pattern, uuid_str):
        # 轉換為標準格式：8-4-4-4-12
        return f"{uuid_str[0:8]}-{uuid_str[8:12]}-{uuid_str[12:16]}-{uuid_str[16:20]}-{uuid_str[20:32]}"

    # 如果都不符合，返回原值（將在驗證時被拒絕）
    return uuid_str

def format_rtu_id(decimal_value):
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
