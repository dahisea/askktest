import requests
import threading
from queue import Queue
from bs4 import BeautifulSoup
import time
import pandas as pd
from openpyxl import Workbook

base_url = "http://47.97.87.78/ddt/bbs.php"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# 线程安全的队列
task_queue = Queue()
# 线程锁
print_lock = threading.Lock()
# 用于存储去重数据
data_records = set()

def worker():
    while True:
        page = task_queue.get()
        if page is None:  # 终止信号
            break
            
        params = {
            "phone": "",
            "pass": "",
            "mode": "0",
            "suoshu": "",
            "getpage": "1",
            "bbspage": str(page)
        }
        
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=10)
            
            with print_lock:
                print(f"正在处理页面: {page}，状态码: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    spans = soup.find_all('span')
                    
                    page_data = []
                    for span in spans:
                        phone = span.get('phone')
                        if phone:  # 只处理有phone属性的span
                            content = span.get_text(strip=True)
                            # 使用(phone, content)作为唯一标识去重
                            record = (phone, content)
                            if record not in data_records:
                                data_records.add(record)
                                page_data.append({
                                    "页码": page,
                                    "Phone": phone,
                                    "内容": content
                                })
                    
                    if page_data:
                        # 追加数据到Excel文件
                        df = pd.DataFrame(page_data)
                        with pd.ExcelWriter("output.xlsx", mode='a', engine='openpyxl', if_sheet_exists='overlay') as writer:
                            # 尝试读取已有数据
                            try:
                                existing_df = pd.read_excel("output.xlsx")
                                combined_df = pd.concat([existing_df, df], ignore_index=True)
                            except:
                                combined_df = df
                            
                            # 保存去重后的数据
                            combined_df.drop_duplicates(subset=['Phone', '内容'], keep='first', inplace=True)
                            combined_df.to_excel(writer, index=False)
                    
                    print(f"页面 {page} 完成，找到 {len(page_data)} 个有效span标签")
                else:
                    print(f"页面 {page} 返回状态码: {response.status_code}")
                
        except Exception as e:
            with print_lock:
                print(f"处理页面 {page} 时出错: {e}")
        
        # 适当延迟，避免被封
        time.sleep(0.5)
        task_queue.task_done()

# 初始化Excel文件
try:
    pd.DataFrame(columns=["页码", "Phone", "内容"]).to_excel("output.xlsx", index=False)
except:
    pass

# 设置线程数
num_worker_threads = 5
threads = []

# 启动工作线程
for i in range(num_worker_threads):
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)

# 添加任务到队列 (1-99页)
for page in range(1, 130):
    task_queue.put(page)

# 等待所有任务完成
task_queue.join()

# 停止工作线程
for i in range(num_worker_threads):
    task_queue.put(None)
for t in threads:
    t.join()

print("所有页面扫描完成，结果已保存到 output.xlsx")

# 最终去重处理（确保没有重复数据）
try:
    df = pd.read_excel("output.xlsx")
    df.drop_duplicates(subset=['Phone', '内容'], keep='first', inplace=True)
    df.to_excel("output.xlsx", index=False)
    print(f"最终去重后保留 {len(df)} 条唯一记录")
except Exception as e:
    print(f"最终去重处理时出错: {e}")