#!/bin/bash
# Initialize .env from .env.example, then overwrite SECRET_KEY + FERNET_ENCRYPTION_KEY
# with random values for local dev. Idempotent: refuses to overwrite existing .env
# unless --force is passed.
#
# Usage:
#   ./scripts/init_env.sh         # creates .env only if it doesn't exist
#   ./scripts/init_env.sh --force # regenerates .env from scratch
#
# Wrapper: `make init-env` and `make init-env FORCE=1`.

set -e

FORCE=false
if [[ "${1:-}" == "--force" ]]; then
    FORCE=true
fi

cd "$(dirname "$0")/.."

if [[ -f .env ]] && ! $FORCE; then
    echo "  · .env already exists. Use --force to regenerate."
    exit 0
fi

if [[ ! -f .env.example ]]; then
    echo "  ✗ .env.example not found in $PWD. Are you in a project root?"
    exit 1
fi

# Step 1: start from .env.example (preserves structure: SQLite default + Postgres commented).
cp .env.example .env

# Step 2 + 3: generate random secrets and write them in one Python pass.
# This avoids shell-escape pitfalls (sed + chars like $, #, (, ) in random keys).
python3 <<'PYEOF'
import secrets
import re
from pathlib import Path

env_path = Path(".env")

# Use only URL-safe / .env-safe chars. NO $, #, (, ), =, +, &, *, |, \, ",
# because those break either shell expansion or .env parsers (e.g. python-dotenv).
# Django's get_random_secret_key() uses [a-zA-Z0-9...] — same approach.
SECRET_KEY = "".join(
    secrets.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!_-.")
    for _ in range(64)
)
FERNET_KEY = __import__("base64").urlsafe_b64encode(secrets.token_bytes(32)).decode()

content = env_path.read_text()

# Replace SECRET_KEY=... (any value, possibly empty).
content = re.sub(r"^SECRET_KEY=.*$", f"SECRET_KEY={SECRET_KEY}", content, count=1, flags=re.MULTILINE)

# FERNET_ENCRYPTION_KEY line may have empty value or be absent. Always set it.
if re.search(r"^FERNET_ENCRYPTION_KEY=.*$", content, flags=re.MULTILINE):
    content = re.sub(
        r"^FERNET_ENCRYPTION_KEY=.*$",
        f"FERNET_ENCRYPTION_KEY={FERNET_KEY}",
        content,
        count=1,
        flags=re.MULTILINE,
    )
else:
    content += f"\nFERNET_ENCRYPTION_KEY={FERNET_KEY}\n"

env_path.write_text(content)

print(f"  · SECRET_KEY replaced ({len(SECRET_KEY)} chars, URL-safe alphabet).")
print(f"  · FERNET_ENCRYPTION_KEY replaced.")
PYEOF

echo "  ✓ .env created from .env.example."
echo "  · DB default kept from .env.example (SQLite for local dev, Postgres commented for prod)."