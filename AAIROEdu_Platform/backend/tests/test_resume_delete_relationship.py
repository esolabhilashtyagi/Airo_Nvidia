from app.models.resume import Resume, ResumeATSReview


def test_resume_delete_uses_database_cascade_for_ats_history_without_loading_collection():
    relationship = Resume.ats_reviews.property
    assert relationship.passive_deletes is True
    assert any(
        foreign_key.ondelete == "CASCADE"
        for foreign_key in ResumeATSReview.__table__.c.resume_id.foreign_keys
    )
