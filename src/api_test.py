#!/usr/bin/env python3
"""api_test.py — 永豐 API 測試（解鎖正式行情權限用）

模擬模式跑「登入 + 期貨下單」兩個測試；下單為遠離市價的限價單(不會成交)，
送 2 筆間隔 >1 秒，完成後自動取消。永豐審核(約5分)通過後才會開通正式權限。

安全開關：預設只「建立」委託物件並印出(不送單)；設環境變數 PLACE=1 才會真的送出模擬單。
前提：需先在永豐簽好「期貨 API 簽署」，且簽署時間早於本測試時間。
       且 API Key 需勾選「交易」與「正式環境」權限（建立後不可改，缺則重新產一把）。
測試時段：週一~五 08:00-20:00；台指期交易時段 08:45-13:45 / 15:00-翌05:00。
出處：https://sinotrade.github.io/zh/tutor/prepare/terms/
"""
import os
import subprocess
import time
import shioaji as sj


def kc(s):
    try:
        return subprocess.check_output(
            ["security", "find-generic-password", "-s", s, "-w"],
            text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


PLACE = os.environ.get("PLACE", "0") == "1"

api = sj.Shioaji(simulation=True)
api.login(api_key=kc("shioaji-api-key"),
          secret_key=kc("shioaji-secret-key"),
          contracts_timeout=15000)
print("[1] 登入測試 OK（模擬模式）")

acct = api.futopt_account
if acct is None:
    raise SystemExit("找不到期貨帳戶 → 請確認此 key 綁的是期貨戶。")
print(f"[info] 期貨帳戶 signed={getattr(acct, 'signed', None)}")

contract = api.Contracts.Futures.TXF.TXFR1


def build_order():
    return sj.FuturesOrder(
        action=sj.Action.Buy,
        price=40000,                       # 遠低於市價的限價 → 不會成交
        quantity=1,
        price_type=sj.FuturesPriceType.LMT,
        order_type=sj.OrderType.ROD,
        octype=sj.FuturesOCType.Auto,      # 自動開平倉
        account=acct,
    )


o = build_order()
print("[2] 委託物件建立成功：")
print(o)

if not PLACE:
    print("\n[dry-run] 未送單。用 PLACE=1 重跑即送出測試單。")
    api.logout()
    raise SystemExit(0)

# 註：模擬環境的 signed 恆為 False，不代表沒簽署。真正的「期貨 API 簽署」在永豐網站完成；
# 本次下單測試送審通過後，正式環境的 signed 才會變 True、正式行情/交易權限才開通。
print(f"[note] 模擬環境 signed={getattr(acct,'signed',None)}（恆為 False，正常）；開始送下單測試…")

trades = []
for i in range(2):
    t = api.place_order(contract, build_order())
    print(f"[3] 下單測試 #{i+1} → status={t.status.status}")
    trades.append(t)
    time.sleep(1.5)                        # 官方要求間隔 >1 秒

# 收尾：把沒成交的測試單取消，保持乾淨
api.update_status(acct)
for t in trades:
    try:
        if t.status.status not in ("Filled", "Cancelled", "Failed"):
            api.cancel_order(t)
    except Exception as e:
        print("[warn] 取消測試單:", e)

print("\n[OK] 登入 + 下單測試已送出。請到永豐 API 後台等審核(約5分)，正式行情權限即生效。")
api.logout()
