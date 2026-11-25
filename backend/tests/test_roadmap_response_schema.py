from uuid import uuid4

from app.schemas.module import RoadmapResponse


def test_roadmap_response_hides_internal_generation_digest():
    response = RoadmapResponse.model_validate({
        "id": uuid4(),
        "candidate_profile_id": uuid4(),
        "title": "Learning roadmap",
        "description": "Profile-based learning steps.\n[generation-context:v1:3af1147df86abbf8775e5ce2d6b2d59bc8fe176e2feec684fb5c23ce40e4ecf4]",
        "status": "active",
        "tasks": [],
    })

    assert response.description == "Profile-based learning steps."
    assert "generation-context" not in response.model_dump_json()
