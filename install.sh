#!/bin/bash
# 安装「二简字·拼音」到 Rime (macOS / 鼠鬚管 Squirrel)
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DST="${RIME_USER_DIR:-$HOME/Library/Rime}"
[ -d "$DST" ] || { echo "找不到 Rime 用户目录: $DST"; exit 1; }

echo "→ 安装到 $DST"
mkdir -p "$DST/opencc"
cp "$SRC/erjian.schema.yaml" "$DST/"
cp "$SRC/opencc/erjian_"*.txt "$SRC/opencc/erjian_"*.json "$DST/opencc/"

# 把 erjian 加进方案列表
CUSTOM="$DST/default.custom.yaml"
if [ -f "$CUSTOM" ] && grep -q 'schema: erjian' "$CUSTOM"; then
  echo "→ default.custom.yaml 已含 erjian，跳过"
else
  cp "$CUSTOM" "$CUSTOM.bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
  if [ -f "$CUSTOM" ] && grep -q 'schema_list/+:' "$CUSTOM"; then
    # 插到 schema_list/+ 的第一项之前
    python3 - "$CUSTOM" <<'PY'
import sys, re
p = sys.argv[1]
s = open(p, encoding='utf-8').read()
m = re.search(r'^(\s*)schema_list/\+:\s*\n', s, re.M)
indent = m.group(1)
item_indent = re.search(r'^(\s*)- schema:', s[m.end():], re.M).group(1)
s = s[:m.end()] + f'{item_indent}- schema: erjian\n' + s[m.end():]
open(p, 'w', encoding='utf-8').write(s)
print('   已插入 - schema: erjian')
PY
  else
    printf '\npatch:\n  schema_list/+:\n    - schema: erjian\n' >> "$CUSTOM"
    echo "   已追加 schema_list/+"
  fi
fi

echo "→ 重新部署"
SQ="/Library/Input Methods/Squirrel.app/Contents/MacOS"
"$SQ/rime_deployer" --build "$DST" "/Library/Input Methods/Squirrel.app/Contents/SharedSupport"
"$SQ/Squirrel" --reload 2>/dev/null || echo "   (请手动点鼠鬚管菜单的「重新部署」)"
echo "✓ 完成"
