import re

# 用戶指定的簡譜基礎映射：原譜音符 -> 轉換後音符。
JIANPU_BASE_MAPPING = {
    '1': '4',
    '2': '5',
    '3': '6',
    '4': 'b7',
    '5': '1',
    '6': '2',
    '7': '3'
}

def clean_jianpu_text(text):
    """
    清理簡譜字串中的雜訊。
    特別優化：保留連續空格以維持 OCR 抓到的原始排版。
    """
    if not text:
        return ""
        
    # 正規表達式只保留數字 1-7, 高音符號 ', 空格 \s, 換行 \n, 小節線 |
    cleaned = re.sub(r"[^1-7'\s\|]", "", text)
    
    # 逐行檢查
    lines = cleaned.split('\n')
    
    # 移除「完全空白或只有空格」的行，但【不要】用 strip() 改變原始行的內容，
    # 這樣才能保留每一行開頭的縮排與音符之間的相對距離。
    non_empty_lines = [line for line in lines if line.strip() != ""]
    
    return '\n'.join(non_empty_lines)


def convert_sheet_music(input_text):
    """將傳入的簡譜字串進行轉換。處理映射和高音。"""
    if not input_text:
        return ""

    # 自動生成高音映射：原譜音符' -> 轉換後音符' (例如 1' -> 4')
    base_mapping = JIANPU_BASE_MAPPING
    high_mapping = {k + "'": v + "'" for k, v in base_mapping.items()}
    complete_mapping = {**base_mapping, **high_mapping}

    # 使用正規表達式匹配 \d' (高音) 或 \d (基礎)。
    # 注意：\d' 必須寫在前面優先匹配，否則 1' 會被拆成 1 和 '
    pattern = r"(\d')|(\d)"

    def replace_match(match):
        # 獲取匹配的文字。
        note_with_high = match.group(1) # 例如：1'
        note_single = match.group(2)    # 例如：1
        
        if note_with_high:
            # 查找高音映射，如果找不到（例如 8'），則保留原樣
            return complete_mapping.get(note_with_high, note_with_high)
        elif note_single:
            # 查找基礎映射，如果找不到（例如 8 或 9），則保留原樣
            return complete_mapping.get(note_single, note_single)
        return match.group(0) # 預防性回傳

    # 使用 sub 進行替換，不在 pattern 內的字元（如空格、|）會自動原樣保留
    converted_text = re.sub(pattern, replace_match, input_text)
    return converted_text


def process_jianpu_ocr(ocr_text):
    """
    完整的簡譜 OCR 處理流程。
    提供給 app.py 呼叫的統一接口。
    """
    # 1. 先清理原始 OCR 結果中的歌詞和雜訊 (保留空格排版)
    cleaned_original = clean_jianpu_text(ocr_text)
    
    # 2. 針對清理後的乾淨字串進行移調轉換
    converted_final = convert_sheet_music(cleaned_original)
    
    # 回傳清理後的原譜，以及轉換後的新譜
    return cleaned_original, converted_final
