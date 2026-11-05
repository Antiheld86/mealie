from pydantic import UUID4

from mealie.repos.all_repositories import get_repositories
from mealie.repos.repository_factory import AllRepositories
from mealie.schema.household.household_member_invitation import (
    ReadHouseholdMemberInvitation,
    SaveHouseholdMemberInvitation,
)
from mealie.schema.user.user import PrivateUser
from mealie.services._base_service import BaseService


class MembershipNotFoundError(Exception):
    """The invitation, user or household doesn't exist, or isn't visible to the caller"""


class InvalidMembershipChangeError(Exception):
    """The change isn't allowed, e.g. inviting an existing member or removing someone from their primary household"""


class HouseholdMembershipService(BaseService):
    """
    Manages who belongs to a household besides the users whose primary household it is.
    A manager invites an existing user of the same group; the invitee accepts or declines.
    """

    def __init__(self, repos: AllRepositories, group_id: UUID4):
        super().__init__()
        # invitations are looked up by household and by invitee, so these repos only scope to the group
        self.repos = get_repositories(repos.session, group_id=group_id, household_id=None)
        self.group_id = group_id

    def _get_user(self, user_id: UUID4) -> PrivateUser:
        user = self.repos.users.get_one(user_id)
        if user is None:
            raise MembershipNotFoundError("user")
        return user

    def _is_member(self, user: PrivateUser, household_id: UUID4) -> bool:
        return any(membership.household_id == household_id for membership in user.households)

    def invite(self, household_id: UUID4, email: str, invited_by: PrivateUser) -> ReadHouseholdMemberInvitation:
        if self.repos.households.get_one(household_id) is None:
            raise MembershipNotFoundError("household")

        invitee = self.repos.users.get_one(email.strip().lower(), "email")
        if invitee is None:
            raise MembershipNotFoundError("user")

        if self._is_member(invitee, household_id):
            raise InvalidMembershipChangeError("already a member")

        existing = self.repos.household_member_invitations.find(household_id, invitee.id)
        if existing:
            return existing

        return self.repos.household_member_invitations.create(
            SaveHouseholdMemberInvitation(household_id=household_id, user_id=invitee.id, invited_by_id=invited_by.id)
        )

    def list_for_household(self, household_id: UUID4) -> list[ReadHouseholdMemberInvitation]:
        return self.repos.household_member_invitations.by_household(household_id)

    def list_for_user(self, user_id: UUID4) -> list[ReadHouseholdMemberInvitation]:
        return self.repos.household_member_invitations.by_user(user_id)

    def revoke(self, household_id: UUID4, invitation_id: UUID4) -> ReadHouseholdMemberInvitation:
        invitation = self.repos.household_member_invitations.get_one(invitation_id)
        if invitation is None or invitation.household_id != household_id:
            raise MembershipNotFoundError("invitation")
        return self.repos.household_member_invitations.delete(invitation_id)

    def _get_own_invitation(self, user_id: UUID4, invitation_id: UUID4) -> ReadHouseholdMemberInvitation:
        invitation = self.repos.household_member_invitations.get_one(invitation_id)
        if invitation is None or invitation.user_id != user_id:
            raise MembershipNotFoundError("invitation")
        return invitation

    def accept(self, user_id: UUID4, invitation_id: UUID4) -> ReadHouseholdMemberInvitation:
        invitation = self._get_own_invitation(user_id, invitation_id)
        self.repos.users.add_household_membership(user_id, invitation.household_id)
        self.repos.household_member_invitations.delete(invitation_id)
        return invitation

    def decline(self, user_id: UUID4, invitation_id: UUID4) -> ReadHouseholdMemberInvitation:
        self._get_own_invitation(user_id, invitation_id)
        return self.repos.household_member_invitations.delete(invitation_id)

    def remove_member(self, household_id: UUID4, user_id: UUID4) -> None:
        """Remove a user from a household. Also used when a user leaves on their own."""
        user = self._get_user(user_id)
        if user.household_id == household_id:
            raise InvalidMembershipChangeError("cannot leave the primary household")
        if not self._is_member(user, household_id):
            raise MembershipNotFoundError("membership")

        self.repos.users.remove_household_membership(user_id, household_id)
