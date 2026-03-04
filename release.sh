#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── 1. Load credentials ──────────────────────────────────────────────
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  echo "ERROR: .env file not found. Copy .env.example and fill in credentials."
  exit 1
fi
# shellcheck source=.env
source "$SCRIPT_DIR/.env"

# ── 2. Commit & push ─────────────────────────────────────────────────
MSG="${1:-build: release $(date '+%Y-%m-%d')}"
cd "$SCRIPT_DIR"
git add -A
git commit -m "$MSG" || echo "(nothing to commit)"
git push origin rust-version

# ── 3. Build ─────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/data-export/ink-density-tool-rs"
cargo build --release --target x86_64-pc-windows-gnu

# ── 4. Zip ───────────────────────────────────────────────────────────
ZIP="target/InkDensityTool.zip"
rm -f "$ZIP"
zip -j "$ZIP" target/x86_64-pc-windows-gnu/release/ink-density-tool.exe
echo "Zipped: $ZIP"

# ── 5. GitHub Release + email link ───────────────────────────────────
TAG="build-$(date '+%Y%m%d-%H%M%S')"
cd "$SCRIPT_DIR"
gh release create "$TAG" \
  "data-export/ink-density-tool-rs/$ZIP" \
  --title "InkDensityTool $TAG" \
  --notes "Automated build from rust-version branch." \
  --prerelease
DOWNLOAD_URL=$(gh release view "$TAG" --json assets --jq '.assets[0].browserDownloadUrl')
echo "Release URL: $DOWNLOAD_URL"

python3 - "$SMTP_USER" "$SMTP_PASS" "$SMTP_TO" "$DOWNLOAD_URL" <<'PYEOF'
import sys, smtplib
from email.mime.text import MIMEText

user, pw, to, url = sys.argv[1:]

body = f"""New InkDensityTool build ready.

Download: {url}

(GitHub release — no expiry, login not required to download)
"""

msg = MIMEText(body, 'plain')
msg['From'] = user
msg['To'] = to
msg['Subject'] = "InkDensityTool build ready"

with smtplib.SMTP('smtp.gmail.com', 587) as s:
    s.ehlo()
    s.starttls()
    s.login(user, pw)
    s.sendmail(user, to, msg.as_string())
    print(f"Sent to {to}")
PYEOF
