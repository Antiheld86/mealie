from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .._model_base import BaseMixins, FilterableColumn, SqlAlchemyBase
from .._model_utils.guid import GUID

if TYPE_CHECKING:
    from ..users import User
    from .household import Household


class HouseholdMemberInvitation(SqlAlchemyBase, BaseMixins):
    """
    A pending invitation for an existing user to join a household as an additional member.
    Accepting, declining or revoking an invitation deletes it, so every row is pending.
    """

    __tablename__ = "household_member_invitations"
    __table_args__ = (UniqueConstraint("household_id", "user_id", name="household_member_invitation_key"),)

    id: FilterableColumn[GUID] = mapped_column(GUID, primary_key=True, default=GUID.generate)

    household_id: FilterableColumn[GUID] = mapped_column(GUID, ForeignKey("households.id"), nullable=False, index=True)
    household: Mapped[Household] = relationship("Household")
    group_id: AssociationProxy[GUID] = association_proxy("household", "group_id")

    user_id: FilterableColumn[GUID] = mapped_column(GUID, ForeignKey("users.id"), nullable=False, index=True)
    user: Mapped[User] = relationship("User", foreign_keys=[user_id])
    invited_by_id: Mapped[GUID | None] = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"))
    invited_by: Mapped[User | None] = relationship("User", foreign_keys=[invited_by_id])

    def __init__(self, household_id: GUID, user_id: GUID, invited_by_id: GUID | None = None, **_) -> None:
        self.household_id = household_id
        self.user_id = user_id
        self.invited_by_id = invited_by_id
