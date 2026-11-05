from datetime import UTC, datetime

from fastapi.testclient import TestClient

from tests.utils import api_routes
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


def test_user_lists_every_household(api_client: TestClient, multi_household_user: TestUser, h2_user: TestUser):
    response = api_client.get(api_routes.users_self, headers=multi_household_user.token)
    assert response.status_code == 200
    data = response.json()

    households = {h["householdId"]: h for h in data["households"]}
    assert set(households) == {multi_household_user.household_id, h2_user.household_id}
    assert households[multi_household_user.household_id]["isPrimary"] is True
    assert households[h2_user.household_id]["isPrimary"] is False
    assert data["householdId"] == multi_household_user.household_id


def test_mealplan_defaults_to_primary_household(api_client: TestClient, multi_household_user: TestUser):
    response = api_client.post(
        api_routes.households_mealplans,
        json={"date": _today(), "entryType": "dinner", "title": random_string()},
        headers=multi_household_user.token,
    )
    assert response.status_code == 201
    assert response.json()["householdId"] == multi_household_user.household_id


def test_mealplan_can_be_created_in_another_member_household(
    api_client: TestClient, multi_household_user: TestUser, h2_user: TestUser
):
    title = random_string()
    response = api_client.post(
        api_routes.households_mealplans,
        json={"date": _today(), "entryType": "dinner", "title": title, "householdId": h2_user.household_id},
        headers=multi_household_user.token,
    )
    assert response.status_code == 201
    entry = response.json()
    assert entry["householdId"] == h2_user.household_id

    # it is visible to the creator and to the other household's members
    for user in (multi_household_user, h2_user):
        response = api_client.get(api_routes.households_mealplans_item_id(entry["id"]), headers=user.token)
        assert response.status_code == 200

    # the creator sees entries of all their households together
    response = api_client.get(
        api_routes.households_mealplans, params={"perPage": -1}, headers=multi_household_user.token
    )
    assert entry["id"] in [e["id"] for e in response.json()["items"]]


def test_mealplan_in_non_member_household_is_forbidden(
    api_client: TestClient, unique_user: TestUser, h2_user: TestUser
):
    response = api_client.post(
        api_routes.households_mealplans,
        json={"date": _today(), "entryType": "dinner", "title": random_string(), "householdId": h2_user.household_id},
        headers=unique_user.token,
    )
    assert response.status_code == 403


def test_mealplans_of_other_households_are_hidden(api_client: TestClient, unique_user: TestUser, h2_user: TestUser):
    response = api_client.post(
        api_routes.households_mealplans,
        json={"date": _today(), "entryType": "dinner", "title": random_string()},
        headers=unique_user.token,
    )
    assert response.status_code == 201
    entry = response.json()

    response = api_client.get(api_routes.households_mealplans_item_id(entry["id"]), headers=h2_user.token)
    assert response.status_code == 404


def test_mealplan_can_move_between_member_households(
    api_client: TestClient, multi_household_user: TestUser, h2_user: TestUser
):
    response = api_client.post(
        api_routes.households_mealplans,
        json={"date": _today(), "entryType": "dinner", "title": random_string()},
        headers=multi_household_user.token,
    )
    entry = response.json()

    entry["householdId"] = h2_user.household_id
    response = api_client.put(
        api_routes.households_mealplans_item_id(entry["id"]), json=entry, headers=multi_household_user.token
    )
    assert response.status_code == 200
    assert response.json()["householdId"] == h2_user.household_id


def test_mealplan_cannot_move_to_non_member_household(api_client: TestClient, unique_user: TestUser, h2_user: TestUser):
    response = api_client.post(
        api_routes.households_mealplans,
        json={"date": _today(), "entryType": "dinner", "title": random_string()},
        headers=unique_user.token,
    )
    entry = response.json()

    entry["householdId"] = h2_user.household_id
    response = api_client.put(
        api_routes.households_mealplans_item_id(entry["id"]), json=entry, headers=unique_user.token
    )
    assert response.status_code == 403


def test_shopping_list_can_be_created_in_another_member_household(
    api_client: TestClient, multi_household_user: TestUser, h2_user: TestUser
):
    response = api_client.post(
        api_routes.households_shopping_lists,
        json={"name": random_string(), "householdId": h2_user.household_id},
        headers=multi_household_user.token,
    )
    assert response.status_code == 201
    shopping_list = response.json()
    assert shopping_list["householdId"] == h2_user.household_id

    # members of that household can use it, and the creator sees it alongside lists of their primary household
    response = api_client.get(api_routes.households_shopping_lists_item_id(shopping_list["id"]), headers=h2_user.token)
    assert response.status_code == 200

    response = api_client.get(
        api_routes.households_shopping_lists, params={"perPage": -1}, headers=multi_household_user.token
    )
    assert shopping_list["id"] in [x["id"] for x in response.json()["items"]]


def test_shopping_list_in_non_member_household_is_forbidden(
    api_client: TestClient, unique_user: TestUser, h2_user: TestUser
):
    response = api_client.post(
        api_routes.households_shopping_lists,
        json={"name": random_string(), "householdId": h2_user.household_id},
        headers=unique_user.token,
    )
    assert response.status_code == 403


def test_shopping_lists_of_other_households_are_hidden(
    api_client: TestClient, unique_user: TestUser, h2_user: TestUser
):
    response = api_client.post(
        api_routes.households_shopping_lists, json={"name": random_string()}, headers=unique_user.token
    )
    assert response.status_code == 201

    response = api_client.get(
        api_routes.households_shopping_lists_item_id(response.json()["id"]), headers=h2_user.token
    )
    assert response.status_code == 404


def test_shopping_list_owner_must_be_member_of_target_household(
    api_client: TestClient, multi_household_user: TestUser, h2_user: TestUser
):
    response = api_client.post(
        api_routes.households_shopping_lists, json={"name": random_string()}, headers=multi_household_user.token
    )
    shopping_list = response.json()

    # moving the list to the other household while the owner is a member of it is fine
    shopping_list["householdId"] = h2_user.household_id
    response = api_client.put(
        api_routes.households_shopping_lists_item_id(shopping_list["id"]),
        json=shopping_list,
        headers=multi_household_user.token,
    )
    assert response.status_code == 200
    assert response.json()["householdId"] == h2_user.household_id

    # an owner from a household the list isn't in is rejected
    shopping_list["userId"] = str(h2_user.user_id)
    shopping_list["householdId"] = multi_household_user.household_id
    response = api_client.put(
        api_routes.households_shopping_lists_item_id(shopping_list["id"]),
        json=shopping_list,
        headers=multi_household_user.token,
    )
    assert response.status_code == 400
