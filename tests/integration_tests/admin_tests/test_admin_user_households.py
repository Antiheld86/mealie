from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from mealie.db.models.household import HouseholdMembership
from tests.utils import api_routes
from tests.utils.fixture_schemas import TestUser


def _route(user: TestUser) -> str:
    return api_routes.admin_users_item_id_households(user.user_id)


def _payload(primary: str, **households: bool) -> dict:
    return {
        "primaryHouseholdId": primary,
        "households": [{"householdId": hid, "canManageHousehold": flag} for hid, flag in households.items()],
    }


@pytest.fixture
def clean_memberships(session: Session, unique_user: TestUser, h2_user: TestUser) -> Generator[None]:
    """Leave `unique_user` with only their primary household, whatever a test did"""
    yield
    session.execute(
        delete(HouseholdMembership).where(
            HouseholdMembership.user_id == UUID(str(unique_user.user_id)),
            HouseholdMembership.household_id != UUID(str(unique_user.household_id)),
        )
    )
    session.commit()


def test_admin_lists_user_households(api_client: TestClient, admin_token, unique_user: TestUser):
    response = api_client.get(_route(unique_user), headers=admin_token)
    assert response.status_code == 200
    households = response.json()
    assert [h["householdId"] for h in households] == [unique_user.household_id]
    assert households[0]["isPrimary"] is True


@pytest.mark.usefixtures("clean_memberships")
def test_admin_sets_user_households(api_client: TestClient, admin_token, unique_user: TestUser, h2_user: TestUser):
    body = _payload(unique_user.household_id, **{unique_user.household_id: False, h2_user.household_id: True})
    response = api_client.put(_route(unique_user), json=body, headers=admin_token)
    assert response.status_code == 200

    by_id = {h["householdId"]: h for h in response.json()}
    assert set(by_id) == {unique_user.household_id, h2_user.household_id}
    assert by_id[h2_user.household_id]["canManageHousehold"] is True
    assert by_id[h2_user.household_id]["isPrimary"] is False

    # and the user sees it
    own = api_client.get(api_routes.users_self, headers=unique_user.token).json()
    assert {h["householdId"] for h in own["households"]} == set(by_id)

    # leaving a household out removes the membership
    body = _payload(unique_user.household_id, **{unique_user.household_id: False})
    response = api_client.put(_route(unique_user), json=body, headers=admin_token)
    assert [h["householdId"] for h in response.json()] == [unique_user.household_id]


@pytest.mark.usefixtures("clean_memberships")
def test_admin_can_change_primary_household(
    api_client: TestClient, admin_token, unique_user: TestUser, h2_user: TestUser
):
    body = _payload(h2_user.household_id, **{h2_user.household_id: False})
    try:
        response = api_client.put(_route(unique_user), json=body, headers=admin_token)
        assert response.status_code == 200
        assert [h["householdId"] for h in response.json()] == [h2_user.household_id]
        assert api_client.get(api_routes.users_self, headers=unique_user.token).json()["householdId"] == (
            h2_user.household_id
        )
    finally:
        restore = _payload(unique_user.household_id, **{unique_user.household_id: False})
        api_client.put(_route(unique_user), json=restore, headers=admin_token)


@pytest.mark.usefixtures("clean_memberships")
def test_primary_household_must_be_listed(
    api_client: TestClient, admin_token, unique_user: TestUser, h2_user: TestUser
):
    body = _payload(unique_user.household_id, **{h2_user.household_id: True})
    assert api_client.put(_route(unique_user), json=body, headers=admin_token).status_code == 400


@pytest.mark.usefixtures("clean_memberships")
def test_households_must_be_in_the_users_group(
    api_client: TestClient, admin_token, unique_user: TestUser, g2_user: TestUser
):
    body = _payload(unique_user.household_id, **{unique_user.household_id: False, g2_user.household_id: False})
    assert api_client.put(_route(unique_user), json=body, headers=admin_token).status_code == 400


def test_only_admins_manage_user_households(api_client: TestClient, unique_user: TestUser, h2_user: TestUser):
    assert api_client.get(_route(unique_user), headers=unique_user.token).status_code == 403
    body = _payload(unique_user.household_id, **{unique_user.household_id: True})
    assert api_client.put(_route(unique_user), json=body, headers=unique_user.token).status_code == 403


@pytest.mark.usefixtures("clean_memberships")
def test_household_with_additional_members_cannot_be_deleted(
    api_client: TestClient, admin_token, unique_user: TestUser
):
    group = api_client.get(api_routes.groups_self, headers=unique_user.token).json()
    response = api_client.post(
        api_routes.admin_households, json={"name": "extra", "groupId": group["id"]}, headers=admin_token
    )
    assert response.status_code == 201
    household_id = response.json()["id"]

    body = _payload(unique_user.household_id, **{unique_user.household_id: False, household_id: False})
    assert api_client.put(_route(unique_user), json=body, headers=admin_token).status_code == 200

    response = api_client.delete(api_routes.admin_households_item_id(household_id), headers=admin_token)
    assert response.status_code == 400

    # once nobody belongs to it any more, it can go
    body = _payload(unique_user.household_id, **{unique_user.household_id: False})
    api_client.put(_route(unique_user), json=body, headers=admin_token)
    assert api_client.delete(api_routes.admin_households_item_id(household_id), headers=admin_token).status_code == 200
