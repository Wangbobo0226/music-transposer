import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw
import io
import easyocr

# --- 1. 豎笛專用移調邏輯 (固定 +2) ---
def transpose_for_clarinet(note_str):
    try:
        if note_str.isdigit():
            val = int(note_str)
            # 簡譜 1-7 循環移調 (+2)
            # 例如：1 -> 3, 6 -> 1, 7 -> 2
            new_val = (val + 2 - 1) % 7 + 1
            return str(new_val)
    except: pass
    return note_str

# --- 2. 網頁配置 ---
st.set_page_config(page_title="豎笛專用轉譜器", layout="centered")
st.title("🎷 豎笛 (Bb) 自動轉譜助手")
st.markdown("上傳手寫簡譜，我會幫你生成一張**純白背景**的專用電子譜。")

@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()

uploaded_file = st.file_uploader("請上傳樂譜照片", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        img_bytes = uploaded_file.read()
        pil_orig = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        if st.button("✨ 生成豎笛專用純白譜"):
            with st.spinner('正在淨化譜面並移調...'):
                
                # --- A. 影像強效淨化 (變成純白電子檔感) ---
                img_opencv = cv2.cvtColor(np.array(pil_orig), cv2.COLOR_RGB2BGR)
                gray = cv2.cvtColor(img_opencv, cv2.COLOR_BGR2GRAY)
                
                # 自適應二值化：過濾掉所有灰色陰影，只留黑字
                clean_mask = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 115, 25 # 調整此參數可增加去背強度
                )
                
                # 建立純白電子畫布
                pil_clean = Image.fromarray(clean_mask).convert('RGB')
                draw = ImageDraw.Draw(pil_clean)
                
                # --- B. AI 辨識與覆寫 ---
                results = reader.readtext(img_opencv)
                
                count = 0
                for (bbox, text, prob) in results:
                    # 篩選數字
                    cleaned_text = "".join([c for c in text if c.isdigit()])
                    if cleaned_text and prob > 0.3:
                        # 執行豎笛移調
                        new_text = "".join([transpose_for_clarinet(c) for c in cleaned_text])
                        
                        # 取得座標安全邊界
                        xs = [p[0] for p in bbox]
                        ys = [p[1] for p in bbox]
                        min_x, max_x = int(min(xs)), int(max(xs))
                        min_y, max_y = int(min(ys)), int(max(ys))
                        
                        # 在純白畫布上先塗白(清除舊痕跡)，再印紅字
                        draw.rectangle([min_x, min_y, max_x, max_y], fill="white")
                        draw.text((min_x, min_y), new_text, fill=(255, 0, 0))
                        count += 1
                
                # --- C. 結果顯示 ---
                st.subheader("✅ 豎笛專用譜已生成")
                st.image(np.array(pil_clean), use_column_width=True)
                
                # 下載按鈕
                buf = io.BytesIO()
                pil_clean.save(buf, format="PNG")
                st.download_button("📥 下載此電子譜", buf.getvalue(), "Clarinet_Sheet.png", "image/png")
                
    except Exception as e:
        st.error(f"轉換出錯：{e}")
else:
    st.info("請上傳您的手寫簡譜照片。")
