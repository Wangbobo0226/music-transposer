import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
import io
import easyocr
import os

# --- 1. 豎笛移調邏輯 (+2) ---
def transpose_for_clarinet(note_str):
    try:
        if note_str.isdigit():
            val = int(note_str)
            # 簡譜 1-7 循環
            new_val = (val + 2 - 1) % 7 + 1
            return str(new_val)
    except: pass
    return note_str

# --- 2. 網頁配置 ---
st.set_page_config(page_title="數位填譜助手", layout="centered")
st.title("🎼 手寫轉數位：豎笛專用電子譜生成")
st.markdown("將手寫稿辨識後，自動填入您提供的**空白五線譜**範本中。")

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()

# --- 3. 讀取空白範本 ---
TEMPLATE_PATH = "image_e83be0.png" # 確保此檔案在你的 GitHub 根目錄

uploaded_file = st.file_uploader("上傳手寫簡譜照片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    if not os.path.exists(TEMPLATE_PATH):
        st.error(f"找不到空白範本檔案 {TEMPLATE_PATH}，請確認已上傳至 GitHub。")
    else:
        try:
            # 讀取手寫稿
            input_bytes = uploaded_file.read()
            pil_input = Image.open(io.BytesIO(input_bytes)).convert('RGB')
            input_w, input_h = pil_input.size
            
            # 讀取空白範本
            pil_template = Image.open(TEMPLATE_PATH).convert('RGB')
            temp_w, temp_h = pil_template.size
            
            if st.button("🚀 開始數位填譜"):
                with st.spinner('AI 正在分析座標並重新排版...'):
                    # OpenCV 辨識
                    img_cv = cv2.cvtColor(np.array(pil_input), cv2.COLOR_RGB2BGR)
                    results = reader.readtext(img_cv)
                    
                    draw = ImageDraw.Draw(pil_template)
                    count = 0
                    
                    for (bbox, text, prob) in results:
                        cleaned = "".join([c for c in text if c.isdigit()])
                        if cleaned and prob > 0.3:
                            new_text = "".join([transpose_for_clarinet(c) for c in cleaned])
                            
                            # 座標映射：將手寫稿位置比例轉換到範本位置
                            # 取得手寫稿中心點
                            orig_x = (bbox[0][0] + bbox[2][0]) / 2
                            orig_y = (bbox[0][1] + bbox[2][1]) / 2
                            
                            # 計算在範本上的相對位置
                            target_x = int((orig_x / input_w) * temp_w)
                            target_y = int((orig_y / input_h) * temp_h)
                            
                            # 在新譜上印出數位紅字
                            draw.text((target_x, target_y), new_text, fill=(255, 0, 0))
                            count += 1
                    
                    if count > 0:
                        st.success(f"轉換成功！已將 {count} 個音符填入新譜。")
                        st.image(np.array(pil_template), caption="生成的數位電子譜", use_column_width=True)
                        
                        # 下載
                        buf = io.BytesIO()
                        pil_template.save(buf, format="PNG")
                        st.download_button("📥 下載完整電子譜", buf.getvalue(), "Digital_Score.png", "image/png")
                    else:
                        st.warning("辨識不到音符，請確保手寫稿字跡清晰。")
                        
        except Exception as e:
            st.error(f"發生錯誤：{e}")
