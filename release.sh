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

# ── 4. Strip + gzip + base64 encode as .txt ──────────────────────────
EXE="target/x86_64-pc-windows-gnu/release/ink-density-tool.exe"
GZ="target/ink-density-tool.exe.gz"
TXT="target/InkDensityTool.txt"
x86_64-w64-mingw32-strip "$EXE" 2>/dev/null || true
gzip -9 -c "$EXE" > "$GZ"
base64 "$GZ" > "$TXT"
SIZE=$(du -sh "$TXT" | cut -f1)
echo "Encoded: $TXT ($SIZE)"

# ── 5. Email with .txt attachment ─────────────────────────────────────
python3 - "$SMTP_USER" "$SMTP_PASS" "$SMTP_TO" "$TXT" <<'PYEOF'
import sys, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

user, pw, to, txt_path = sys.argv[1:]

decode_cmd = r"""$b=[Convert]::FromBase64String((Get-Content -Raw InkDensityTool.txt))
$ms=New-Object IO.MemoryStream(,$b)
$gz=New-Object IO.Compression.GzipStream($ms,[IO.Compression.CompressionMode]::Decompress)
$out=New-Object IO.MemoryStream; $gz.CopyTo($out)
[IO.File]::WriteAllBytes("$PWD\ink-density-tool.exe",$out.ToArray())"""

msg = MIMEMultipart()
msg['From'] = user
msg['To'] = to
msg['Subject'] = "InkDensityTool build ready"
msg.attach(MIMEText(
    "Latest build attached as InkDensityTool.txt.\n\n"
    "To decode: save the attachment, open PowerShell in the same folder, paste and run:\n\n"
    f"{decode_cmd}\n\n"
    "Then run ink-density-tool.exe.",
    'plain'
))

with open(txt_path, 'rb') as f:
    part = MIMEBase('text', 'plain')
    part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="InkDensityTool.txt"')
    msg.attach(part)

with smtplib.SMTP('smtp.gmail.com', 587) as s:
    s.ehlo()
    s.starttls()
    s.login(user, pw)
    s.sendmail(user, to, msg.as_string())
    print(f"Sent to {to}")
PYEOF
