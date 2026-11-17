# 土木工地日常行政與材料進出貨管理系統

課程：單元7 AI Agent 的世界  
技術：Python Flask + SQLite + HTML/CSS/JavaScript  
資料庫：site_management.db（本機單一檔案，免架設伺服器）

## 功能
1. 材料進出貨：進貨、領料、即時計算庫存，低於最低庫存量時紅燈警示。
2. 協力廠商：名稱、工種、聯絡人、電話、統編、評價。
3. 單據關聯：材料進貨可指定供應商、單價、發票號碼、對帳狀態。
4. 行政零用金：便當、五金耗材等支出。
5. 機具租借：借出與歸還狀態。
6. CRUD：新增、查詢、刪除；資料直接寫入 SQLite。

## 執行
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
pip install -r requirements.txt
python app.py
```
瀏覽器開啟 http://127.0.0.1:5000

## AI Agent 說明
本專案以 AI Agent 協助進行需求分析、資料表設計、Flask 程式產生、介面整合與測試規劃；資料庫採 SQLite，符合「本機單一檔案資料庫」要求。

## 部署
可部署至 Render、Railway、PythonAnywhere 等支援 Flask 的平台。若需公開網址，必須在平台建立服務並取得該平台提供的網址；本壓縮檔本身不會自動產生公開網址。
