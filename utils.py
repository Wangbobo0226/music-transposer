# utils.py - 專門處理樂理與移調的工具組

def get_transpose_info(instrument_name):
    """
    根據樂器名稱，回傳需要移動的半音數 (Semitones)
    """
    transpose_table = {
        "豎笛 (Bb)": 2,          # 升高大二度
        "小號 (Bb)": 2,          # 升高大二度
        "中音薩克斯風 (Eb)": 9,   # 升高大六度 (或降低小三度)
        "長笛 (C)": 0            # 不用動
    }
    return transpose_table.get(instrument_name, 0)

def transpose_numbered_note(note_str, shift):
    """
    處理單個簡譜數字的移調
    note_str: 字串格式的數字 '1'~'7'
    shift: 要移動的半音數量
    """
    # 簡譜 1 2 3 4 5 6 7 對應的半音階位置 (C大調為例)
    semitone_map = {
        '1': 0, '2': 2, '3': 4, '4': 5, '5': 7, '6': 9, '7': 11
    }
    # 反向查找表
    reverse_map = {v: k for k, v in semitone_map.items()}
    
    if note_str in semitone_map:
        original_semi = semitone_map[note_str]
        # 計算新位置 (12格一循環)
        new_semi = (original_semi + shift) % 12
        
        # 尋找最接近的數字 (處理非正準音
