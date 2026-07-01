#!/bin/bash
# txf.1s.sh — SwiftBar plugin：每秒讀 daemon 寫的最新台指期報價貼到選單列。
# 主行：TXF <價> ▲<漲跌幅>% <走勢線>（紅漲綠跌）；超過 STALE 秒沒更新顯示「休市」。
# 下拉：加權現貨對照、開高低量、更新時間、重新整理。
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"   # 找得到 jq
STATE="$HOME/.cache/shioaji-ticker/latest.json"
STALE=30                                                # 超過幾秒沒更新視為休市

if [ ! -f "$STATE" ]; then
  echo "TXF --"; echo "---"; echo "daemon 未啟動或尚無資料"; exit 0
fi

AGE=$(( $(date +%s) - $(stat -f %m "$STATE") ))
[ "$AGE" -gt "$STALE" ] && STALEF=1 || STALEF=0

# 走勢線：history 以 min→max 正規化成 8 階區塊字元；不足 2 點不顯示；全平顯示中段
SPARK=$(jq -r '
  ["▁","▂","▃","▄","▅","▆","▇","█"] as $b |
  (.history // []) as $h |
  if ($h|length) < 2 then ""
  else
    ($h|min) as $lo | ($h|max) as $hi |
    ($h | map(if $hi==$lo then 4 else (((. - $lo)/($hi-$lo))*7 | round) end)
        | map($b[.]) | join(""))
  end' "$STATE")

# 主行（menu bar）
jq -r --argjson stale "$STALEF" '
  (if .chg==null then "" elif .chg>=0 then "▲" else "▼" end) as $a |
  (if $stale==1 then "#888888"
   elif .chg==null then "white"
   elif .chg>=0 then "red" else "green" end) as $c |
  (if .sim then " 🧪模擬" else "" end) as $sim |
  if $stale==1 then "TXF \(.price|floor) 休市\($sim) | color=\($c)"
  elif .chg==null then "TXF \(.price|floor)\($sim)"
  else "TXF \(.price|floor) \($a)\(.pct|fabs)%\($sim) | color=\($c)" end' "$STATE"

# 下拉選單
echo "---"
[ -n "$SPARK" ] && echo "走勢 $SPARK  (近 2 分鐘) | font=Menlo"
jq -r '
  "台指近月連續 TXFR1 | font=Menlo",
  (if .underlying then "加權現貨 \(.underlying|floor)  (期現對照) | font=Menlo" else empty end),
  (if .open then "開\(.open|floor) 高\(.high|floor) 低\(.low|floor) 量\(.vol) | font=Menlo" else empty end),
  "更新 \(.ts)  ｜ 永豐 Shioaji\(if .sim then "（模擬）" else "" end) | font=Menlo"' "$STATE"
[ "$STALEF" = 1 ] && echo "⚠️ 已 ${AGE}s 未更新（休市/空檔） | color=#888888 font=Menlo"
echo "重新整理 | refresh=true"
echo "🔄 重新連線 (重啟 daemon) | bash=/bin/launchctl param1=kickstart param2=-k param3=gui/$(id -u)/com.local.shioaji-ticker terminal=false refresh=true"
