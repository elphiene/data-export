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

# ── 4. Zip (password-protected so Gmail doesn't block the exe) ───────
ZIP="target/InkDensityTool.zip"
rm -f "$ZIP"
zip -j -P "$ZIP_PASS" "$ZIP" target/x86_64-pc-windows-gnu/release/ink-density-tool.exe
echo "Zipped: $ZIP  (password: $ZIP_PASS)"

# ── 5. Upload & email link ────────────────────────────────────────────
echo "Uploading to 0x0.st..."
DOWNLOAD_URL=$(curl -# -F"file=@$ZIP" https://0x0.st)
echo "Upload URL: $DOWNLOAD_URL"

python3 - "$SMTP_USER" "$SMTP_PASS" "$SMTP_TO" "$DOWNLOAD_URL" "$ZIP_PASS" <<'PYEOF'
import sys, smtplib
from email.mime.text import MIMEText

user, pw, to, url, zip_pass = sys.argv[1:]

body = f"""New InkDensityTool build ready.

Download: {url}
Zip password: {zip_pass}

Link expires in 14 days.
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
