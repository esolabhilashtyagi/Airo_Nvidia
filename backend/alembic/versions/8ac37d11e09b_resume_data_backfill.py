"""Backfill resume metadata and quarantine unverified legacy analyses.

Revision ID: 8ac37d11e09b
Revises: 2b8ce1a40f57
"""
from alembic import op

revision = "8ac37d11e09b"
down_revision = "2b8ce1a40f57"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Preserve prior parser output as the immutable uploaded baseline.
    op.execute("UPDATE resumes SET original_parsed_data = parsed_data WHERE original_parsed_data = '{}'::jsonb")
    op.execute("""
        UPDATE resumes
        SET parsing_status = 'extracted'
        WHERE parsing_status = 'completed' AND raw_text IS NOT NULL AND length(trim(raw_text)) > 0
    """)
    op.execute("""
        UPDATE resumes
        SET parsing_status = 'extraction_failed'
        WHERE parsing_status = 'completed' AND (raw_text IS NULL OR length(trim(raw_text)) = 0)
    """)
    # Previous code emitted deterministic sample scores when AI was unavailable.
    # Retain rows for audit, but prevent them being presented as validated results.
    op.execute("""
        UPDATE resume_analyses SET status = 'analysis_failed', analysis_provider = 'legacy_unverified'
        WHERE analysis_provider IS NULL
    """)
    op.execute("""
        UPDATE resumes SET analysis_status = 'analysis_failed',
          analysis_error = 'Existing analysis requires regeneration with a configured AI provider.'
        WHERE EXISTS (
          SELECT 1 FROM resume_analyses a
          WHERE a.resume_id = resumes.id AND a.analysis_provider = 'legacy_unverified'
        )
    """)


def downgrade() -> None:
    # Deliberately preserve the quarantine: restoring an unverified score as completed is unsafe.
    pass
