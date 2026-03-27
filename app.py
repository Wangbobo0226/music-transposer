import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import easyocr
import os

# --- 1. 移調與座標參數 ---
def transpose_for_clarinet(note_str):
    try:
        if note_str.isdigit():
            val = int(note_str)
            return str((val + 2 - 1) % 7 + 1)
    except: pass
    return note_str

# 專業範本 Bb36e564c1fa1f3c3db.jpg 的格點定義
GRID_ORIGIN_X = 85   # 第一格中心 X
GRID_ORIGIN_Y = 160  # 第一列中心 Y
COL_SPACING = 68.5   # 每一格的寬度
ROW_SPACING = 162    # 每一列的高度
TOTAL_COLS = 14      # 每行 14 格

# --- 2. 網頁配置 ---
st.set_page_config(page_title="專業級對齊轉譜器", layout="centered")
st.title("🎷 豎笛專業轉譜：格點自動吸附版")
st.markdown("此版本會自動將辨識到的音符**吸附**到最接近的格位中心，確保排版完美整齊。")

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()

TEMPLATE_FILE = "Bb36e564c1fa1f3c3db.jpg"

uploaded_file = st.file_uploader("上傳手寫簡譜照片", type=["jpg", "jpeg", "png"])

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
            
            if st.button("🚀 生成專業對齊電子譜"):
                with st.spinner('正在精確對位與吸附中...'):
                    img_cv = cv2.cvtColor(np.array(pil_input), cv2.COLOR_RGB2BGR)
                    results = reader.readtext(img_cv)
                    
                    try:
                        font = ImageFont.load_default(size=60)
                    except:
                        font = ImageFont.load_default()

                    count = 0
                    for (bbox, text, prob) in results:
                        cleaned = "".join([c for c in text if c.isdigit()])
                        if cleaned and prob > 0.2:
                            # 1. 計算在手寫稿上的比例位置
                            rx = (bbox[0][0] + bbox[2][0]) / 2 / orig_w
                            ry = (bbox[0][1] + bbox[2][1]) / 2 / orig_h
                            
                            # 2. 映射到範本座標
                            raw_tx = rx * temp_w
                            raw_ty = ry * temp_h
                            
                            # 3. [核心] 格點吸附邏輯
                            # 判斷這是在第幾行、第幾列
                            col_idx = round((raw_tx - GRID_ORIGIN_X) / COL_SPACING)
                            row_idx = round((raw_ty - GRID_ORIGIN_Y) / ROW_SPACING)
                            
                            # 限制範圍避免畫到邊界外
                            col_idx = max(0, min(TOTAL_COLS - 1, col_idx))
                            row_idx = max(0, min(9, row_idx))

                            # 4. 逐字拆解並填入連續格子
                            for i, char in enumerate(cleaned):
                                current_col = col_idx + i
                                if current_col >= TOTAL_COLS: break # 避免爆行
                                
                                # 強制鎖定中心座標
                                final_x = GRID_ORIGIN_X + (current_col * COL_SPACING)
                                final_y = GRID_ORIGIN_Y + (row_idx * ROW_SPACING)
                                
                                trans_note = transpose_for_clarinet(char)
                                draw.text((final_x, final_y), trans_note, fill=(180, 0, 0), 
                                          font=font, stroke_width=1, anchor="mm")
                                count += 1
                    
                    if count > 0:
                        st.success(f"✅ 生成完畢！已將 {count} 個音符吸附至格位。")
                        st.image(np.array(pil_temp), use_container_width=True)
                        
                        buf = io.BytesIO()
                        pil_temp.save(buf, format="PNG")
                        st.download_button("📥 下載專業電子譜", buf.getvalue(), "Pro_Aligned_Score.png", "image/png")
                    else:
                        st.warning("辨識不到音符。")
                        
        except Exception as e:
            st.error(f"執行錯誤：{e}")
                        
        except Exception as e:
            st.error(f"執行錯誤：{e}")
