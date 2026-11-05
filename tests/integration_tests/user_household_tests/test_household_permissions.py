from uuid import uuid4

from fastapi.testclient import TestClient

from tests.utils import api_routes
from tests.utils.factories import random_bool
from tests.utils.fixture_schemas import TestUser


def get_permissions_payload(user_id: str, can_manage=None, can_manage_household=None) -> dict:
    return {
        "user_id": user_id,
        "can_manage": random_bool() if can_manage is None else can_manage,
        "can_manage_household": random_bool(),
        "can_invite": random_bool(),
        "can_organize": random_bool(),
    }


def test_set_member_permissions(api_client: TestClient, user_tuple: list[TestUser]):
    usr_1, usr_2 = user_tuple

    # Set Acting User
    acting_user = usr_1.repos.users.get_one(usr_1.user_id)
    assert acting_user
    acting_user.can_manage = True
    usr_1.repos.users.update(acting_user.id, acting_user)

    payload = get_permissions_payload(str(usr_2.user_id))

    # Test
    response = api_client.put(api_routes.households_permissions, json=payload, headers=usr_1.token)
    assert response.status_code == 200


def test_set_member_permissions_other_household(
    api_client: TestClient,
    unique_user: TestUser,
    h2_user: TestUser,
):
    database = unique_user.repos

    user = database.users.get_one(unique_user.user_id)
    assert user
    user.can_manage = True
    database.users.update(user.id, user)

    payload = get_permissions_payload(str(h2_user.user_id))
    response = api_client.put(api_routes.households_permissions, json=payload, headers=unique_user.token)
    assert response.status_code == 403


def test_set_member_permissions_no_user(
    api_client: TestClient,
    unique_user: TestUser,
):
    database = unique_user.repos

    user = database.users.get_one(unique_user.user_id)
    assert user
    user.can_manage = True
    database.users.update(user.id, user)

    payload = get_permissions_payload(str(uuid4()))
    response = api_client.put(api_routes.households_permissions, json=payload, headers=unique_user.token)
    assert response.status_code == 404


def test_set_own_permissions(api_client: TestClient, unique_user: TestUser):
    database = unique_user.repos

    user = database.users.get_one(unique_user.user_id)
    assert user
    user.can_manage = True
    database.users.update(user.id, user)

    form = {"user_id": str(unique_user.user_id), "canOrganize": not user.can_organize}
    response = api_client.put(api_routes.households_permissions, json=form, headers=unique_user.token)
    assert response.status_code == 403


def _membership_flags(api_client: TestClient, user: TestUser) -> dict[str, bool]:
    data = api_client.get(api_routes.users_self, headers=user.token).json()
    return {h["householdId"]: h["canManageHousehold"] for h in data["households"]}


def test_set_permissions_of_non_primary_member(
    api_client: TestClient, multi_household_user: TestUser, h2_user: TestUser
):
    # h2_user acts as manager of their own household
    acting_user = h2_user.repos.users.get_one(h2_user.user_id)
    assert acting_user
    acting_user.can_manage = True
    h2_user.repos.users.update(acting_user.id, acting_user)

    before = api_client.get(api_routes.users_self, headers=multi_household_user.token).json()
    flags_before = _membership_flags(api_client, multi_household_user)
    assert flags_before[h2_user.household_id] is False

    payload = {
        "user_id": str(multi_household_user.user_id),
        "can_manage_household": True,
        "can_manage": True,
        "can_invite": True,
        "can_organize": True,
    }
    response = api_client.put(api_routes.households_permissions, json=payload, headers=h2_user.token)
    assert response.status_code == 200

    # only the permission this household grants changed; the user's other households and group flags did not
    flags_after = _membership_flags(api_client, multi_household_user)
    assert flags_after[h2_user.household_id] is True
    assert flags_after[multi_household_user.household_id] == flags_before[multi_household_user.household_id]

    after = api_client.get(api_routes.users_self, headers=multi_household_user.token).json()
    for flag in ("canManage", "canInvite", "canOrganize"):
        assert after[flag] == before[flag]
