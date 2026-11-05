from datetime import datetime

from pydantic import UUID4, AliasChoices, AliasPath, ConfigDict, Field

from mealie.schema._mealie import MealieModel


class CreateHouseholdMemberInvitation(MealieModel):
    email: str
    """The email address of an existing user in the same group"""


class SaveHouseholdMemberInvitation(MealieModel):
    household_id: UUID4
    user_id: UUID4
    invited_by_id: UUID4 | None = None


class ReadHouseholdMemberInvitation(SaveHouseholdMemberInvitation):
    id: UUID4
    created_at: datetime | None = None
    household_name: str = Field(validation_alias=AliasChoices("household_name", AliasPath("household", "name")))
    user_name: str = Field(validation_alias=AliasChoices("user_name", AliasPath("user", "full_name")))
    invited_by_name: str | None = Field(
        None, validation_alias=AliasChoices("invited_by_name", AliasPath("invited_by", "full_name"))
    )
    model_config = ConfigDict(from_attributes=True)
