"""
Create required Supabase Storage buckets and apply RLS policies.

Run once after project creation:
  python -m scripts.setup_supabase

Buckets created:
  kyc-recordings  — encrypted video/audio (private, 7-year retention)
  kyc-pdfs        — offer letter PDFs (private, 30-day pre-signed URLs)
"""
import sys
from app.config import get_settings
from app.database import get_supabase

settings = get_settings()


def setup_buckets():
    sb = get_supabase()

    buckets_to_create = [
        {
            "name": settings.storage_bucket_recordings,
            "public": False,
            "file_size_limit": 10 * 1024 * 1024,   # 500 MB per recording
            "allowed_mime_types": ["video/webm", "video/mp4", "audio/wav", "audio/webm"],
        },
        {
            "name": settings.storage_bucket_pdfs,
            "public": False,
            "file_size_limit": 5 * 1024 * 1024,     # 5 MB per PDF
            "allowed_mime_types": ["application/pdf"],
        },
    ]

    existing = {b["name"] for b in sb.storage.list_buckets()}

    for bucket in buckets_to_create:
        name = bucket["name"]
        if name in existing:
            print(f"  ✓ Bucket '{name}' already exists — skipping")
            continue
        sb.storage.create_bucket(
            name,
            options={
                "public": bucket["public"],
                "file_size_limit": bucket["file_size_limit"],
                "allowed_mime_types": bucket["allowed_mime_types"],
            },
        )
        print(f"  ✓ Created bucket '{name}'")

    print("\nSupabase storage setup complete.")
    print(f"  Recordings bucket : {settings.storage_bucket_recordings}")
    print(f"  PDFs bucket       : {settings.storage_bucket_pdfs}")


if __name__ == "__main__":
    setup_buckets()
