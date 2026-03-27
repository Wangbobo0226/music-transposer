import streamlit as st
import cv2
import numpy as np
from PIL import Image
import easyocr
from utils import convert_sheet_music, process_jianpu_ocr
import re

st.set_page_config(page_title="簡譜移調轉換器 (AI 升級版)", page_icon="🎵", layout="wide")

# --- 初始化 EasyOCR 模型 ---
@st.cache_resource
def load_ocr_model():
    # 載入模型，關閉 GPU 節省資源，適合雲端環境
    return easyocr.Reader(['ch_tra', 'en'], gpu=False)

def reconstruct_layout(ocr_results):
    """根據 EasyOCR 的座標結果重構初步排版"""
    if not ocr_results:
        return ""
        
    blocks = []
    for res in ocr_results:
        bbox = res[0]
        text = res[1]
        
        min_y = min([p[1] for p in bbox])
        max_y = max([p[1] for p in bbox])
        center_y = (min_y + max_y) / 2
        min_x = min([p[0] for p in bbox])
        
        blocks.append({'text': text, 'center_y': center_y, 'min_x': min_x})
        
    blocks.sort(key=lambda b: b['center_y'])
    lines = []
    current_line = []
    y_threshold = 15 # 容差值
    
    for block in blocks:
        if not current_line:
            current_line.append(block)
        else:
            avg_y = sum([b['center_y'] for b in current_line]) / len(current_line)
            if abs(block['center_y'] - avg_y) < y_threshold:
                current_line.append(block)
            else:
                lines.append(current_line)
                current_line = [block]
    if current_line:
        lines.append(current_line)
        
    final_text = ""
    for line in lines:
        line.sort(key=lambda b: b['min_x'])
        line_text = "  ".join([b['text'] for b in line])
        final_text += line_text + "\n"
        
    return final_text

def format_jianpu_text(text):
    """將文字強制格式化為標準簡譜樣式 (自動補齊小節線與間距)"""
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        if not line.strip():
            continue
            
        # 修正誤判的小節線
        line = re.sub(r'(?<=\s)[Il](?=\s)', '|', line)
        # 確保小節線前後有空格
        line = line.replace('|', ' | ')
        # 清理多餘的連續空格
        line = re.sub(r'\s{3,}', '  ', line).strip()
        
        # 智慧補齊頭尾小節線
        chars = [c for c in line if c.strip()]
        if chars:
            music_char_count = sum(1 for c in chars if c.isdigit() or c in '-·|')
            if music_char_count / len(chars) > 0.4: 
                if not line.startswith('|'):
                    line = '| ' + line
                if not line.endswith('|'):
                    line = line + ' |'
                    
        formatted_lines.append(line)
        
    return '\n'.join(formatted_lines)

# --- 側邊欄選單 ---
st.sidebar.title("⚙️ 功能選單")
menu_option = st.sidebar.radio(
    "請選擇您要使用的轉換方式：",
    ("📝 文字輸入轉換", "🖼️ 圖片 AI 智慧辨識 (EasyOCR)")
)

st.sidebar.divider()
st.sidebar.info("💡 **升級提示**：已開啟「二值化黑白強化模式」，AI 能更精準地捕捉微小的音符與小節線！")

if menu_option == "📝 文字輸入轉換":
    st.title("📝 簡譜文字轉換")
    st.write("請在下方輸入框貼上或手打您的簡譜，系統將自動為您移調。")
    
    sheet_text = st.text_area(
        "輸入簡譜：", 
        placeholder="例如：\n| 3 5 2 5 | 4 4 3 5 | 1' 2' 3' |",
        height=300
    )

    if st.button("開始轉換", type="primary"):
        if sheet_text.strip():
            converted = convert_sheet_music(sheet_text)
            st.success("✅ 轉換成功！")
            st.code(converted, language="text") 
        else:
            st.warning("請先輸入簡譜文字喔！")

elif menu_option == "🖼️ 圖片 AI 智慧辨識 (EasyOCR)":
    st.title("🖼️ 樂譜圖片 AI 智慧偵測")
    st.write("上傳樂譜圖片，AI 將自動辨識數字、過濾雜訊，並重構排版進行移調！")

    uploaded_file = st.file_uploader("請選擇樂譜圖片", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2 = st.columns(2)
        with col1:
            st.image(image, caption="已上傳的樂譜", use_container_width=True)
            
        with col2:
            if st.button("🚀 開始啟動 AI 掃描", type="primary"):
                with st.spinner('📦 正在喚醒 AI 視覺模型...'):
                    try:
                        ocr = load_ocr_model()
                    except Exception as e:
                        st.error(f"❌ 模型載入失敗：{str(e)}")
                        st.stop()
                
                with st.spinner('🔍 正在進行影像黑白強化與排版解析...'):
                    try:
                        # 將 PIL 影像轉為 OpenCV 格式
                        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                        
                        # 1. 溫和放大 (1.5倍)：既能放大數字，又能把記憶體消耗控制在安全範圍內
                        width, height = int(img_cv.shape[1] * 1.5), int(img_cv.shape[0] * 1.5)
                        resized_img = cv2.resize(img_cv, (width, height), interpolation=cv2.INTER_CUBIC)
                        
                        # 2. 轉灰階
                        gray_img = cv2.cvtColor(resized_img, cv2.COLOR_BGR2GRAY)
                        
                        # 3. Otsu 二值化：自動尋找最佳閥值，把背景變純白、字體變純黑！
                        _, binary_img = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                        
                        # 4. 進行辨識 (內部放大率設為 1.5，強制處理低對比字體)
                        result = ocr.readtext(binary_img, mag_ratio=1.5, contrast_ths=0.1, adjust_contrast=0.5)
                        
                        # 重構排版與格式化
                        structured_text = reconstruct_layout(result)
                        beautified_text = format_jianpu_text(structured_text)
                        
                        # 進行過濾雜訊與移調
                        cleaned_original, final_converted = process_jianpu_ocr(beautified_text)
                        
                        if cleaned_original.strip():
                            st.success("✅ 辨識與轉換完成！")
                            st.write("**(1) 根據座標重構並格式化的乾淨原譜：**")
                            st.code(cleaned_original, language="text")
                            
                            st.write("**(2) 自動移調後的結果：**")
                            st.code(final_converted, language="text")
                        else:
                            st.error("⚠️ AI 仍然無法從圖片中解析出清晰的音符。建議裁切圖片只保留樂譜部分測試。")
                            
                    except Exception as e:
                        st.error(f"❌ 處理圖片時發生錯誤：{str(e)}")
