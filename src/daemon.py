#!/usr/bin/env python3
"""
daemon.py — 常駐程式
登入永豐 Shioaji → 訂閱台指期近月連續(TXFR1) 的 tick → 把最新報價原子寫入
STATE_FILE，供 SwiftBar plugin 每秒讀取。

純看盤、不下單 → 不需要啟用憑證(CA)，登入只要 API Key / Secret Key（讀自 Keychain）。
全時段(日盤+夜盤)：TXFR1 在開盤期間會持續推 tick，daemon 維持連線即可。

環境變數：
  SHIOAJI_SIMULATION=1   使用模擬環境（免正式權限、即時資料可用）；預設正式環境
  SHIOAJI_API_KEY / SHIOAJI_SECRET_KEY   覆寫 Keychain（臨時測試用）
  SHIOAJI_TEST_SECONDS=N 跑 N 秒就結束（煙霧測試）；不設則常駐

語法依永豐官方文件查證(2026-06)：
  登入 https://sinotrade.github.io/tutor/login/
  期貨 https://sinotrade.github.io/zh_TW/tutor/market_data/streaming/futures/
"""
import os
import json
import time
import signal
import subprocess
from collections import deque
import shioaji as sj

STATE_FILE = os.path.expanduser("~/.cache/shioaji-ticker/latest.json")
HISTORY_LEN = 12        # 走勢線格數
SAMPLE_SEC = 10         # 每 10 秒取樣一格存進走勢線

_history = deque(maxlen=HISTORY_LEN)
_last_sample = [0.0]    # 上次取樣的 monotonic 時間（用 list 以便在巢狀函式內改寫）


def keychain(service: str) -> str:
    """從 macOS Keychain 讀一筆 generic password；沒有就回空字串。"""
    try:
        return subprocess.check_output(
            ["security", "find-generic-password", "-s", service, "-w"],
            text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


# 優先讀環境變數(方便臨時測試)，否則讀 Keychain
API_KEY = os.environ.get("SHIOAJI_API_KEY") or keychain("shioaji-api-key")
SECRET_KEY = os.environ.get("SHIOAJI_SECRET_KEY") or keychain("shioaji-secret-key")

os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

if not API_KEY or not SECRET_KEY:
    raise SystemExit(
        "找不到金鑰。請先存入 Keychain（或跑 ./install.sh）：\n"
        '  security add-generic-password -a "$USER" -s shioaji-api-key    -U -w\n'
        '  security add-generic-password -a "$USER" -s shioaji-secret-key -U -w')

# SHIOAJI_SIMULATION=1 → 模擬環境；預設正式環境
SIMULATION = os.environ.get("SHIOAJI_SIMULATION", "0") == "1"
api = sj.Shioaji(simulation=SIMULATION)
api.login(api_key=API_KEY, secret_key=SECRET_KEY, contracts_timeout=15000)
print(f"[ok] 已登入（{'模擬' if SIMULATION else '正式'}環境）")

contract = api.Contracts.Futures.TXF.TXFR1   # 台指期「近月連續」全時段


def write_state(tick):
    price = float(tick.close)
    now = time.monotonic()
    if now - _last_sample[0] >= SAMPLE_SEC:      # 每 SAMPLE_SEC 取樣一格做走勢線
        _history.append(price)
        _last_sample[0] = now
    data = {
        "price": price,
        "chg": float(tick.price_chg),
        "pct": round(float(tick.pct_chg), 2),
        "ts": str(tick.time)[:8],
        "underlying": float(tick.underlying_price),   # 加權現貨(期現對照)
        "open": float(tick.open),
        "high": float(tick.high),
        "low": float(tick.low),
        "vol": int(tick.total_volume),
        "history": list(_history),
        "sim": SIMULATION,                    # 模擬模式旗標（plugin 用來顯示模擬 tag）
    }
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, STATE_FILE)          # 原子寫入，避免讀到寫一半的檔


@api.on_tick_fop_v1()
def on_tick(exchange, tick):
    # tick 欄位皆已實機驗證（close/price_chg/pct_chg/underlying_price/open/high/low/total_volume）
    write_state(tick)


api.subscribe(contract, quote_type=sj.QuoteType.Tick, version=sj.QuoteVersion.v1)
print("[ok] 已訂閱 TXFR1，開始推送…(Ctrl-C 結束)")

test_secs = os.environ.get("SHIOAJI_TEST_SECONDS")
if test_secs:
    time.sleep(float(test_secs))
else:
    signal.pause()                            # 維持連線直到被中止
