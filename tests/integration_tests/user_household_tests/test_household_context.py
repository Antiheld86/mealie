from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from mealie.db.models.household import HouseholdMembership
from tests.utils import api_routes
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser


def _webhook_payload() -> dict:
    return {"enabled": False, "name": random_string(), "url": "https://example.com/hook", "scheduledTime": "00:00:00"}


def _set_manage_flag(session: Session, user: TestUser, household_id: str, value: bool) -> None:
    membership = session.execute(
        select(HouseholdMembership).where(
            HouseholdMembership.user_id == UUID(str(user.user_id)),
            HouseholdMembership.household_id == UUID(household_id),
        )
    ).scalar_one()
    membership.can_manage_household = value
    session.commit()


def test_household_context_defaults_to_primary(api_client: TestClient, multi_household_user: TestUser):
    response = api_client.post(
        api_routes.households_webhooks, json=_webhook_payload(), headers=multi_household_user.token
    )
    assert response.status_code == 201
    assert response.json()["householdId"] == multi_household_user.household_id


def test_household_context_requires_manage_flag_of_that_household(
    api_client: TestClient, session: Session, multi_household_user: TestUser, h2_user: TestUser
):
    _set_manage_flag(session, multi_household_user, h2_user.household_id, False)

    # managing their primary household does not let them manage another one
    response = api_client.post(
        api_routes.households_webhooks,
        json=_webhook_payload(),
        params={"householdId": h2_user.household_id},
        headers=multi_household_user.token,
    )
    assert response.status_code == 403


def test_household_context_uses_membership_manage_flag(
    api_client: TestClient, session: Session, multi_household_user: TestUser, h2_user: TestUser
):
    _set_manage_flag(session, multi_household_user, h2_user.household_id, True)
    try:
        response = api_client.post(
            api_routes.households_webhooks,
            json=_webhook_payload(),
            params={"householdId": h2_user.household_id},
            headers=multi_household_user.token,
        )
        assert response.status_code == 201
        webhook = response.json()
        assert webhook["householdId"] == h2_user.household_id

        # it lives in the other household, so it is only found when acting on that household
        response = api_client.get(
            api_routes.households_webhooks_item_id(webhook["id"]),
            params={"householdId": h2_user.household_id},
            headers=multi_household_user.token,
        )
        assert response.status_code == 200

        response = api_client.get(
            api_routes.households_webhooks_item_id(webhook["id"]), headers=multi_household_user.token
        )
        assert response.status_code == 404
    finally:
        _set_manage_flag(session, multi_household_user, h2_user.household_id, False)


@pytest.mark.parametrize("route", [api_routes.households_webhooks, api_routes.households_preferences])
def test_household_context_rejects_non_member_household(
    api_client: TestClient, unique_user: TestUser, g2_user: TestUser, route: str
):
    response = api_client.get(route, params={"householdId": g2_user.household_id}, headers=unique_user.token)
    assert response.status_code == 403


def test_cookbook_created_in_selected_household(
    api_client: TestClient, multi_household_user: TestUser, h2_user: TestUser
):
    response = api_client.post(
        api_routes.households_cookbooks,
        json={"name": random_string()},
        params={"householdId": h2_user.household_id},
        headers=multi_household_user.token,
    )
    assert response.status_code == 201
    cookbook = response.json()
    assert cookbook["householdId"] == h2_user.household_id

    response = api_client.delete(
        api_routes.households_cookbooks_item_id(cookbook["id"]),
        params={"householdId": h2_user.household_id},
        headers=multi_household_user.token,
    )
    assert response.status_code == 200


def test_household_members_include_additional_members(
    api_client: TestClient, multi_household_user: TestUser, h2_user: TestUser
):
    acting_user = h2_user.repos.users.get_one(h2_user.user_id)
    assert acting_user
    acting_user.can_manage = True
    h2_user.repos.users.update(acting_user.id, acting_user)

    response = api_client.get(api_routes.households_members, headers=h2_user.token)
    assert response.status_code == 200
    members = {member["id"]: member for member in response.json()["items"]}
    assert set(members) == {str(h2_user.user_id), str(multi_household_user.user_id)}

    # each member says what they may do in each of their households, so the caller can pick this one's
    memberships = {h["householdId"]: h for h in members[str(multi_household_user.user_id)]["households"]}
    assert memberships[h2_user.household_id]["isPrimary"] is False

    # the user's primary household only lists its own members
    response = api_client.get(api_routes.households_members, headers=multi_household_user.token)
    assert str(h2_user.user_id) not in {member["id"] for member in response.json()["items"]}
