#!/usr/bin/env bash
# install.sh — 一鍵互動安裝（可重跑）
# 建 venv + 裝 shioaji、把金鑰存進 Keychain、依當前位置生成 launchd plist 並載入、
# 把 SwiftBar plugin 複製到你的 plugin 資料夾。所有路徑依本腳本所在位置動態決定。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LABEL="com.local.shioaji-ticker"
CACHE="$HOME/.cache/shioaji-ticker"
LA_DIR="$HOME/Library/LaunchAgents"
PLIST_DST="$LA_DIR/${LABEL}.plist"
VENV="$HERE/.venv"
PY="$VENV/bin/python"

echo "== shioaji-ticker 安裝 =="
echo "專案位置：$HERE"

# 1) 相依檢查
command -v python3 >/dev/null || { echo "✗ 缺 python3"; exit 1; }
command -v jq >/dev/null || echo "⚠️  缺 jq → 請先 'brew install jq'（plugin 需要）"
[ -d /Applications/SwiftBar.app ] || echo "⚠️  找不到 SwiftBar.app → 'brew install --cask swiftbar'"

# 2) venv + shioaji
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$PY" -m pip install --quiet --upgrade pip
"$PY" -c "import shioaji" >/dev/null 2>&1 || { echo "安裝 shioaji…"; "$PY" -m pip install --quiet shioaji; }
echo "✓ Python 環境就緒（$("$PY" -c 'import shioaji,sys; print("shioaji",shioaji.__version__)')）"

# 3) 模式
echo
read -r -p "用哪種模式？ [1] 模擬(預設)  [2] 正式： " MODE || true
if [ "${MODE:-1}" = "2" ]; then SIM=0; echo "→ 正式模式（需已開通正式權限）"; else SIM=1; echo "→ 模擬模式"; fi

# 4) Keychain（-w 不接值 → 提示輸入、不留 history；已存則略過）
echo
for s in shioaji-api-key shioaji-secret-key; do
  if security find-generic-password -s "$s" -w >/dev/null 2>&1; then
    echo "✓ Keychain 已有 $s"
  else
    echo "請輸入 $s（輸入時不顯示）："
    security add-generic-password -a "$USER" -s "$s" -U -w
  fi
done

# 5) 依當前位置生成 plist
mkdir -p "$CACHE" "$LA_DIR"
sed -e "s|{{LABEL}}|$LABEL|g" \
    -e "s|{{VENV_PYTHON}}|$PY|g" \
    -e "s|{{DAEMON_PY}}|$HERE/src/daemon.py|g" \
    -e "s|{{PROJECT_DIR}}|$HERE|g" \
    -e "s|{{LOG_DIR}}|$CACHE|g" \
    -e "s|{{SIMULATION}}|$SIM|g" \
    "$HERE/templates/txf-daemon.plist.tmpl" > "$PLIST_DST"
echo "✓ 已生成 $PLIST_DST"

# 6) 載入 launchd（先卸載舊的；重試以避開 bootout→bootstrap 的 race，且不讓 set -e 中斷）
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
for _ in 1 2 3 4 5; do
  launchctl bootstrap "gui/$(id -u)" "$PLIST_DST" 2>/dev/null && break
  sleep 1
done
if launchctl list | grep -q "$LABEL"; then
  echo "✓ daemon 已載入：$(launchctl list | grep "$LABEL")"
else
  echo "⚠️  daemon 載入失敗，請手動： launchctl bootstrap gui/\$(id -u) \"$PLIST_DST\""
fi

# 7) SwiftBar plugin
echo
DEFAULT_PLUG="$HOME/SwiftBarPlugins"
read -r -p "SwiftBar plugin 資料夾 [$DEFAULT_PLUG]： " PLUG || true
PLUG="${PLUG:-$DEFAULT_PLUG}"
mkdir -p "$PLUG"
cp "$HERE/plugin/txf.1s.sh" "$PLUG/" && chmod +x "$PLUG/txf.1s.sh"
echo "✓ plugin 複製到 $PLUG"
open "swiftbar://refreshallplugins" 2>/dev/null || true

echo
echo "== 完成 =="
echo "交易時段內，menu bar 應出現 TXF 報價與走勢線。"
echo "日誌：$CACHE/daemon.err.log"
echo "停止：launchctl bootout gui/\$(id -u)/$LABEL"
if [ "$SIM" = 0 ]; then
  echo
  echo "正式模式：若登入被擋(production permission)，需先完成開通測試："
  echo "  1) 永豐網站簽『期貨 API 簽署』、API Key 需勾『交易+正式環境』"
  echo "  2) 交易時段跑： PLACE=1 $VENV/bin/python $HERE/src/api_test.py"
fi
