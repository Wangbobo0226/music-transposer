import re

# 用戶指定的簡譜基礎映射：原譜音符 -> 轉換後音符。
JIANPU_BASE_MAPPING = {
    '1': '4',
    '2': '5',
    '3': '6',
    '4': '7',
    '5': '1',
    '6': '2',
    '7': '3'
}

def clean_jianpu_text(text):
    """清理簡譜字串中的雜訊。保留數字, ', 空格, 換行, |。"""
    if not text:
        return ""
    # 正規表達式只保留數字 1-7, 高音符號 ', 空格, 換行 \n, 小節線 |。
    cleaned = re.sub(r"[^1-7'\s\|]", "", text)
    # 移除過多的換行符。
    cleaned = '\n'.join([line.strip() for line in cleaned.split('\n') if line.strip()])
    return cleaned

def convert_sheet_music(input_text):
    """將傳入的簡譜字串進行轉換。處理映射和高音。"""
    if not input_text:
        return ""

    # 生成高音映射：原譜音符' -> 轉換後音符'。
    base_mapping = JIANPU_BASE_MAPPING
    high_mapping = {k + "'": v + "'" for k, v in base_mapping.items()}
    complete_mapping = {**base_mapping, **high_mapping}

    # 使用正規表達式匹配 \d' (高音) 或 \d (基礎)。
    # \d' 會比 \d 優先匹配，這很重要。
    pattern = r"(\d')|(\d)"

    def replace_match(match):
        # 獲取匹配的文字。
        note_with_high = match.group(1) # 例如：1'
        note_single = match.group(2) # 例如：1
        
        if note_with_high:
            # 查找高音映射。如果找不到，則保留原樣。
            return complete_mapping.get(note_with_high, note_with_high)
        elif note_single:
            # 查找基礎映射。如果找不到，則保留原樣。
            return complete_mapping.get(note_single, note_single)
        return match.group(0) # 預防性。

    # 使用 sub 和一個自定義替換函數來保留其餘字符（空格, 換行, |）。
    converted_text = re.sub(pattern, replace_match, input_text)
    return converted_text

def process_jianpu_ocr(ocr_text):
    """完整的簡譜 OCR 處理流程。先清理，再轉換。"""
    # 先清理原始 OCR 結果中的歌詞和雜訊。
    cleaned_original = clean_jianpu_text(ocr_text)
    # 再進行移調轉換。
    converted_final = convert_sheet_music(cleaned_original)
    # 最後再次清理轉換後的結果，以移除 OCR 可能生成的不尋常符號。
    final_cleaned = clean_jianpu_text(converted_final)
    return cleaned_original, final_cleaned
