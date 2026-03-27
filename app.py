import streamlit as st
import cv2
import numpy as np
from PIL import Image

# 1. 移調邏輯 (對應簡譜數字)
def transpose_logic(note_list, shift_amount):
    # 簡化的移調：1->2, 2->3... 
    # 實際開發會用半音階計算(如我之前給你的那段)
    result = []
    for note in note_list:
        if note.isdigit():
            new_note = str((int(note) + shift_amount - 1) % 7 + 1)
            result.append(new_note)
        else:
            result.append(note)
    return result

# 2. 網頁介面
st.title("🎷 豎笛/薩克斯風 轉譜小助手")

st.sidebar.header("設定")
instrument = st.sidebar.selectbox("你的樂器", ["豎笛 (Bb)", "中音薩克斯風 (Eb)"])
output_type = st.sidebar.radio("輸出格式", ["新簡譜", "五線譜(開發中)"])

uploaded_file = st.file_uploader("上傳簡譜圖片", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    # 讀取圖片
    image = Image.open(uploaded_file)
    st.image(image, caption="原始樂譜", use_column_width=True)
    
    if st.button("開始轉譜"):
        with st.spinner("AI 正在辨識音符中..."):
            # --- 這裡未來會串接 EasyOCR 辨識 ---
            # 暫時模擬辨識結果
            mock_detected = ["5", "3", "3", "6", "5", "3"] 
            
            # 根據樂器決定移調量 (豎笛通常是 +1 或 +2)
            shift = 1 if "Bb" in instrument else 3
            
            final_score = transpose_logic(mock_detected, shift)
            
            st.success("轉換成功！")
            st.write(f"移調後的音符序列為： {' '.join(final_score)}")
            st.info("註：目前為開發階段，僅顯示數位序列，下一版將直接生成新譜圖片。")
