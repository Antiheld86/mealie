from collections.abc import Generator
from contextlib import contextmanager

from fastapi import HTTPException, status

from mealie.lang.providers import Translator
from mealie.routes._base.permissions import not_found
from mealie.schema.response import ErrorResponse
from mealie.services.household_services.household_membership_service import (
    InvalidMembershipChangeError,
    MembershipNotFoundError,
)


@contextmanager
def membership_errors(translator: Translator) -> Generator[None]:
    """Turn the membership service's errors into HTTP responses"""
    try:
        yield
    except MembershipNotFoundError as e:
        raise not_found(translator.t("household.membership-not-found")) from e
    except InvalidMembershipChangeError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse.respond(message=translator.t("household.invalid-membership-change")),
        ) from e
