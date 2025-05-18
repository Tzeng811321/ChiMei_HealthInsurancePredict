# -*- coding: utf-8 -*-
"""
HistoryDataSearch.py   最後更新-> 2025-05-15
By Tseng-Tasi
------------------------------------------------------------
🌟 功能總覽
------------------------------------------------------------
1. 讀入三份來源 CSV
   • format_clean.csv           → 合法「核價類別」清單
   • IndexSQL_find.csv          → 特材代碼前五碼 ↔ 功能類別（此版僅用來先接資料）
   • 價量調查品項108-112.csv    → 歷史價量調查資料（欲標記之主體）

2. 對三張表需要比對的欄位執行「字串標準化」：
   • 去前後空白、合併多重空白、全形→半形、轉小寫
   • 產生 *_clean 欄位，不破壞原始內容

3. 先以「特材代碼前五碼」把 價量調查資料 × IndexSQL_find 進行 inner merge

4. 再以「核價類別」(clean) 與 format_clean 做 left merge，開啟 indicator
   -> 自動產生 _merge 欄，可得值 {both, left_only}

5. 點數變更記錄 = 1  ⇔ _merge == 'both'

6. 移除暫用欄位、重新排欄位順序、輸出 > HistoryData.csv
------------------------------------------------------------
⚠️ 變更提醒
------------------------------------------------------------
● 若確實需要「核價類別也必須存在於 IndexSQL_find['名稱']」，
  請把 STEP-B-2 下方的 `df_format_valid` 改成雙重交集條件，
  註解中已示範替換方法。

● 如需保留大小寫敏感，可把 clean_str() 的 `.lower()` 那行註解掉。
------------------------------------------------------------
"""
import os
import re
import unicodedata
from typing import Tuple, Optional

import pandas as pd


# ---------- 共用：字串標準化 ---------------------------------------
def clean_str(s: str) -> str:
    """
    將字串轉成統一比對格式：
      1. NFKC 正規化 → 全形→半形、兼容字元收斂
      2. strip()      → 去前後空白
      3. \s+ → ' '    → 多重空白壓成單一半形空白
      4. lower()      → 統一小寫（若需保留大小寫，移除此行）
    NaN → '' 以避免後續 .lower() 出錯
    """
    if pd.isna(s):
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    s = s.lower()
    return s
# ------------------------------------------------------------------


def HistoryDataSearch(
    base_dir: str = r"D:\CYCU\113_WebCrawler\CODE",
    data_dir: Optional[str] = None,
    format_file: Optional[str] = None,
    index_file: Optional[str] = None,
    price_file: Optional[str] = None,
    output_file: Optional[str] = None
) -> Tuple[Optional[pd.DataFrame], str]:
    """
    處理歷史資料搜尋，比對核價類別和功能類別，產生點數變更記錄。

    Args:
        base_dir (str): 基礎目錄路徑，預設為 D:\CYCU\113_WebCrawler\CODE
        data_dir (Optional[str]): 資料目錄路徑，預設為 base_dir/data
        format_file (Optional[str]): format_clean.csv 的完整路徑
        index_file (Optional[str]): IndexSQL_find.csv 的完整路徑
        price_file (Optional[str]): 價量調查品項108-112.csv 的完整路徑
        output_file (Optional[str]): 輸出檔案 HistoryData.csv 的完整路徑
    -------        
    Returns:
        依規則產生「點數變更記錄」並輸出 HistoryData.csv
    -------
    (DataFrame | None, str)
        • 若成功：回傳結果 DataFrame 與狀態訊息
        • 若失敗：DataFrame 為 None，訊息說明錯誤原因
    """
    # ---------- 1. 檔案路徑設定 -----------------------------------
    data_dir = data_dir or os.path.join(base_dir, "data")
    format_file = format_file or os.path.join(data_dir, "format_clean.csv")
    index_file  = index_file  or os.path.join(data_dir, "IndexSQL_find.csv")
    price_file  = price_file  or os.path.join(data_dir, "價量調查品項108-112_FINAL.csv")
    output_file = output_file or os.path.join(data_dir, "HistoryData.csv")

    try:
        # ---------- 2. 讀檔 --------------------------------------
        df_format = pd.read_csv(format_file, encoding="utf-8")
        df_index  = pd.read_csv(index_file,  encoding="utf-8")
        df_price  = pd.read_csv(price_file,  encoding="utf-8")

        # ---------- 3. 欄位檢查 ----------------------------------
        required_cols = {
            "df_format": ["核價類別"],
            "df_index":  ["名稱", "功能類別(前5碼)"],
            "df_price":  ["特材代碼前五碼", "核價類別名稱"]
        }
        for df_name, cols in required_cols.items():
            missing = [c for c in cols if c not in locals()[df_name].columns]
            if missing:
                raise ValueError(f"{df_name} 缺少欄位: {missing}")

        # ---------- 4. 建立 *_clean 欄位 -------------------------
        df_format["核價類別_clean"]     = df_format["核價類別"].apply(clean_str)
        df_index["名稱_clean"]          = df_index["名稱"].apply(clean_str)
        df_price["核價類別名稱_clean"] = df_price["核價類別名稱"].apply(clean_str)

        # ---------- 5. 先以「特材代碼前五碼」關聯價量調查 & IndexSQL_find
        result = pd.merge(
            df_price,
            df_index[["功能類別(前5碼)", "名稱_clean"]],
            left_on="特材代碼前五碼",
            right_on="功能類別(前5碼)",
            how="inner"
        )

        # ---------- 6. 只取 format_clean 中「同時存在於 IndexSQL_find」的核價類別
        """
        valid_categories = (
            df_format.loc[
                df_format["核價類別_clean"].isin(df_index["名稱_clean"]),
                "核價類別_clean"
            ].drop_duplicates()
        )
        df_format_valid = pd.DataFrame({"核價類別_clean": valid_categories})
        #---------- 如果輸出是 0 或只有零星幾個，就確定是「雙重條件」把資料全濾掉。
        print("step-check | valid_categories =", len(valid_categories))
        print(valid_categories[:20])        # 看看前 20 個長甚麼樣
        """
        df_format_valid = df_format[['核價類別_clean']].drop_duplicates()

        # ---------- 7. 再用核價類別 (clean) 做比對，產生 _merge
        result = result.merge(
            df_format_valid,
            left_on="核價類別名稱_clean",
            right_on="核價類別_clean",
            how="left",
            indicator=True
        )

        # ---------- 8. 設定點數變更記錄 -------------------------
        result["點數變更記錄"] = (result["_merge"] == "both").astype(int)

        # ---------- 9. 整理欄位順序 & 移除暫用欄 ----------------
        drop_cols = ["名稱_clean", "核價類別_clean", "_merge"]
        result = result.drop(columns=[c for c in drop_cols if c in result.columns])

        output_columns = [
            "年份", "特材代碼", "特材代碼前五碼", "核價類別名稱",
            "中英文品名", "產品型號/規格", "單位", "支付點數",
            "申請者簡稱", "許可證字號", "中文品名", "英文品名",
            "點數變更記錄"
        ]
        # 允許有欄位缺失（例如年份），僅保留存在的欄
        result = result[[c for c in output_columns if c in result.columns]]

        # ---------- 10. 輸出 ------------------------------------
        result.to_csv(output_file, encoding="utf-8", index=False)
        msg = (
            f"處理完成，共 {len(result)} 筆資料；"
            f"點數變更記錄=1：{result['點數變更記錄'].sum()} 筆\n"
            f"已輸出 → {output_file}"
        )
        return result, msg

    except FileNotFoundError as e:
        return None, f"檔案不存在：{e}"
    except ValueError as e:
        return None, f"資料欄位錯誤：{e}"
    except Exception as e:
        return None, f"未預期錯誤：{e}"


if __name__ == "__main__":
    # 預設路徑（依需要修改）
    df_out, status = HistoryDataSearch()
    print(status)