from functools import cached_property

from pydantic import UUID4

from mealie.routes._base import HouseholdContextController, controller
from mealie.routes._base.permissions import Perm, require
from mealie.routes._base.routers import UserAPIRouter
from mealie.routes.households._membership_errors import membership_errors
from mealie.schema.household.household_member_invitation import (
    CreateHouseholdMemberInvitation,
    ReadHouseholdMemberInvitation,
)
from mealie.schema.response.responses import SuccessResponse
from mealie.services.household_services.household_membership_service import HouseholdMembershipService

router = UserAPIRouter(prefix="/households", tags=["Households: Members"])


@controller(router)
class HouseholdMembersController(HouseholdContextController):
    @cached_property
    def service(self) -> HouseholdMembershipService:
        return HouseholdMembershipService(self.repos, self.group_id)

    @router.get(
        "/member-invitations",
        response_model=list[ReadHouseholdMemberInvitation],
        dependencies=[require(Perm.HOUSEHOLD_MANAGE)],
    )
    def get_member_invitations(self):
        """Pending invitations of existing users to join the household"""
        return self.service.list_for_household(self.household_id)

    @router.post(
        "/member-invitations",
        response_model=ReadHouseholdMemberInvitation,
        status_code=201,
        dependencies=[require(Perm.HOUSEHOLD_MANAGE)],
    )
    def invite_member(self, body: CreateHouseholdMemberInvitation):
        """Invite an existing user of the same group to join the household"""
        with membership_errors(self.translator):
            return self.service.invite(self.household_id, body.email, self.user)

    @router.delete(
        "/member-invitations/{invitation_id}",
        response_model=ReadHouseholdMemberInvitation,
        dependencies=[require(Perm.HOUSEHOLD_MANAGE)],
    )
    def revoke_member_invitation(self, invitation_id: UUID4):
        with membership_errors(self.translator):
            return self.service.revoke(self.household_id, invitation_id)

    @router.delete("/members/{user_id}", response_model=SuccessResponse, dependencies=[require(Perm.HOUSEHOLD_MANAGE)])
    def remove_member(self, user_id: UUID4):
        """Remove a user from the household. Users cannot be removed from their primary household."""
        with membership_errors(self.translator):
            self.service.remove_member(self.household_id, user_id)
        return SuccessResponse.respond()
