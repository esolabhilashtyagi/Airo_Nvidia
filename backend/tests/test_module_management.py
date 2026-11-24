import pytest
import uuid
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_module_draft_lesson_and_publish_workflow(async_client: AsyncClient, candidate_headers: dict, admin_headers: dict):
    denied = await async_client.get("/api/v1/modules/manage", headers=candidate_headers)
    assert denied.status_code == 403
    candidate_profile = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    industry_id = candidate_profile["industry_id"]
    created = await async_client.post("/api/v1/modules/manage", headers=admin_headers, json={
        "industry_id": industry_id, "title": "Admin workflow test module", "description": "Test module workflow content.",
    })
    assert created.status_code == 201
    module = created.json()["data"]
    assert module["is_published"] is False

    invalid_publish = await async_client.patch(f"/api/v1/modules/manage/{module['id']}", headers=admin_headers, json={"is_published": True})
    assert invalid_publish.status_code == 422
    lesson = await async_client.post(f"/api/v1/modules/manage/{module['id']}/lessons", headers=admin_headers, json={
        "title": "Persisted lesson", "content": "Lesson contents persist through the database API.",
    })
    assert lesson.status_code == 201
    assert lesson.json()["data"]["title"] == "Persisted lesson"

    published = await async_client.patch(f"/api/v1/modules/manage/{module['id']}", headers=admin_headers, json={"is_published": True})
    assert published.status_code == 200
    assert published.json()["data"]["is_published"] is True
    assert len(published.json()["data"]["lessons"]) == 1
    deleted = await async_client.delete(f"/api/v1/modules/manage/{module['id']}", headers=candidate_headers)
    assert deleted.status_code == 403
    enrolled = await async_client.post(f"/api/v1/modules/{module['id']}/enroll", headers=candidate_headers)
    assert enrolled.status_code == 200
    archived = await async_client.delete(f"/api/v1/modules/manage/{module['id']}", headers=admin_headers)
    assert archived.status_code == 200
    assert archived.json()["data"]["is_archived"] is True
    assert (await async_client.get(f"/api/v1/modules/{module['id']}", headers=candidate_headers)).status_code == 404
    managed = await async_client.get("/api/v1/modules/manage", headers=admin_headers)
    archived_record = next(item for item in managed.json()["data"] if item["id"] == module["id"])
    assert archived_record["is_archived"] is True


@pytest.mark.asyncio
async def test_archived_lesson_history_does_not_inflate_active_module_completion(
    async_client: AsyncClient, candidate_headers: dict, admin_headers: dict,
):
    profile = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    module_result = await async_client.post("/api/v1/modules/manage", headers=admin_headers, json={
        "industry_id": profile["industry_id"], "title": f"Archive history {uuid.uuid4()}",
        "description": "Check active lessons against retained completion history.",
    })
    assert module_result.status_code == 201, module_result.text
    module_id = module_result.json()["data"]["id"]
    lessons = []
    for index in range(1, 3):
        created = await async_client.post(f"/api/v1/modules/manage/{module_id}/lessons", headers=admin_headers, json={
            "title": f"Active lesson {index}", "content": f"Persisted lesson content {index}.", "order_index": index,
        })
        assert created.status_code == 201, created.text
        lessons.append(created.json()["data"])
    assert (await async_client.patch(f"/api/v1/modules/manage/{module_id}", headers=admin_headers,
        json={"is_published": True})).status_code == 200
    assert (await async_client.post(f"/api/v1/modules/{module_id}/enroll", headers=candidate_headers)).status_code == 200

    first_completion = await async_client.post(
        f"/api/v1/modules/{module_id}/lessons/{lessons[0]['id']}/complete", headers=candidate_headers,
    )
    assert first_completion.status_code == 200
    assert first_completion.json()["data"]["completion_percentage"] == 50

    archived = await async_client.delete(
        f"/api/v1/modules/manage/{module_id}/lessons/{lessons[0]['id']}", headers=admin_headers,
    )
    assert archived.status_code == 200
    third = await async_client.post(f"/api/v1/modules/manage/{module_id}/lessons", headers=admin_headers, json={
        "title": "Replacement active lesson", "content": "Progress should count active lessons only.", "order_index": 3,
    })
    assert third.status_code == 201, third.text
    assert (await async_client.patch(f"/api/v1/modules/manage/{module_id}", headers=admin_headers,
        json={"is_published": True})).status_code == 200
    final = await async_client.post(
        f"/api/v1/modules/{module_id}/lessons/{third.json()['data']['id']}/complete", headers=candidate_headers,
    )
    assert final.status_code == 200
    result = final.json()["data"]
    assert result["completion_percentage"] == 50
    assert str(lessons[0]["id"]) in result["completed_lesson_ids"]
    assert all(lesson["id"] != lessons[0]["id"] for lesson in result["lessons"])

    second_email = f"module-isolation-{uuid.uuid4()}@example.com"
    second_password = "SecureModuleIsolation123!"
    registration = await async_client.post("/api/v1/auth/register", json={
        "email": second_email, "password": second_password, "full_name": "Module Isolation Test",
    })
    assert registration.status_code == 201
    second_login = await async_client.post("/api/v1/auth/login", json={"email": second_email, "password": second_password})
    second_headers = {"Authorization": f"Bearer {second_login.json()['data']['access_token']}"}
    other_candidate_detail = await async_client.get(f"/api/v1/modules/{module_id}", headers=second_headers)
    assert other_candidate_detail.status_code == 200
    assert other_candidate_detail.json()["data"]["progress_status"] == "not_started"
    assert other_candidate_detail.json()["data"]["completed_lesson_ids"] == []

    unpublished = await async_client.patch(f"/api/v1/modules/manage/{module_id}", headers=admin_headers,
        json={"is_published": False})
    assert unpublished.status_code == 200
    assert (await async_client.get(f"/api/v1/modules/{module_id}", headers=candidate_headers)).status_code == 404


@pytest.mark.asyncio
async def test_module_role_skill_links_and_lesson_edit_order_persist(
    async_client: AsyncClient, candidate_headers: dict, admin_headers: dict,
):
    profile = (await async_client.get("/api/v1/candidates/profile", headers=candidate_headers)).json()["data"]
    taxonomy = (await async_client.get(
        f"/api/v1/question-taxonomy?industry_id={profile['industry_id']}", headers=candidate_headers,
    )).json()["data"]
    assert taxonomy["job_roles"]
    if not taxonomy["skills"]:
        created_skill = await async_client.post("/api/v1/question-taxonomy/manage", headers=admin_headers, json={
            "kind": "skill", "name": f"Module relationship skill {uuid.uuid4()}", "category": "test",
        })
        assert created_skill.status_code == 201, created_skill.text
        skill_id = created_skill.json()["data"]["id"]
    else:
        skill_id = taxonomy["skills"][0]["id"]
    role_id = taxonomy["job_roles"][0]["id"]

    created = await async_client.post("/api/v1/modules/manage", headers=admin_headers, json={
        "industry_id": profile["industry_id"], "title": f"Linked module {uuid.uuid4()}",
        "description": "Persist role, skill, lesson editing and sequence changes.",
        "job_role_ids": [role_id], "skill_ids": [skill_id],
    })
    assert created.status_code == 201, created.text
    module = created.json()["data"]
    assert module["job_role_ids"] == [role_id]
    assert module["skill_ids"] == [skill_id]

    lessons = []
    for index in (1, 2):
        result = await async_client.post(f"/api/v1/modules/manage/{module['id']}/lessons", headers=admin_headers, json={
            "title": f"Sequence lesson {index}", "content": f"Original content {index}.", "order_index": index,
        })
        assert result.status_code == 201, result.text
        lessons.append(result.json()["data"])
    edited = await async_client.patch(
        f"/api/v1/modules/manage/{module['id']}/lessons/{lessons[0]['id']}", headers=admin_headers, json={
            "title": "Edited first lesson", "content": "Updated lesson content persists.", "order_index": 2,
        },
    )
    assert edited.status_code == 200, edited.text
    reordered = await async_client.patch(
        f"/api/v1/modules/manage/{module['id']}/lessons/{lessons[1]['id']}", headers=admin_headers, json={
            "title": lessons[1]["title"], "content": lessons[1]["content"], "order_index": 1,
        },
    )
    assert reordered.status_code == 200, reordered.text
    managed = await async_client.get("/api/v1/modules/manage", headers=admin_headers)
    persisted = next(item for item in managed.json()["data"] if item["id"] == module["id"])
    ordered_lessons = sorted(persisted["lessons"], key=lambda lesson: lesson["order_index"])
    assert [lesson["title"] for lesson in ordered_lessons] == ["Sequence lesson 2", "Edited first lesson"]
    assert ordered_lessons[1]["content"] == "Updated lesson content persists."
