# integrated_ui.py
# -*- coding: utf-8 -*-
"""
PyQt5 使用者介面：整合 IndexSQL 與 HistoryDataSearch
======================================================
Last update: 2025‑05‑18
Author: ChatGPT (auto‑generated)

▶ 功能
-------
1. 讓使用者輸入 **產品關鍵字** ➜ 呼叫 `IndexSQL.search_products()`。
2. 等待 `IndexSQL` 產生 *IndexSQL_find.csv* 後，接著呼叫
   `HistoryDataSearch.HistoryDataSearch()` 產生點數變更 DataFrame。
3. 將結果以 `QTableView` 顯示，並在下方狀態列回報成功 / 失敗。

📦 依賴
-------
```
pip install PyQt5 pandas fuzzywuzzy python-Levenshtein
```

📁 建議目錄
-----------
```
project/
├─ data/
│  ├─ IndexCode.csv
│  ├─ format_clean.csv
│  ├─ 價量調查品項108-112.csv   ← 若檔名不同請自行修改
├─ IndexSQL.py
├─ HistoryDataSearch.py
└─ integrated_ui.py              ← 本檔
```

> *執行時會請你選擇 `data/` 目錄，以便讀寫 CSV 與 DB 檔。*

"""
import sys
import os
from typing import Optional

import pandas as pd
from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, pyqtSignal, QObject, QThread
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QTableView,
    QMessageBox,
    QFileDialog,
)

# 匯入你的兩支核心腳本
import IndexSQL
import HistoryDataSearch

###############################################################################
# QAbstractTableModel – 把 Pandas DataFrame 掛到 QTableView
###############################################################################
class PandasModel(QAbstractTableModel):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self._df = df

    def rowCount(self, parent=None):
        return len(self._df)

    def columnCount(self, parent=None):
        return len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            value = self._df.iloc[index.row(), index.column()]
            return str(value)
        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._df.columns[section])
            else:
                return str(section)
        return QVariant()

###############################################################################
# Worker (放到 QThread) – 避免 UI 被阻塞
###############################################################################
class Worker(QObject):
    finished = pyqtSignal(object, str, str)  # df, status_msg, error_msg

    def __init__(self, keyword: str, base_dir: str):
        super().__init__()
        self.keyword = keyword
        self.base_dir = base_dir

    def run(self):
        try:
            data_dir = os.path.join(self.base_dir, "data")
            # 1️⃣ 執行 IndexSQL 搜尋
            csv_indexcode = os.path.join(data_dir, "IndexCode.csv")
            db_file = os.path.join(data_dir, "products.db")
            IndexSQL.search_products(
                self.keyword,
                db_file=db_file,
                csv_file=csv_indexcode,
            )

            # 2️⃣ 執行 HistoryDataSearch
            df, msg = HistoryDataSearch.HistoryDataSearch(
                base_dir=self.base_dir,
                data_dir=data_dir,
                format_file=os.path.join(data_dir, "format_clean.csv"),
                index_file=os.path.join(data_dir, "IndexSQL_find.csv"),
                price_file=os.path.join(data_dir, "價量調查品項108-112.csv"),
            )

            if df is None:
                self.finished.emit(pd.DataFrame(), "", msg)
            else:
                self.finished.emit(df, msg, "")

        except Exception as e:
            self.finished.emit(pd.DataFrame(), "", str(e))

###############################################################################
# 主視窗
###############################################################################
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("醫材變更紀錄搜索器 SQL.ver UI")
        self.resize(1100, 700)

        central = QWidget()
        self.setCentralWidget(central)
        vbox = QVBoxLayout(central)

        # --- 上：輸入區 ---
        hbox = QHBoxLayout()
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("輸入產品關鍵字…")
        self.search_btn = QPushButton("搜尋")
        hbox.addWidget(self.keyword_edit, 1)
        hbox.addWidget(self.search_btn)
        vbox.addLayout(hbox)

        # --- 中：結果表格 ---
        self.table = QTableView()
        vbox.addWidget(self.table, 1)

        # --- 下：狀態列 ---
        self.status = QLabel("準備就緒")
        vbox.addWidget(self.status)

        # 事件綁定
        self.search_btn.clicked.connect(self.start_search)

    # ---------------------------------------------------------------------
    def start_search(self):
        keyword = self.keyword_edit.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提醒", "請先輸入關鍵字！")
            return

        # 讓使用者選擇專案根目錄（裡面應該有 data/ 資料夾）
        base_dir = QFileDialog.getExistingDirectory(self, "選擇專案根目錄")
        if not base_dir:
            return

        # UI disable + 狀態更新
        self.search_btn.setEnabled(False)
        self.status.setText("處理中…請稍候")

        # 建立執行緒
        self.thread = QThread()
        self.worker = Worker(keyword, base_dir)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    # ---------------------------------------------------------------------
    def on_finished(self, df: pd.DataFrame, status_msg: str, error_msg: str):
        self.search_btn.setEnabled(True)
        if error_msg:
            QMessageBox.critical(self, "錯誤", error_msg)
            self.status.setText("失敗")
            return

        if df.empty:
            QMessageBox.information(self, "結果", "沒有找到符合資料！")
            self.status.setText(status_msg or "沒有資料")
            return

        model = PandasModel(df)
        self.table.setModel(model)
        self.status.setText(status_msg or "完成！")

###############################################################################
# 入口點
###############################################################################
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())