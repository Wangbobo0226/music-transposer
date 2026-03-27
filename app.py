import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import easyocr
import os

# --- 1. 移調邏輯 (支援高音符號) ---
def transpose_for_clarinet(note_str):
    """
    原譜的 1 -> 4
    原譜的 2 -> 5
    原譜的 3 -> 6
    原譜的 4 -> 7
    原譜的 5 -> 1
    原譜的 6 -> 2
    原譜的 7 -> 3
    保留後面的高音符號 (例如 1' -> 4')
    """
    mapping = {
        '1': '4', '2': '5', '3': '6', '4': '7',
        '5': '1', '6': '2', '7': '3'
    }
    
    if not note_str: return note_str
    
    # 拆分主音符與高音符號
    base_note = note_str[0]
    modifier = note_str[1:] # 取得後面的所有 "'"
    
    # 轉換主音符，並將高音符號加回去
    transposed_base = mapping.get(base_note, base_note)
    return transposed_base + modifier

# --- 2. 座標參數 ---
GRID_X_START = 100   
GRID_Y_START = 222   
COL_GAP = 68.5       
ROW_GAP = 162.2      
COLS_PER_ROW = 14    

# --- 3. 網頁配置 ---
st.set_page_config(page_title="專業格式校正器", layout="centered")
st.title("🎼 豎笛轉譜：支援高音記號版")

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()
TEMPLATE_FILE = "Bb36e564c1fa1f3c3db.jpg"

uploaded_file = st.file_uploader("上傳手寫簡譜照片 (請確保高音 ' 標示清晰)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    if not os.path.exists(TEMPLATE_FILE):
        st.error(f"找不到範本檔案 {TEMPLATE_FILE}")
    else:
        try:
            in_bytes = uploaded_file.read()
            pil_input = Image.open(io.BytesIO(in_bytes)).convert('RGB')
            orig_w, orig_h = pil_input.size
            
            pil_temp = Image.open(TEMPLATE_FILE).convert('RGB')
            temp_w, temp_h = pil_temp.size
            draw = ImageDraw.Draw(pil_temp)
            
            if st.button("🚀 生成包含高音的電子譜"):
                with st.spinner('正在分析位置與高音符號...'):
                    img_cv = cv2.cvtColor(np.array(pil_input), cv2.COLOR_RGB2BGR)
                    results = reader.readtext(img_cv)
                    
                    try:
                        font = ImageFont.load_default(size=60)
                    except:
                        font = ImageFont.load_default()

                    count = 0
                    for (bbox, text, prob) in results:
                        if prob < 0.15: continue
                        
                        # 核心修正：將數字與對應的高音符號綁定成一個列表
                        # 範例： text = "33'2" 會被轉成 parsed_notes = ["3", "3'", "2"]
                        parsed_notes = []
                        for c in text:
                            if c.isdigit():
                                parsed_notes.append(c)
                            elif c in ["'", "’", "`"] and len(parsed_notes) > 0:
                                # 把符號加到前一個數字身上
                                parsed_notes[-1] += "'"
                        
                        if parsed_notes:
                            # 1. 計算在原圖中的百分比位置
                            rx = (bbox[0][0] + bbox[2][0]) / 2 / orig_w
                            ry = (bbox[0][1] + bbox[2][1]) / 2 / orig_h
                            
                            # 2. 映射到電子譜的大約座標
                            target_x_raw = rx * temp_w
                            target_y_raw = ry * temp_h
                            
                            # 3. 尋找最接近的格子索引
                            col_idx = round((target_x_raw - GRID_X_START) / COL_GAP)
                            row_idx = round((target_y_raw - GRID_Y_START) / ROW_GAP)
                            
                            # 限制範圍
                            row_idx = max(0, min(9, row_idx))
                            col_idx = max(0, min(COLS_PER_ROW - 1, col_idx))

                            # 4. 逐個音符填入
                            for i, note in enumerate(parsed_notes):
                                final_col = col_idx + i
                                if final_col >= COLS_PER_ROW: break
                                
                                draw_x = GRID_X_START + (final_col * COL_GAP)
                                draw_y = GRID_Y_START + (row_idx * ROW_GAP)
                                
                                trans_note = transpose_for_clarinet(note)
                                
                                # 繪製音符
                                draw.text((draw_x, draw_y), trans_note, fill=(180, 0, 0), 
                                          font=font, stroke_width=1, anchor="mm")
                                count += 1
                    
                    if count > 0:
                        st.success(f"✅ 對位完成！已處理高音符號，共填入 {count} 個音符。")
                        st.image(np.array(pil_temp), use_container_width=True)
                        
                        buf = io.BytesIO()
                        pil_temp.save(buf, format="PNG")
                        st.download_button("📥 下載對位修正譜", buf.getvalue(), "HighPitch_Accurate_Score.png", "image/png")
                        
        except Exception as e:
            st.error(f"執行錯誤：{e}")
