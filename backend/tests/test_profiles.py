from fastapi.testclient import TestClient

from app.main import app


def _session(client: TestClient) -> dict[str, str]:
    response = client.post("/sessions")
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_profile_is_owned_by_session():
    with TestClient(app) as client:
        owner_headers = _session(client)
        payload = {
            "household_name": "Gia đình Demo",
            "members": [
                {
                    "name": "Nguyễn An",
                    "age": 25,
                    "sex": "male",
                    "weight_kg": 65,
                    "height_cm": 170,
                    "conditions": ["diabetes"],
                    "allergies": ["peanut"],
                    "energy_target_kcal": 2200,
                    "texture_requirements": "normal",
                }
            ],
        }

        created = client.post("/profiles", json=payload, headers=owner_headers)
        assert created.status_code == 201
        member_id = created.json()["members"][0]["member_id"]

        assert client.get(
            f"/profiles/{member_id}", headers=owner_headers
        ).status_code == 200

        other_headers = _session(client)
        assert client.get(
            f"/profiles/{member_id}", headers=other_headers
        ).status_code == 404


def test_profile_requires_session_and_valid_choices():
    with TestClient(app) as client:
        payload = {
            "household_name": "Invalid",
            "members": [
                {
                    "name": "Test",
                    "age": 25,
                    "conditions": ["unsupported-condition"],
                }
            ],
        }
        assert client.post("/profiles", json=payload).status_code == 401

        headers = _session(client)
        assert client.post(
            "/profiles", json=payload, headers=headers
        ).status_code == 422
