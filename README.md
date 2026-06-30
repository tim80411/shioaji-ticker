# shioaji-ticker

macOS 選單列（menu bar）的**台指期 TXF 近月連續、近即時**報價小工具。
資料走永豐金證券官方 **Shioaji** API，金鑰存在 **macOS Keychain**（不落地、不進版控）。

```
menu bar：  TXF 46618 ▼0.34% █▄▅▁          ← 每秒更新、紅漲綠跌、含即時走勢線
點開：      台指近月連續 TXFR1
            加權現貨 46125  (期現對照)
            開46684 高46700 低46607 量1565
            更新 15:09:37 ｜ 永豐 Shioaji
```

## 運作架構

```
launchd ─ src/daemon.py   登入 Shioaji → 訂閱 TXFR1 tick → 原子寫 ~/.cache/shioaji-ticker/latest.json
                                                              │
SwiftBar ─ plugin/txf.1s.sh   每秒讀 latest.json → 畫到選單列
```
- daemon 常駐（launchd，開機自動起、掛掉自動重啟）。
- 走勢線：daemon 每 10 秒取樣價格、留 12 格（約 2 分鐘趨勢），plugin 以 Unicode 區塊字元 `▁▂▃▄▅▆▇█` 畫出。
- 休市偵測：`latest.json` 超過 30 秒沒更新 → 顯示灰字「休市」。

## 需求

- macOS、Python 3.8+
- [SwiftBar](https://github.com/swiftbar/SwiftBar)：`brew install --cask swiftbar`
- `jq`：`brew install jq`
- 一個永豐金證券帳戶 + Shioaji API Key（[申請](https://sinotrade.github.io/zh/tutor/prepare/token/)）

## 安裝

```bash
./install.sh
```
一鍵互動完成：建 venv＋裝 shioaji、把金鑰存進 Keychain、依當前位置生成 launchd plist 並載入、
把 plugin 複製到你的 SwiftBar 資料夾。可重跑（換 key／換模式再跑一次即可）。

## 三種模式

| 模式 | 怎麼用 | 說明 |
|---|---|---|
| **模擬** | install 時選 [1]，或 plist `SHIOAJI_SIMULATION=1` | 免正式權限即可看即時行情。最快上手。 |
| **正式** | install 時選 [2]，或 `SHIOAJI_SIMULATION=0` | 需已開通正式權限（見下）。 |
| **開通測試** | `PLACE=1 .venv/bin/python src/api_test.py` | 模擬環境跑登入＋下單測試，送永豐審核以解鎖正式權限。 |

### 解鎖正式權限（首次）
永豐規定：先在網站簽**期貨 API 簽署**、且 API Key 需勾**「交易」+「正式環境」**（建立後不可改，缺則重產一把），
再於交易時段跑 `api_test.py`（模擬下單測試，簽署時間需早於測試），審核約 5 分鐘後生效。
出處：<https://sinotrade.github.io/zh/tutor/prepare/terms/>

## 管理

```bash
launchctl list | grep shioaji-ticker             # 是否在跑
tail -f ~/.cache/shioaji-ticker/daemon.err.log   # 看錯誤
launchctl bootout gui/$(id -u)/com.local.shioaji-ticker   # 停止（KeepAlive 下要 bootout）
```

## 安全

- API 金鑰只存 macOS Keychain（`shioaji-api-key` / `shioaji-secret-key`），程式不含任何 secret。
- 純看盤不需憑證(CA)；`api_test.py` 的下單為**模擬限價單、不會成交**，且預設 dry-run（要 `PLACE=1` 才送）。

## 免責

個人自用工具，與永豐金證券無任何關係。行情資料之使用請遵循永豐 Shioaji 服務條款。
本工具不構成任何投資建議；使用風險自負。

## License

MIT，見 [LICENSE](LICENSE)。
