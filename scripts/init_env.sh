#!/bin/bash
# Initialize .env with random SECRET_KEY + FERNET_ENCRYPTION_KEY for local dev.
# Usage: ./scripts/init_env.sh [--force]

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

SECRET_KEY=$(python3 -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits+'!@#\$%^&*(-_=+)') for _ in range(64)))")
FERNET_KEY=$(python3 -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())")
SLUG=$(basename "$PWD")

cat > .env <<EOF
SECRET_KEY=$SECRET_KEY
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
FERNET_ENCRYPTION_KEY=$FERNET_KEY
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/$SLUG
EOF

echo "  ✓ .env created with SECRET_KEY (64 chars), FERNET_ENCRYPTION_KEY, DATABASE_URL=postgresql://.../$SLUG"
