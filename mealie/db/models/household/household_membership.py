from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint, false
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import Mapped, mapped_column, object_session, relationship

from .._model_base import BaseMixins, FilterableColumn, SqlAlchemyBase
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from ..users import User
    from .household import Household


class HouseholdMembership(SqlAlchemyBase, BaseMixins):
    """
    A user's membership of a household. Users always belong to their primary household
    (`users.household_id`) and may belong to additional households in the same group.
    Household-level permissions live here so they can differ per household.
    """

    __tablename__ = "households_to_users"
    __table_args__ = (UniqueConstraint("household_id", "user_id", name="household_id_user_id_key"),)

    id: FilterableColumn[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)

    household_id: FilterableColumn[GUID] = mapped_column(GUID, ForeignKey("households.id"), nullable=False, index=True)
    household: Mapped[Household] = relationship("Household", overlaps="memberships")
    user_id: FilterableColumn[GUID] = mapped_column(GUID, ForeignKey("users.id"), nullable=False, index=True)
    user: Mapped[User] = relationship("User", back_populates="household_memberships")
    group_id: AssociationProxy[GUID] = association_proxy("household", "group_id")

    can_manage_household: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())

    def __init__(self, household: Household, user: User, can_manage_household: bool = False, **_) -> None:
        self.household = household
        # appended from the user's side (backrefs don't cascade into the session)
        user.household_memberships.append(self)
        if (session := object_session(user)) is not None:
            session.add(self)
        self.can_manage_household = can_manage_household
