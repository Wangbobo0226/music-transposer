import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
import easyocr
import os

# --- 1. 移調與繪圖邏輯 ---
def transpose_for_clarinet(note_str):
    try:
        if note_str.isdigit():
            val = int(note_str)
            return str((val + 2 - 1) % 7 + 1)
    except: pass
    return note_str

# --- 2. 網頁配置 ---
st.set_page_config(page_title="精準對位轉譜器", layout="centered")
st.title("🎼 豎笛專業轉譜：1:1 精準對位版")
st.markdown("此版本會根據手寫稿的**原始位置**，將移調音符精確填入數位範本中。")

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
            # 讀取手寫稿並獲取尺寸
            in_bytes = uploaded_file.read()
            pil_input = Image.open(io.BytesIO(in_bytes)).convert('RGB')
            orig_w, orig_h = pil_input.size
            
            # 準備數位底圖
            pil_temp = Image.open(TEMPLATE_FILE).convert('RGB')
            temp_w, temp_h = pil_temp.size
            draw = ImageDraw.Draw(pil_temp)
            
            if st.button("🚀 生成 1:1 精準對位譜"):
                with st.spinner('正在計算座標映射中...'):
                    img_cv = cv2.cvtColor(np.array(pil_input), cv2.COLOR_RGB2BGR)
                    results = reader.readtext(img_cv)
                    
                    try:
                        font = ImageFont.load_default(size=55)
                    except:
                        font = ImageFont.load_default()

                    count = 0
                    for (bbox, text, prob) in results:
                        cleaned = "".join([c for c in text if c.isdigit()])
                        if cleaned and prob > 0.2:
                            # 計算手寫稿中心點比例 (0.0 ~ 1.0)
                            center_x = (bbox[0][0] + bbox[2][0]) / 2 / orig_w
                            center_y = (bbox[0][1] + bbox[2][1]) / 2 / orig_h
                            
                            # 映射到範本座標
                            target_x_base = center_x * temp_w
                            target_y = center_y * temp_h
                            
                            # 如果辨識出一串數字 (如 33)，逐字拆解並拉開一點點間距
                            for i, char in enumerate(cleaned):
                                trans_note = transpose_for_clarinet(char)
                                # 水平微調避免疊字
                                offset_x = (i - (len(cleaned)-1)/2) * 45 
                                final_x = target_x_base + offset_x
                                
                                # 繪製：深紅色、中心對齊
                                draw.text((final_x, target_y), trans_note, fill=(200, 0, 0), 
                                          font=font, stroke_width=1, anchor="mm")
                                count += 1
                    
                    if count > 0:
                        st.success(f"✅ 生成完畢！已對位填入 {count} 個音符。")
                        st.image(np.array(pil_temp), use_container_width=True)
                        
                        buf = io.BytesIO()
                        pil_temp.save(buf, format="PNG")
                        st.download_button("📥 下載精準對位譜", buf.getvalue(), "Clarinet_Perfect_Match.png", "image/png")
                    else:
                        st.warning("未能辨識音符。")
                        
        except Exception as e:
            st.error(f"執行錯誤：{e}")
