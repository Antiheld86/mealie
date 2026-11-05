from pydantic import UUID4

from mealie.db.models.household import HouseholdMemberInvitation
from mealie.schema.household.household_member_invitation import ReadHouseholdMemberInvitation

from .repository_generic import HouseholdRepositoryGeneric


class RepositoryHouseholdMemberInvitations(
    HouseholdRepositoryGeneric[ReadHouseholdMemberInvitation, HouseholdMemberInvitation]
):
    def _read(self, household_id: UUID4 | None = None, user_id: UUID4 | None = None):
        stmt = self._query().order_by(HouseholdMemberInvitation.created_at)
        if household_id is not None:
            stmt = stmt.where(HouseholdMemberInvitation.household_id == household_id)
        if user_id is not None:
            stmt = stmt.where(HouseholdMemberInvitation.user_id == user_id)
        return [self.schema.model_validate(row) for row in self.session.execute(stmt).scalars().all()]

    def by_household(self, household_id: UUID4) -> list[ReadHouseholdMemberInvitation]:
        return self._read(household_id=household_id)

    def by_user(self, user_id: UUID4) -> list[ReadHouseholdMemberInvitation]:
        return self._read(user_id=user_id)

    def find(self, household_id: UUID4, user_id: UUID4) -> ReadHouseholdMemberInvitation | None:
        return next(iter(self._read(household_id=household_id, user_id=user_id)), None)
