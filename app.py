import streamlit as st
import cv2
import numpy as np
from PIL import Image
from paddleocr import PaddleOCR
from utils import convert_sheet_music, process_jianpu_ocr
import re

# 設定網頁標題與圖示 (Layout 設定為寬屏)
st.set_page_config(page_title="簡譜移調轉換器 (AI 升級版)", page_icon="🎵", layout="wide")

# --- 初始化 PaddleOCR 模型 ---
# 使用 st.cache_resource 確保模型只在第一次載入，避免每次按按鈕都重新讀取浪費時間與記憶體
@st.cache_resource
def load_ocr_model():
    # lang='ch' 支援中英文與數字混合，這對過濾歌詞很有幫助
    # use_angle_cls=True 可以稍微修正傾斜的圖片
    return PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)

# --- 根據座標重構排版的函數 ---
def reconstruct_layout(ocr_results):
    """
    接收 PaddleOCR 的結果，根據 Y 座標分行，X 座標排序，
    盡可能還原原本的樂譜排版結構。
    """
    if not ocr_results or not ocr_results[0]:
        return ""
    
    blocks = []
    # ocr_results[0] 包含所有辨識到的文字框
    for res in ocr_results[0]:
        bbox = res[0]      # 座標點 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        text = res[1][0]   # 辨識出的文字
        
        # 計算這個文字框的中心 Y 座標和最左邊的 X 座標
        min_y = min([p[1] for p in bbox])
        max_y = max([p[1] for p in bbox])
        center_y = (min_y + max_y) / 2
        min_x = min([p[0] for p in bbox])
        
        blocks.append({'text': text, 'center_y': center_y, 'min_x': min_x})
        
    # 1. 先根據 Y 座標排序 (從上到下)
    blocks.sort(key=lambda b: b['center_y'])
    
    lines = []
    current_line = []
    y_threshold = 15 # 設定容差值：中心 Y 座標相差 15 像素內算同一行 (可視情況微調)
    
    for block in blocks:
        if not current_line:
            current_line.append(block)
        else:
            # 計算目前這行平均的 Y 座標
            avg_y = sum([b['center_y'] for b in current_line]) / len(current_line)
            if abs(block['center_y'] - avg_y) < y_threshold:
                current_line.append(block) # 算同一行
            else:
                lines.append(current_line) # 換下一行
                current_line = [block]
    if current_line:
        lines.append(current_line)
        
    # 2. 每一行內部再根據 X 座標排序 (從左到右)
    final_text = ""
    for line in lines:
        line.sort(key=lambda b: b['min_x'])
        # 用雙空格連接同一行的文字，模擬樂譜間距
        line_text = "  ".join([b['text'] for b in line])
        final_text += line_text + "\n"
        
    return final_text

# --- 建立側邊欄選單 ---
st.sidebar.title("⚙️ 功能選單")
menu_option = st.sidebar.radio(
    "請選擇您要使用的轉換方式：",
    ("📝 文字輸入轉換", "🖼️ 圖片 AI 智慧辨識 (PaddleOCR)")
)

st.sidebar.divider()
st.sidebar.info("💡 **升級提示**：目前已切換至 PaddleOCR 引擎，具備強大的座標定位功能，能更精準地剝離歌詞並保留小節線結構。")

# --- 文字轉換區塊 ---
if menu_option == "📝 文字輸入轉換":
    st.title("📝 簡譜文字轉換")
    st.write("請在下方輸入框貼上或手打您的簡譜，系統將自動為您移調。")
    
    sheet_text = st.text_area(
        "輸入簡譜：", 
        placeholder="例如：\n3 5 2 5 | 4 4 3 5 | 1' 2' 3'",
        height=300
    )

    if st.button("開始轉換", type="primary"):
        if sheet_text.strip():
            converted = convert_sheet_music(sheet_text)
            st.success("✅ 轉換成功！")
            st.code(converted, language="text") 
        else:
            st.warning("請先輸入簡譜文字喔！")

# --- 圖片轉換區塊 ---
elif menu_option == "🖼️ 圖片 AI 智慧辨識 (PaddleOCR)":
    st.title("🖼️ 樂譜圖片 AI 智慧偵測")
    st.write("上傳樂譜圖片，AI 將自動辨識數字、過濾中文歌詞，並重構排版進行移調！")

    uploaded_file = st.file_uploader("請選擇樂譜圖片", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        
        col1, col2 = st.columns(2)
        with col1:
            st.image(image, caption="已上傳的樂譜", use_container_width=True)
            
        with col2:
            if st.button("🚀 開始啟動 AI 掃描", type="primary"):
                
                # 載入模型，這一步會有 Spinner 提示使用者
                with st.spinner('📦 正在喚醒 AI 視覺模型 (初次啟動需時較長)...'):
                    try:
                        ocr = load_ocr_model()
                    except Exception as e:
                        st.error(f"❌ 模型載入失敗：{str(e)}")
                        st.stop()
                
                with st.spinner('🔍 正在掃描影像與重構樂譜排版...'):
                    try:
                        # 將 PIL 影像轉為 OpenCV 格式供 PaddleOCR 使用
                        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                        
                        # 執行 PaddleOCR 辨識
                        result = ocr.ocr(img_cv, cls=True)
                        
                        # 呼叫重構函數，把雜亂的框框變成有條理的字串
                        structured_text = reconstruct_layout(result)
                        
                        # 丟給 utils.py 去做過濾雜訊(去歌詞)與移調
                        cleaned_original, final_converted = process_jianpu_ocr(structured_text)
                        
                        if cleaned_original.strip():
                            st.success("✅ 辨識與轉換完成！")
                            st.write("**(1) 根據座標重構的乾淨原譜：**")
                            st.text(cleaned_original)
                            
                            st.write("**(2) 自動移調後的結果：**")
                            st.text(final_converted)
                        else:
                            st.error("⚠️ 無法從圖片中解析出清晰的音符，請嘗試其他圖片。")
                            
                    except Exception as e:
                        st.error(f"❌ 處理圖片時發生錯誤：{str(e)}")
