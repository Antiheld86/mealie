from functools import cached_property

from pydantic import UUID4

from mealie.routes._base import BaseUserController, controller
from mealie.routes._base.routers import UserAPIRouter
from mealie.routes.households._membership_errors import membership_errors
from mealie.schema.household.household_member_invitation import ReadHouseholdMemberInvitation
from mealie.schema.response.responses import SuccessResponse
from mealie.services.household_services.household_membership_service import HouseholdMembershipService

router = UserAPIRouter(prefix="/users/self", tags=["Users: Household Memberships"])


@controller(router)
class UserHouseholdMembershipsController(BaseUserController):
    @cached_property
    def service(self) -> HouseholdMembershipService:
        return HouseholdMembershipService(self.repos, self.group_id)

    @router.get("/household-invitations", response_model=list[ReadHouseholdMemberInvitation])
    def get_my_invitations(self):
        """Pending invitations to join another household"""
        return self.service.list_for_user(self.user.id)

    @router.post("/household-invitations/{invitation_id}/accept", response_model=ReadHouseholdMemberInvitation)
    def accept_invitation(self, invitation_id: UUID4):
        with membership_errors(self.translator):
            return self.service.accept(self.user.id, invitation_id)

    @router.post("/household-invitations/{invitation_id}/decline", response_model=ReadHouseholdMemberInvitation)
    def decline_invitation(self, invitation_id: UUID4):
        with membership_errors(self.translator):
            return self.service.decline(self.user.id, invitation_id)

    @router.post("/households/{household_id}/leave", response_model=SuccessResponse)
    def leave_household(self, household_id: UUID4):
        """Leave a household. Your primary household cannot be left."""
        with membership_errors(self.translator):
            self.service.remove_member(household_id, self.user.id)
        return SuccessResponse.respond()
