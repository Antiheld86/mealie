from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from mealie.db.models.household import HouseholdMembership
from tests.utils import api_routes
from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser


def _memberships(api_client: TestClient, user: TestUser) -> dict[str, dict]:
    data = api_client.get(api_routes.users_self, headers=user.token).json()
    return {h["householdId"]: h for h in data["households"]}


def _set_manager(session: Session, user: TestUser, household_id: str, value: bool) -> None:
    membership = session.execute(
        select(HouseholdMembership).where(
            HouseholdMembership.user_id == UUID(str(user.user_id)),
            HouseholdMembership.household_id == UUID(str(household_id)),
        )
    ).scalar_one()
    membership.can_manage_household = value
    session.commit()


@pytest.fixture
def h2_manager(session: Session, h2_user: TestUser) -> Generator[TestUser]:
    """`h2_user`, who manages their own household, and a clean slate of extra memberships for `unique_user`"""
    _set_manager(session, h2_user, h2_user.household_id, True)
    yield h2_user
    session.execute(
        delete(HouseholdMembership).where(
            HouseholdMembership.household_id == UUID(str(h2_user.household_id)),
            HouseholdMembership.user_id != UUID(str(h2_user.user_id)),
        )
    )
    session.commit()


def _invite(api_client: TestClient, manager: TestUser, invitee: TestUser):
    return api_client.post(
        api_routes.households_member_invitations, json={"email": invitee.email}, headers=manager.token
    )


def test_invite_accept_makes_user_a_member(api_client: TestClient, h2_manager: TestUser, unique_user: TestUser):
    response = _invite(api_client, h2_manager, unique_user)
    assert response.status_code == 201
    invitation = response.json()
    assert invitation["householdId"] == h2_manager.household_id

    pending = api_client.get(api_routes.users_self_household_invitations, headers=unique_user.token).json()
    assert [i["id"] for i in pending] == [invitation["id"]]

    response = api_client.post(
        api_routes.users_self_household_invitations_invitation_id_accept(invitation["id"]), headers=unique_user.token
    )
    assert response.status_code == 200

    memberships = _memberships(api_client, unique_user)
    assert set(memberships) == {unique_user.household_id, h2_manager.household_id}
    assert memberships[h2_manager.household_id]["canManageHousehold"] is False
    assert memberships[h2_manager.household_id]["isPrimary"] is False
    assert api_client.get(api_routes.users_self_household_invitations, headers=unique_user.token).json() == []


def test_declined_invitation_adds_nothing(api_client: TestClient, h2_manager: TestUser, unique_user: TestUser):
    invitation = _invite(api_client, h2_manager, unique_user).json()

    response = api_client.post(
        api_routes.users_self_household_invitations_invitation_id_decline(invitation["id"]), headers=unique_user.token
    )
    assert response.status_code == 200
    assert set(_memberships(api_client, unique_user)) == {unique_user.household_id}

    # a declined invitation cannot be accepted afterwards
    response = api_client.post(
        api_routes.users_self_household_invitations_invitation_id_accept(invitation["id"]), headers=unique_user.token
    )
    assert response.status_code == 404


def test_revoked_invitation_cannot_be_accepted(api_client: TestClient, h2_manager: TestUser, unique_user: TestUser):
    invitation = _invite(api_client, h2_manager, unique_user).json()

    assert (
        api_client.get(api_routes.households_member_invitations, headers=h2_manager.token).json()[0]["id"]
        == invitation["id"]
    )
    assert (
        api_client.delete(
            api_routes.households_member_invitations_invitation_id(invitation["id"]), headers=h2_manager.token
        ).status_code
        == 200
    )

    response = api_client.post(
        api_routes.users_self_household_invitations_invitation_id_accept(invitation["id"]), headers=unique_user.token
    )
    assert response.status_code == 404


def test_only_the_invitee_can_answer_an_invitation(
    api_client: TestClient, h2_manager: TestUser, unique_user: TestUser, g2_user: TestUser
):
    invitation = _invite(api_client, h2_manager, unique_user).json()

    for answer in ("accept", "decline"):
        response = api_client.post(
            getattr(api_routes, f"users_self_household_invitations_invitation_id_{answer}")(invitation["id"]),
            headers=g2_user.token,
        )
        assert response.status_code == 404


def test_invitation_needs_household_manager(
    api_client: TestClient, session: Session, h2_manager: TestUser, unique_user: TestUser
):
    _set_manager(session, h2_manager, h2_manager.household_id, False)
    assert _invite(api_client, h2_manager, unique_user).status_code == 403


def test_cannot_invite_user_from_another_group(api_client: TestClient, h2_manager: TestUser, g2_user: TestUser):
    assert _invite(api_client, h2_manager, g2_user).status_code == 404


def test_cannot_invite_existing_member(api_client: TestClient, h2_manager: TestUser):
    # h2_manager is a member of their own household already
    response = api_client.post(
        api_routes.households_member_invitations, json={"email": h2_manager.email}, headers=h2_manager.token
    )
    assert response.status_code == 400


def test_cannot_invite_unknown_user(api_client: TestClient, h2_manager: TestUser):
    response = api_client.post(
        api_routes.households_member_invitations,
        json={"email": f"{random_string()}@example.com"},
        headers=h2_manager.token,
    )
    assert response.status_code == 404


def test_manager_can_remove_member(api_client: TestClient, h2_manager: TestUser, unique_user: TestUser):
    invitation = _invite(api_client, h2_manager, unique_user).json()
    api_client.post(
        api_routes.users_self_household_invitations_invitation_id_accept(invitation["id"]), headers=unique_user.token
    )

    response = api_client.delete(api_routes.households_members_user_id(unique_user.user_id), headers=h2_manager.token)
    assert response.status_code == 200
    assert set(_memberships(api_client, unique_user)) == {unique_user.household_id}


def test_cannot_remove_member_from_their_primary_household(api_client: TestClient, h2_manager: TestUser):
    response = api_client.delete(api_routes.households_members_user_id(h2_manager.user_id), headers=h2_manager.token)
    assert response.status_code == 400


def test_member_can_leave_and_keeps_primary(api_client: TestClient, h2_manager: TestUser, unique_user: TestUser):
    invitation = _invite(api_client, h2_manager, unique_user).json()
    api_client.post(
        api_routes.users_self_household_invitations_invitation_id_accept(invitation["id"]), headers=unique_user.token
    )

    response = api_client.post(
        api_routes.users_self_households_household_id_leave(h2_manager.household_id), headers=unique_user.token
    )
    assert response.status_code == 200
    assert set(_memberships(api_client, unique_user)) == {unique_user.household_id}


def test_cannot_leave_primary_household(api_client: TestClient, unique_user: TestUser):
    response = api_client.post(
        api_routes.users_self_households_household_id_leave(unique_user.household_id), headers=unique_user.token
    )
    assert response.status_code == 400


def test_leaving_hands_shopping_lists_to_another_member(
    api_client: TestClient, h2_manager: TestUser, unique_user: TestUser
):
    invitation = _invite(api_client, h2_manager, unique_user).json()
    api_client.post(
        api_routes.users_self_household_invitations_invitation_id_accept(invitation["id"]), headers=unique_user.token
    )

    response = api_client.post(
        api_routes.households_shopping_lists,
        json={"name": random_string(), "householdId": h2_manager.household_id},
        headers=unique_user.token,
    )
    assert response.status_code == 201
    shopping_list = response.json()
    assert shopping_list["userId"] == str(unique_user.user_id)

    api_client.post(
        api_routes.users_self_households_household_id_leave(h2_manager.household_id), headers=unique_user.token
    )

    response = api_client.get(
        api_routes.households_shopping_lists_item_id(shopping_list["id"]), headers=h2_manager.token
    )
    assert response.status_code == 200
    assert response.json()["userId"] == str(h2_manager.user_id)
