# utils.py

def get_mapping():
    """建立並回傳簡譜轉換的字典映射"""
    # 基礎轉換規則
    base_mapping = {
        '1': '4',
        '2': '5',
        '3': '6',
        '4': '7',
        '5': '1',
        '6': '2',
        '7': '3'
    }
    
    # 自動生成高音的轉換規則 (例如: "1'" -> "4'")
    high_mapping = {k + "'": v + "'" for k, v in base_mapping.items()}
    
    # 將基礎音與高音規則合併
    return {**base_mapping, **high_mapping}

def convert_sheet_music(input_text):
    """將傳入的簡譜字串進行轉換"""
    if not input_text:
        return ""
        
    mapping = get_mapping()
    converted_text = ""
    
    i = 0
    while i < len(input_text):
        # 先檢查是否有兩個字元的組合 (例如 1', 2')
        if i + 1 < len(input_text) and input_text[i:i+2] in mapping:
            converted_text += mapping[input_text[i:i+2]]
            i += 2
        # 再檢查單一數字
        elif input_text[i] in mapping:
            converted_text += mapping[input_text[i]]
            i += 1
        else:
            # 如果不是數字 (例如空格、小節線 | 等)，則保留原樣
            converted_text += input_text[i]
            i += 1
            
    return converted_text
