from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import re
import json
import pandas as pd

# 設定無頭模式
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")

# 設置 User-Agent，這裡用的是 Chrome 瀏覽器的 User-Agent 字串
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
chrome_options.add_argument(f"user-agent={user_agent}")

# 初始化 driver
driver = webdriver.Chrome(options=chrome_options)

def clean_text(text):
    lines = text.split('\n')
    author = 'N/A'

    for line in lines:
        if line.startswith('作者'):
            author = line.replace('作者', '').strip()

    # 去除 meta 資訊（前 4 行）和簽名檔（-- 之後）
    content_body = re.split(r'--\n', '\n'.join(lines[4:]))[0]
    return author, content_body.strip()

def get_articles_from_page():
    articles = []
    
    # 找出每篇文章的標題和連結
    entries = driver.find_elements(By.CSS_SELECTOR, 'div.r-ent')
    for entry in entries:
        try:
            title_el = entry.find_element(By.CSS_SELECTOR, 'div.title > a')
            title = title_el.text
            link = title_el.get_attribute('href')
            nrec_el = entry.find_element(By.CSS_SELECTOR, 'div.nrec > span')
            nrec_text = nrec_el.text.strip()

            # 處理 nrec：可能是數字，也可能是 "爆" 或 "X1" 之類
            if nrec_text == '爆':
                nrec = 100  # 自訂，代表爆文
            elif re.match(r'^X\d+$', nrec_text):
                nrec = -int(nrec_text[1:])  # 例如 X1 → -1
            elif nrec_text.isdigit():
                nrec = int(nrec_text)
            else:
                nrec = 0

            # 進入文章
            driver.execute_script("window.open(arguments[0]);", link)
            driver.switch_to.window(driver.window_handles[1])
            time.sleep(0.1)

            # 取得時間、內文
            try:
                main_content = driver.find_element(By.ID, 'main-content').text
                author, content = clean_text(main_content)

                articles.append({
                    "title": title,
                    "url": link,
                    "author": author,
                    "popularity": nrec,
                    "content": content
                })
            except Exception as e:
                print(f"❌ 無法讀取文章內容: {e}")
            
            # 關閉分頁
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        except:
            continue
    
    return articles

# 主流程：抓取一定數量的頁數
def crawl_cfantasy(pages):
    base_url = "https://www.ptt.cc/bbs/CFantasy/index.html"
    all_articles = []
    
    driver.get(base_url)
    time.sleep(1)  # 等待頁面加載完成

    for i in range(pages):
        print(f"正在抓取第 {i+1} 頁...")
        
        # 抓取該頁的文章
        articles = get_articles_from_page()
        all_articles.extend(articles)
        
        # 點擊「上一頁」
        try:
            prev_page_button = driver.find_element(By.LINK_TEXT, '‹ 上頁') 
            prev_page_button.click()
            time.sleep(0.1)  # 等待頁面加載
        except:
            print("❌ 沒有更多頁面了，停止爬取")
            break
    
    return all_articles

# 執行爬蟲
result = crawl_cfantasy(pages=2)  # 爬取 2 頁

'''# 存成 JSON
with open("CFantasy_articles.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
'''

df = pd.DataFrame(result)

df.to_csv("CFantasy_articles.txt", sep=",", index=False, encoding="utf-8")

with open("CFantasy_articles.txt", "w", encoding="utf-8") as f:
    for article in result:
        f.write("📌 Title: " + article.get("title", "N/A") + "\n")
        f.write("Author: " + article.get("author", "N/A") + "\n")
        f.write("Popularity: " + str(article.get("popularity", "N/A")) + "\n")
        f.write("URL: " + article.get("url", "N/A") + "\n\n")
        f.write("Content:\n" + article.get("content", "").strip() + "\n")
        f.write("\n" + "—" * 50 + "\n\n")


driver.quit()
print("✅ 爬取完成！共收集文章數量：", len(result))
