#!/usr/bin/env bash
# Full first-time setup. Run from backend/ directory.
# Usage: bash scripts/run_full_setup.sh

set -e
echo "=== Video KYC Backend Setup ==="

# 1. Copy env
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  ✓ Created .env — fill in your secrets before continuing"
  echo "  Required: SUPABASE_DB_URL, SUPABASE_SERVICE_ROLE_KEY, GEMINI_API_KEY, JWT_SECRET"
  exit 1
fi

# 2. Scaffold models dir
echo ""
echo "--- Setting up models directory ---"
python -m scripts.create_model_dir

# 3. Alembic migration
echo ""
echo "--- Running database migrations ---"
python -m alembic upgrade head

# 4. Seed admin user
echo ""
echo "--- Creating default admin user ---"
python -m scripts.seed_admin

# 5. Supabase buckets
echo ""
echo "--- Creating Supabase Storage buckets ---"
python -m scripts.setup_supabase

# 6. GeoIP (optional — needs MAXMIND_LICENSE_KEY)
if [ -n "$MAXMIND_LICENSE_KEY" ]; then
  echo ""
  echo "--- Downloading GeoIP database ---"
  python -m scripts.download_geoip
else
  echo ""
  echo "  ⚠ MAXMIND_LICENSE_KEY not set — skipping GeoIP download"
  echo "    Get a free key at https://www.maxmind.com/en/geolite2/signup"
  mkdir -p data/geoip data
fi

echo ""
echo "=== Setup complete ==="
echo "  Start server : docker compose up"
echo "  Run tests    : pytest"
echo "  API docs     : http://localhost:8000/docs"
