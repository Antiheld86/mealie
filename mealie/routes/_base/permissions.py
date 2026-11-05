from collections.abc import Callable
from enum import StrEnum
from typing import Any

from fastapi import Depends, HTTPException, Query, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from mealie.core.dependencies import get_current_user
from mealie.db.db_setup import generate_session
from mealie.lang.providers import Translator, get_locale_provider
from mealie.repos.all_repositories import get_repositories
from mealie.schema.response import ErrorResponse
from mealie.schema.user.user import PrivateUser


class Perm(StrEnum):
    """
    A permission a route can require. The prefix names the scope the user flag applies to.
    `ANY_VALID_USER` marks a route as open to any signed-in user on purpose.
    """

    ANY_VALID_USER = "any_valid_user"
    GROUP_ORGANIZE = "group:organize"
    GROUP_MANAGE = "group:manage"
    GROUP_INVITE = "group:invite"
    HOUSEHOLD_MANAGE = "household:manage"


_GRANTED_BY: dict[Perm, Callable[[PrivateUser], bool]] = {
    Perm.ANY_VALID_USER: lambda _: True,
    Perm.GROUP_ORGANIZE: lambda user: user.can_organize,
    Perm.GROUP_MANAGE: lambda user: user.can_manage,
    Perm.HOUSEHOLD_MANAGE: lambda user: user.can_manage_household,
    Perm.GROUP_INVITE: lambda user: user.can_invite,
}


def _error(status_code: int, message: str | None) -> HTTPException:
    # The frontend shows `detail.message` as a toast, so a message is only sent when one is given.
    if message is None:
        return HTTPException(status_code)
    return HTTPException(status_code, detail=ErrorResponse.respond(message=message))


def forbidden(message: str | None = None) -> HTTPException:
    """The caller can see the resource but may not perform the action."""
    return _error(status.HTTP_403_FORBIDDEN, message)


def not_found(message: str | None = None) -> HTTPException:
    """The caller cannot see the resource. Use it for missing and inaccessible resources alike."""
    return _error(status.HTTP_404_NOT_FOUND, message)


def get_target_household_id(
    household_id: UUID4 | None = Query(
        None,
        alias="householdId",
        description="The household to act on. Defaults to the user's primary household.",
    ),
    user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
    translator: Translator = Depends(get_locale_provider),
) -> UUID4:
    """
    The household a household-management request acts on: the requested one, or the user's primary household.
    Raises a 403 unless the user is a member of it. Admins may act on any household in their group.
    """
    if household_id is None or household_id == user.household_id:
        return user.household_id

    if any(membership.household_id == household_id for membership in user.households):
        return household_id

    if user.admin:
        household = get_repositories(session, group_id=user.group_id, household_id=None).households.get_one(
            household_id
        )
        if household is not None:
            return household_id

    raise forbidden(translator.t("household.not-a-member"))


class RequirePermission:
    """
    Route dependency that answers 403 unless the current user holds `perm`. The instance stays on the
    route's dependant, so the permission each route declares can be read back from `app.routes`.
    """

    def __init__(self, perm: Perm) -> None:
        self.perm = perm

    def __call__(
        self,
        user: PrivateUser = Depends(get_current_user),
        translator: Translator = Depends(get_locale_provider),
    ) -> None:
        if not _GRANTED_BY[self.perm](user):
            raise forbidden(translator.t("exceptions.permission-denied"))


def require(perm: Perm) -> Any:
    """Declare the permission a route needs: `@router.post("", dependencies=[require(Perm.GROUP_ORGANIZE)])`."""
    if perm is Perm.HOUSEHOLD_MANAGE:
        return Depends(RequireHouseholdPermission(perm))
    return Depends(RequirePermission(perm))


class RequireHouseholdPermission(RequirePermission):
    """
    Like `RequirePermission`, for permissions that are granted per household. It checks the user's membership in the
    household the request acts on (see `get_target_household_id`), not just their primary household.
    """

    def __call__(  # type: ignore[override]
        self,
        user: PrivateUser = Depends(get_current_user),
        household_id: UUID4 = Depends(get_target_household_id),
        translator: Translator = Depends(get_locale_provider),
    ) -> None:
        if user.admin:
            return

        membership = next((m for m in user.households if m.household_id == household_id), None)
        if membership is None or not membership.can_manage_household:
            raise forbidden(translator.t("exceptions.permission-denied"))
