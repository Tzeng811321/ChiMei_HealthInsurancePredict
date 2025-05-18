# -*- coding: utf-8 -*-
"""
last update: 2025-05-17
By Tseng-Tasi
------------------------------------------------------------
機制說明：
1. 本程式先將 IndexCode.csv 的產品資料匯入 SQLite，建立資料表與索引。
2. 使用者輸入關鍵字後，先以 SQL LIKE 查找直接匹配，若無則透過 fuzzywuzzy 進行
   文字相似度比對，找出最接近的產品名稱。
3. 取得參考產品的功能類別(前5碼)，再查詢相同功能類別的所有產品，並依「大小類」
   分組列印與匯出至 CSV。
4. 流程結束後釋放資料庫連線。
"""
import pandas as pd
import sqlite3
from fuzzywuzzy import process, fuzz
import os

def load_data_to_db(csv_file, db_file):
    """
    將 CSV 資料匯入 SQLite 資料庫，若資料庫不存在則建立一個新資料庫。
    參數:
        csv_file: CSV 檔案路徑
        db_file: 資料庫檔案名稱
    回傳:
        conn: SQLite 資料庫連線物件
    """
    # 讀取 CSV 檔案
    df = pd.read_csv(csv_file, encoding="utf-8")
    # 連線至 SQLite 資料庫，若無則建立一個新資料庫
    conn = sqlite3.connect(db_file)
    
    # 建立 products 表格，欄位名稱需與 CSV 內的欄位一致
    # 注意因為欄位名稱中有括號，因此使用雙引號括起來
    create_table_query = '''
        CREATE TABLE IF NOT EXISTS products (
            "功能類別(前5碼)" TEXT,
            "名稱" TEXT,
            "大小類" TEXT,
            "類別" TEXT
        )
    '''
    conn.execute(create_table_query)
    
    # 為避免重複資料，先清空表格
    conn.execute("DELETE FROM products")
    
    # 將 DataFrame 寫入資料庫
    df.to_sql("products", conn, if_exists="append", index=False)
    conn.commit()
    return conn

def create_index(conn):
    """
    在資料庫的「功能類別(前5碼)」欄位建立索引，提升查詢效能。
    參數:
        conn: SQLite 資料庫連線物件
    """
    conn.execute('CREATE INDEX IF NOT EXISTS idx_function_code ON products("功能類別(前5碼)")')
    conn.commit()

def fuzzy_search_product(conn, keyword, threshold=40):
    """利用模糊匹配在資料庫中搜尋相關產品"""
    # 從資料庫中取出所有產品相關資訊
    query = """
    SELECT 名稱, "功能類別(前5碼)", 大小類, 類別 
    FROM products 
    WHERE 名稱 LIKE ? 
    OR 大小類 LIKE ? 
    OR 類別 LIKE ?
    """
    search_pattern = f"%{keyword}%"
    cursor = conn.execute(query, (search_pattern, search_pattern, search_pattern))
    direct_matches = cursor.fetchall()
    
    if direct_matches:
        # 回傳所有直接匹配結果
        return [(match[0], match[1]) for match in direct_matches]
    
    # 如果沒有直接匹配，使用模糊匹配
    df_products = pd.read_sql("SELECT 名稱, \"功能類別(前5碼)\" FROM products", conn)
    product_names = df_products["名稱"].tolist()
    
    # 使用模糊匹配找出所有符合閾值的結果
    matches = process.extract(keyword, product_names, scorer=fuzz.token_set_ratio, limit=30)
    
    matched_products = []
    for matched_name, score in matches:
        if score >= threshold:
            query = 'SELECT "功能類別(前5碼)" FROM products WHERE 名稱 = ?'
            cursor = conn.execute(query, (matched_name,))
            ref_product = cursor.fetchone()
            if ref_product:
                matched_products.append((matched_name, ref_product[0]))
    
    if matched_products:
        return matched_products
        
    print(f"找不到符合關鍵字 '{keyword}' 的產品")
    return []

def query_products_by_function(conn, ref_code):
    """
    根據功能類別(前5碼)查詢所有相同分類的產品，並回傳結果 DataFrame。

    參數:
        conn (sqlite3.Connection): 已開啟的資料庫連線
        ref_code (str): 參考產品的功能類別(前5碼)
    回傳:
        pd.DataFrame: 包含查詢結果的 DataFrame，欄位為功能類別、名稱、大小類、類別
    """
    query = 'SELECT * FROM products WHERE "功能類別(前5碼)" = ?'
    cursor = conn.execute(query, (ref_code,))
    results = cursor.fetchall()
    
    # 將查詢結果轉為 DataFrame 方便後續處理
    df_results = pd.DataFrame(results, columns=["功能類別(前5碼)", "名稱", "大小類", "類別"])
    return df_results

def search_products(keyword, db_file="products.db", csv_file="IndexCode.csv"):
    """
    主函式：
      1. 將 CSV 資料匯入資料庫並建立索引。
      2. 利用模糊匹配搜尋產品，取得參考產品的功能類別(前5碼)。
      3. 查詢所有擁有相同功能類別(前5碼)的產品，並依照大小類分組輸出。
    參數:
        keyword: 使用者輸入的關鍵字或產品名稱
        db_file: 資料庫檔案名稱（預設 "products.db"）
        csv_file: CSV 檔案路徑（預設 "IndexCode.csv"）
    """
    # 匯入資料到資料庫
    conn = load_data_to_db(csv_file, db_file)
    create_index(conn)
    
    # 使用模糊匹配取得參考產品的功能類別(前5碼)
    matched_products = fuzzy_search_product(conn, keyword)
    if not matched_products:
        conn.close()
        return
    
    print(f"\n找到 {len(matched_products)} 個相關產品:")
    
    # 創建一個空的 DataFrame 來存儲所有結果
    all_results_df = pd.DataFrame()
    
    # 處理每個匹配的產品
    for matched_name, ref_code in matched_products:
        print(f"\n參考產品: {matched_name}, 功能類別: {ref_code}")
        
        # 根據功能類別(前5碼)查詢所有相關產品
        df_results = query_products_by_function(conn, ref_code)
        
        # 添加搜尋關鍵字和參考產品資訊
        df_results['搜尋關鍵字'] = keyword
        df_results['參考產品'] = matched_name
        
        # 將結果添加到總表中
        all_results_df = pd.concat([all_results_df, df_results])
        
        # 根據大小類進行分組並輸出到終端
        grouped = df_results.groupby("大小類")
        for group_name, group_data in grouped:
            print(f"\n大小類: {group_name}")
            print(group_data[["名稱", "功能類別(前5碼)", "類別"]])
            print("-" * 30)
    
    # 儲存所有結果到 CSV 檔案
    output_dir = os.path.dirname(csv_file)
    output_file = os.path.join(output_dir, "IndexSQL_find.csv")
    all_results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n搜尋結果已保存到：{output_file}")
    
    conn.close()

# 主程式執行
if __name__ == "__main__":
    keyword_input = input("請輸入產品名稱或關鍵字: ")
    # 請依實際路徑修改 db_file 與 csv_file 參數
    #search_products(keyword_input, csv_file="D:\\CYCU\\113_WebCrawler\\CODE\\data\\IndexCode.csv")
    search_products(keyword_input, db_file="D:\\CYCU\\113_WebCrawler\\CODE\\data\\products.db", csv_file="D:\\CYCU\\113_WebCrawler\\CODE\\data\\IndexCode.csv")