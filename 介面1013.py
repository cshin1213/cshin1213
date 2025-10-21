import gradio as gr
import os
import mimetypes
#from google import genai
from google.genai import types
from PIL import Image
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time
import google.generativeai as genai

genai.configure(api_key='AIzaSyAQGTDYYj5aP8MlrWR3gsWpzv8M6jjVApw')  # ← 用這一行完成設定

#client = genai.Client(api_key = 'AIzaSyAQGTDYYj5aP8MlrWR3gsWpzv8M6jjVApw')
# print("text")
# load_dotenv()  # 自動讀取 .env
# print(os.getenv("GOOGLE_API_KEY"))

# 自動判斷 MIME type
def get_mime_type(file_path: str) -> str:
    mime, _ = mimetypes.guess_type(file_path)
    return mime if mime else "application/octet-stream"

# 把圖片清單轉成 contents
def build_image_parts(image_paths):
    parts = []
    for path in image_paths:
        img = Image.open(path)
        parts.append(img)
    return parts


# 問問題
def ask_gemini(prompt, image_paths):
    model = genai.GenerativeModel('gemini-2.5-flash') # 初始化模型
    contents = [prompt] + build_image_parts(image_paths)
    response = model.generate_content(
        contents=contents
    )
    return response.text

def get_gemini_response(image_paths, description_places, description_actions, description_food):
    """
    傳送圖片和描述文字給 GEMINI 模型，並獲取回覆。
    """
    if not image_paths:
        return "錯誤：請提供圖片檔案。"

    # 檢查圖片檔案是否存在
    for path in image_paths:
        if not os.path.exists(path):
            return f"錯誤：找不到指定的圖片檔案 - {path}"

    prompt = (
        f"我剛剛去過{description_places}、吃過{description_food}、做過{description_actions}。"
        "請你透過文字與圖片給我一個肯定的答覆，如果無法判斷，請回復：『我不確定，請給我更多圖片或更早的時間描述』，"
        "如果可以確定不是過敏情形請回復：『這不是過敏，可以再多加觀察或就醫』"
        "確定是什麼過敏症狀後請給我：『這是[什麼過敏]，是因為[吃了什麼、做了什麼]所以才過敏，你可以[解決辦法、抑制過敏的辦法]，當然這並不能保證你不需要去看病，若是後續愈發嚴重，請立即就醫。』"
        "[]中的詞語是替換的，如果圖片中的過敏情形十分嚴重，請回復：『您的症狀已十分嚴重，請您立即就醫！』"
    )

    return ask_gemini(prompt, image_paths)


AIR_QUALITY_DATA = {
    "基隆市": ["基隆"],
    "臺北市": ["士林", "大同", "中山", "古亭", "松山", "陽明", "萬華"],
    "新北市": ["三重", "土城", "永和", "汐止", "板橋", "林口", "淡水", "菜寮", "新店", "新莊", "新北(樹林)", "富貴角"],
    "桃園市": ["大園", "中壢", "平鎮", "桃園", "龍潭", "觀音"],
    "新竹市": ["新竹"],
    "新竹縣": ["竹東", "湖口"],
    "苗栗縣": ["三義", "苗栗", "頭份"],
    "臺中市": ["大里", "西屯", "沙鹿", "忠明", "豐原", "臺中市(和平區)"],
    "彰化縣": ["二林", "彰化", "線西", "大城", "員林"],
    "南投縣": ["竹山", "南投", "埔里", "南投(鹿谷)"],
    "雲林縣": ["斗六", "崙背", "麥寮", "臺西"],
    "嘉義市": ["嘉義"],
    "嘉義縣": ["朴子", "新港"],
    "臺南市": ["安南", "善化", "新營", "臺南", "臺南(南化)"],
    "高雄市": ["大寮", "小港", "仁武", "左營", "林園", "前金", "前鎮", "美濃", "復興", "楠梓",  "鳳山", "橋頭", "高雄(湖內)"],
    "屏東縣": ["屏東", "恆春", "潮州", "屏東(琉球)", "屏東(枋山)"],
    "宜蘭縣": ["冬山", "宜蘭", "宜蘭(三星)"],
    "花蓮縣": ["花蓮"],
    "臺東縣": ["臺東", "關山"],
    "澎湖縣": ["馬公"],
    "金門縣": ["金門"],
    "連江縣": ["馬祖"]
}

# 新增縣市到區域的映射
COUNTY_TO_AREA = {
    "中部空品區": ["臺中市", "彰化縣", "南投縣"],
    "北部空品區": ["基隆市", "臺北市", "新北市", "桃園市"],
    "竹苗空品區": ["新竹市","新竹縣","苗栗縣"],
    "雲嘉南空品區": ["雲林縣","嘉義市","嘉義縣","臺南市"],
    "高屏空品區": ["高雄市", "屏東縣"],
    "宜蘭空品區": ["宜蘭縣"],
    "花東空品區": ["花蓮縣", "臺東縣"],
    "其他空品區": ["澎湖縣", "金門縣", '連江縣']
}

# 建立一個反向查找字典，方便從縣市快速找到區域
AREA_LOOKUP = {
    county: area for area, counties in COUNTY_TO_AREA.items() for county in counties
}

COUNTY_ORDER = [
    "", "基隆市", "臺北市", "新北市", "桃園市", "新竹市", "新竹縣", "宜蘭縣", "苗栗縣",
    "臺中市", "彰化縣", "南投縣", "雲林縣", "嘉義市", "嘉義縣", "臺南市",
    "高雄市", "屏東縣", "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"
]

# 獲取所有縣市，並按照 COUNTY_ORDER 排序
all_counties = [county for county in COUNTY_ORDER if county in AIR_QUALITY_DATA]

# 獲取所有測站
all_sites = sorted(list(set(site for sites in AIR_QUALITY_DATA.values() for site in sites)))

# 獲取所有空品區
all_areas = sorted(list(COUNTY_TO_AREA.keys()))

# 根據選擇的空品區更新縣市選項
def update_counties(area):
    if area in COUNTY_TO_AREA:
        counties = COUNTY_TO_AREA[area]
        return gr.update(choices=counties, value=counties[0] if counties else None)
    return gr.update(choices=[], value=None)

# 根據選擇的縣市更新測站選項
def update_sites(county):
    if county in AIR_QUALITY_DATA:
        sites = AIR_QUALITY_DATA[county]
        return gr.update(choices=sites, value=sites[0] if sites else None)
    return gr.update(choices=[], value=None)

# AQI 函數
def AQI(county, site):
    if not county or not site:
        return "請先選擇縣市和測站", ""

    area = AREA_LOOKUP.get(county)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080") # 避免在 headless 模式下元素不可見

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 10) # 設定最長等待時間為 10 秒
 
    try:
        driver.get("https://airtw.moenv.gov.tw/CHT/EnvMonitoring/Central/CentralMonitoring.aspx")
        time.sleep(1) # 給予頁面一些時間載入

        # 選空品區
        area_select_element = wait.until(EC.presence_of_element_located((By.ID, "ddl_Area")))
        area_select = Select(area_select_element)
        area_select.select_by_visible_text(area)
        time.sleep(0.5)

        # 選縣市
        county_select_element = wait.until(EC.presence_of_element_located((By.ID, "ddl_County")))
        county_select = Select(county_select_element)
        county_select.select_by_visible_text(county)
        time.sleep(0.5)

        # 選測站
        site_select_element = wait.until(EC.presence_of_element_located((By.ID, "ddl_Site")))
        site_select = Select(site_select_element)
        site_select.select_by_visible_text(site)
        time.sleep(0.5)

        # 點擊查詢 (修正 ID 並等待按鈕可被點擊)
        query_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn_seach")))
        query_btn.click()
        time.sleep(1)

        # 取得數據
        aqi_value = wait.until(EC.presence_of_element_located((By.ID, "AQI"))).text.strip()
        pm_25_value = wait.until(EC.presence_of_element_located((By.ID, "AVPM25"))).text.strip()
        pm_10_value = wait.until(EC.presence_of_element_located((By.ID, "AVPM10"))).text.strip()


        return f"AQI: {aqi_value}", f"PM2.5: {pm_25_value}", f"PM10: {pm_10_value}"
    except Exception as e:
        current_url = driver.current_url if driver else "N/A"
        page_source = driver.page_source if driver else "N/A"
        return f"查詢失敗: {e}\n當前網址: {current_url}\n頁面原始碼 (部分): {page_source[:500]}...", ""
    finally:
        driver.quit()



# 模擬吸入檢測功能
def inhalation_detection():
    return "吸入檢測結果：正常" # 這裡可以替換為實際的檢測邏輯

with gr.Blocks(title="居家病理檢測") as demo:
    gr.Markdown("# 居家病理檢測")

    with gr.Tab("病理檢測"):        
        with gr.Row():
            image_input = gr.Files(label="上傳圖片", file_types=["image"])
        accort = gr.Textbox(label = "帳號")
        password = gr.Textbox(label = "密碼")
        search = gr.Button("登入")
        description_places = gr.Textbox(label="剛剛去過哪些地方？")
        description_actions = gr.Textbox(label="剛剛做了什麼？")
        description_food = gr.Textbox(label="剛剛吃了什麼？")
        
        ai_detect_button = gr.Button("執行病理檢測")
        ai_output = gr.Textbox(label="病理檢測結果",lines = 9)

        ai_detect_button.click(
            get_gemini_response,
            inputs=[image_input, description_places, description_actions, description_food],
            outputs=ai_output,
            show_progress="full"
        )

    with gr.Tab("空氣品質檢測"):
        gr.Markdown("## 今日過敏情形：")
        gr.Markdown("### 空氣品質指標 (AQI) 查詢")
        
        area_input = gr.Dropdown(choices=all_areas, label="選擇空品區")
        county_input = gr.Dropdown(choices=[], label="選擇縣市")
        site_input = gr.Dropdown(choices=[], label="選擇測站")

        aqi_output = gr.Textbox(label="AQI")
        pm25_output = gr.Textbox(label="PM2.5")
        pm10_output = gr.Textbox(label="AVPM10")
        
        aqi_button = gr.Button("查詢 AQI")
        
        area_input.change(update_counties, inputs=area_input, outputs=county_input)
        county_input.change(update_sites, inputs=county_input, outputs=site_input)
        aqi_button.click(AQI, inputs=[county_input, site_input], outputs=[aqi_output, pm25_output, pm10_output], show_progress="full")

    with gr.Tab("吸入結果與過往紀錄"):
        gr.Markdown("## 吸入結果：")
        inhalation_output = gr.Textbox(label="吸入檢測結果")
        inhalation_button = gr.Button("吸入檢測")
        inhalation_button.click(inhalation_detection, outputs=inhalation_output)

        gr.Markdown("## 吸入結果的過往紀錄：")
        gr.Markdown("### 這裡將放置過往紀錄功能")

    with gr.Tab("病理檢測的過往紀錄"):
        gr.Markdown("")


    with gr.Tab("病理日記"):
        gr.Markdown("## 病理日記：")
        gr.Markdown("### 這裡將放置病理日記功能")




demo.launch()