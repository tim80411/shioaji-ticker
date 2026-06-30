# 設計記錄

## 為什麼是 menu bar，不是「真的 widget」

目標情境：**工作時隨時瞄一眼**台指期。比較三種形態：

| 形態 | 放哪 | 即時性 | 對「邊工作邊瞄」 |
|---|---|---|---|
| **menu bar（採用）** | 右上角永遠可見 | 每秒 | ⚡ 最佳 |
| Übersicht 桌面卡片 | 桌面，會被視窗蓋 | 每秒 | 🐢 要先顯示桌面 |
| WidgetKit 原生卡片 | 通知中心/桌面 | 系統節流 ~15 分 | ❌ 非即時＋要 Swift |

WidgetKit 的 timeline 模型由系統節流刷新（一天數十次），**做不到近即時**，與需求衝突。
Übersicht 雖可每秒，但桌面卡片會被視窗蓋住、瞄一眼還要先顯示桌面。
→ menu bar 是該情境最佳形態，因此「升級 menu bar 本身」而非換形態。

## 資料源：永豐 Shioaji（合規）

台指期在 TAIFEX 交易。期貨即時行情屬受授權資料；合規的近即時取得只有「期貨商官方 API」。
使用者有永豐戶 → 用官方 Shioaji（Python SDK）。純看盤不需憑證(CA)。
- 近月連續合約：`api.Contracts.Futures.TXF.TXFR1`（含日盤+夜盤全時段）。
- tick 自帶 `close / price_chg / pct_chg / underlying_price / open / high / low / total_volume`（已實機驗證欄位）。
- 不使用任何未公開端點（如期交所 mis 私有 API），避免 ToS／法律風險。

## 架構

`launchd → daemon.py（訂閱 tick、寫 latest.json）→ SwiftBar plugin（每秒讀檔顯示）`

- daemon 是推送式（WebSocket）長連線，與 SwiftBar 的「每秒重跑腳本」模型不合 →
  拆成 producer(daemon 常駐) / consumer(plugin 讀檔)。
- 金鑰讀自 Keychain（`security find-generic-password`），程式不含 secret。
- plist 由 install.sh 從模板依當前位置生成 → 專案可搬移、可公開（不含使用者絕對路徑）。

## 走勢線

- daemon 每 `SAMPLE_SEC`(10) 秒取樣現價，存進 `deque(maxlen=HISTORY_LEN=12)` → 約 2 分鐘窗。
- plugin 將 history 以 min→max 正規化為 8 階區塊字元；不足 2 點不畫；全平顯示中段。

## 模式

- 模擬 `SHIOAJI_SIMULATION=1`：免正式權限、即時資料可用（實測夜盤可得 live tick）。
- 正式 `=0`：需先完成永豐「期貨 API 簽署 + 模擬下單測試」解鎖（api_test.py），且 API Key 需勾「交易+正式環境」。
- 模擬環境 `account.signed` 恆為 False，不代表未簽署。

## YAGNI（不做）

桌面卡片 / WidgetKit、圖片版走勢線、長期歷史儲存。
