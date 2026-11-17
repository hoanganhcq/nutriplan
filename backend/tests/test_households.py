from fastapi.testclient import TestClient

from app.main import app


def test_household_then_members_are_created_separately():
    with TestClient(app) as client:
        session = client.post("/sessions").json()
        headers = {"Authorization": f"Bearer {session['token']}"}

        household = client.post(
            "/households", json={"name": "Gia đình Tách API"}, headers=headers
        )
        assert household.status_code == 201
        household_id = household.json()["household_id"]

        first_member = client.post(
            f"/households/{household_id}/members",
            json={"name": "Thành viên 1", "age": 30},
            headers=headers,
        )
        second_member = client.post(
            f"/households/{household_id}/members",
            json={"name": "Thành viên 2", "age": 28},
            headers=headers,
        )

        assert first_member.status_code == 201
        assert second_member.status_code == 201
        assert first_member.json()["member_id"] != second_member.json()["member_id"]


def test_household_is_not_accessible_from_another_session():
    with TestClient(app) as client:
        owner = client.post("/sessions").json()
        other = client.post("/sessions").json()
        owner_headers = {"Authorization": f"Bearer {owner['token']}"}
        other_headers = {"Authorization": f"Bearer {other['token']}"}
        household = client.post(
            "/households", json={"name": "Riêng tư"}, headers=owner_headers
        )
        household_id = household.json()["household_id"]

        response = client.post(
            f"/households/{household_id}/members",
            json={"name": "Không được phép", "age": 20},
            headers=other_headers,
        )
        assert response.status_code == 404
