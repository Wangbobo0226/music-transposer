import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io
# 從你建立的另一個檔案匯入邏輯
from utils import get_transpose_info, transpose_numbered_note

# --- 網頁頁面設定 ---
st.set_page_config(page_title="簡譜自動轉調助手", page_icon="🎷")

st.title("🎼 簡譜自動轉調助手")
st.markdown("""
這個工具可以幫助你將**鋼琴簡譜**快速轉換為**豎笛 (Bb)** 或 **薩克斯風 (Eb)** 使用的譜！
1. 在左側選擇你的樂器。
2. 上傳簡譜圖片（如：JPG/PNG）。
3. 點擊「開始轉換」即可看到移調後的結果。
""")

# --- 側邊欄設定 ---
st.sidebar.header("🔧 轉換設定")
instrument = st.sidebar.selectbox(
    "1. 選擇你的目標樂器",
    ["豎笛 (Bb)", "中音薩克斯風 (Eb)", "小號 (Bb)", "長笛 (C)"]
)

show_original = st.sidebar.checkbox("顯示原始圖片", value=True)

# --- 檔案上傳 ---
uploaded_file = st.file_uploader("請上傳樂譜照片...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # 將上傳的檔案轉為 OpenCV 格式以便後續 AI 處理
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=uint8)
    opencv_image = cv2.imdecode(file_bytes, 1)
    # 轉回 PIL 格式供 Streamlit 顯示
    pil_image = Image.open(uploaded_file)

    if show_original:
        st.image(pil_image, caption="你上傳的原始樂譜", use_column_width=True)

    # --- 執行按鈕 ---
    if st.button("🚀 開始自動移調"):
        with st.spinner('AI 正在分析簡譜數字與位置...'):
            
            # 獲取該樂器需要移動的半音數
            shift = get_transpose_info(instrument)
            
            # --- 核心辨識模擬 (未來這區會換成 EasyOCR) ---
            # 這裡我們模擬辨識到了圖片中的幾個音符與其座標 (x, y)
            # 假設這是《陪我看日出》的前幾個音
            mock_data = [
                {"note": "5", "pos": (100, 200)},
                {"note": "3", "pos": (150, 200)},
                {"note": "3", "pos": (200, 200)},
                {"note": "6", "pos": (250, 200)},
            ]
            
            # 建立一個繪圖對象，在原圖上做記號
            draw = ImageDraw.Draw(pil_image)
            
            st.subheader(f"✅ 針對 {instrument} 的移調建議：")
            
            results = []
            for item in mock_data:
                # 呼叫 utils.py 裡的移調函數
                new_note = transpose_numbered_note(item["note"], shift)
                results.append(new_note)
                
                # 在圖片上標註移調後的數字 (紅色)
                # 註：實際開發需要處理字體路徑，這裡先做簡易標註
                draw.text(item["pos"], new_note, fill=(255, 0, 0))
            
            # --- 顯示結果 ---
            col1, col2 = st.columns(2)
            with col1:
                st.metric("原始起始音", mock_data[0]["note"])
            with col2:
                st.metric("移調後起始音", results[0])
            
            st.image(pil_image, caption="移調標註預覽 (紅字為新音符)", use_column_width=True)
            
            # --- 下載功能 ---
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.download_button(
                label="📥 下載轉調後的圖片",
                data=byte_im,
                file_name="transposed_score.png",
                mime="image/png"
            )

else:
    st.info("💡 提示：請先在上方上傳一張清晰的簡譜照片。")

# --- 頁尾 ---
st.divider()
st.caption("Made with ❤️ for Musicians | Powered by Streamlit & Python")
