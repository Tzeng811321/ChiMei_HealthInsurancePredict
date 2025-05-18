# ChiMei_HealthInsurancePredict
It's a point predict model for health insurance in ROC.
# 安裝說明（Conda + GitHub）

> 這份文件示範如何在 **Windows / macOS / Linux** 上
>
> 1. 建立 *conda* 虛擬環境
> 2. 安裝 **** APP_UI_SQLver.py 專案所需套件（PyQt5、pandas…）
> 3. 從 GitHub 下載程式碼並執行
>
> 只要跟著指令一步一步操作，即可在 5 分鐘內跑起 UI。

---

## 0. 先決條件

| 軟體                       | 版本建議    | 下載連結                                                                                             |
| ------------------------ | ------- | ------------------------------------------------------------------------------------------------ |
| **Git**                  | ≥ 2.40  | [https://git-scm.com/downloads](https://git-scm.com/downloads)                                   |
| **Miniconda / Anaconda** | ≥ 23.11 | [https://docs.conda.io/en/latest/miniconda.html](https://docs.conda.io/en/latest/miniconda.html) |

安裝好後，請開啟「**終端機 / CMD / PowerShell / Anaconda Prompt**」。

---

## 1. 取得專案原始碼

```bash
# 建議放在 ~/projects 或任何愛用目錄
mkdir -p ~/projects && cd ~/projects

# ✅ 方式 A：Git Clone（推薦，可保留 Git 版本資訊）
git clone https://github.com/<your-username>/integrated_ui.git
cd integrated_ui

# ⬇️ 方式 B：直接下載 Zip（不熟 Git 可用）
# 1) 進 GitHub 按 Code → Download ZIP
# 2) 解壓縮後 cd 至資料夾
```

> **接下來指令皆在 ****`integrated_ui/`**** 目錄內進行**

---

## 2. 建立 Conda 虛擬環境

### 方法一：直接下指令（最直白）

```bash
# 建環境（請依需求選擇 Python 版本）
conda create -n medata_ui python=3.11 -y

# 啟用環境
conda activate medata_ui
```

### 方法二：使用環境檔（可重現性高）

1. 在專案根目錄建立 `environment.yml`（若已提供可跳過）

   ```yaml
   name: medata_ui
   channels:
     - conda-forge
   dependencies:
     - python=3.11
     - pandas
     - fuzzywuzzy
     - python-Levenshtein
     - pip
     - pip:
       - PyQt5  # conda-forge 的 PyQt 包叫 pyqt；這裡示範 pip 安裝
   ```

2. 一行建環境並啟用：

   ```bash
   conda env create -f environment.yml
   conda activate medata_ui
   ```

---

## 3. 安裝專案相依套件

# 加裝主要套件（conda-forge 提速）
condainstall -c conda-forge pandas fuzzywuzzy python-Levenshtein -y
 
# PyQt 建議用 pip 取得最新版
pip install PyQt5
```

> `python-Levenshtein` 能大幅加速 fuzzywuzzy，比純 Python 版本快 5～10 倍。

---

## 4. 執行程式

```bash
# 確認目前位於 integrated_ui/ 目錄
python integrated_ui.py
```

第一次執行會跳出檔案對話框，讓你選擇含
`IndexCode.csv`、`format_clean.csv`… 等資料檔的資料夾。

---

## 5. 常見問題（FAQ）

| 現象                                         | 可能原因                     | 解法                                                                    |
| ------------------------------------------ | ------------------------ | --------------------------------------------------------------------- |
| 出現 `ImportError: DLL load failed`（Windows） | Qt 動態庫衝突                 | 確認只安裝 **一個** PyQt 來源；若同時使用 conda 的 *pyqt* 與 pip 的 *PyQt5* 可能打架 → 移除其一 |
| UI 按鈕卡住、Terminal 無回應                       | 長時間運算在主執行緒               | integrated\_ui 已用 `QThread`；若自行改寫請保留背景執行機制                            |
| `ModuleNotFoundError: sqlite3`             | 系統 Python 缺少 sqlite3（稀有） | 重新建 conda 環境或 `conda install sqlite`                                  |

---

## 6. 移除環境（選擇性）

```bash
conda deactivate
conda env remove -n medata_ui
```

> 一鍵刪除虛擬環境與所有安裝套件。

---

🎉  恭喜！現在你已能在隔離的 conda 環境中執行
**integrated\_ui**，並享受 PyQt5 帶來的圖形化體驗。祝開發順利！
