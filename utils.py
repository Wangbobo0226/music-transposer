def get_transpose_info(instrument_name):
    # 設定各樂器的移調半音數
    transpose_table = {
        "豎笛 (Bb)": 2,
        "小號 (Bb)": 2,
        "中音薩克斯風 (Eb)": 9,
        "長笛 (C)": 0
    }
    return transpose_table.get(instrument_name, 0)

def transpose_numbered_note(note_str, shift):
    # 簡化的 1-7 移調邏輯
    try:
        if note_str.isdigit():
            val = int(note_str)
            # 確保在 1-7 之間循環 (這裡僅為基礎邏輯範例)
            new_val = (val + shift - 1) % 7 + 1
            return str(new_val)
    except:
        pass
    return note_str
