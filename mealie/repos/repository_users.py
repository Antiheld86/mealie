import random
import shutil

from pydantic import UUID4
from sqlalchemy import delete, select

from mealie.assets import users as users_assets
from mealie.core.config import get_app_settings
from mealie.db.models.users.user_to_recipe import UserToRecipe
from mealie.schema.user.user import PrivateUser, UserRatingOut

from ..db.models.household import GroupMealPlan, Household, HouseholdMembership, ShoppingList
from ..db.models.users import User
from .repository_generic import GroupRepositoryGeneric

settings = get_app_settings()


class RepositoryUsers(GroupRepositoryGeneric[PrivateUser, User]):
    def update_password(self, id, password: str):
        entry = self._query_one(match_value=id)
        if settings.IS_DEMO:
            user_to_update = self.schema.model_validate(entry)
            if user_to_update.is_default_user:
                # do not update the default user in demo mode
                return user_to_update

        entry.update_password(password)
        self.session.commit()

        return self.schema.model_validate(entry)

    def create(self, user: PrivateUser | dict):  # type: ignore
        new_user = super().create(user)

        # Select Random Image
        all_images = [
            users_assets.img_random_1,
            users_assets.img_random_2,
            users_assets.img_random_3,
        ]
        random_image = random.choice(all_images)
        shutil.copyfile(random_image, new_user.directory() / "profile.webp")

        return new_user

    def update(self, match_value: str | int | UUID4, new_data: dict | PrivateUser) -> PrivateUser:
        if settings.IS_DEMO:
            user_to_update = self.get_one(match_value)
            if user_to_update and user_to_update.is_default_user:
                # do not update the default user in demo mode
                return user_to_update

        return super().update(match_value, new_data)

    def delete(self, value: str | UUID4, match_key: str | None = None) -> User:
        if settings.IS_DEMO:
            user_to_delete = self.get_one(value, match_key)
            if user_to_delete and user_to_delete.is_default_user:
                # do not update the default user in demo mode
                return user_to_delete

        user = self._query_one(value, match_key)
        self._release_household_data(user.id)

        entry = super().delete(value, match_key)
        # Delete the user's directory
        shutil.rmtree(PrivateUser.get_directory(value))
        return entry

    def set_household_manager(self, user_id: UUID4, household_id: UUID4, can_manage_household: bool) -> None:
        """Set whether the user can manage a household they are a member of. Does nothing for non-members."""
        membership = self.session.execute(
            select(HouseholdMembership).where(
                HouseholdMembership.user_id == user_id, HouseholdMembership.household_id == household_id
            )
        ).scalar_one_or_none()
        if membership is not None:
            membership.can_manage_household = can_manage_household
            self.session.commit()

    def add_household_membership(self, user_id: UUID4, household_id: UUID4) -> None:
        """Make the user a member of a household. Does nothing if they already are."""
        exists = self.session.execute(
            select(HouseholdMembership.id).where(
                HouseholdMembership.user_id == user_id, HouseholdMembership.household_id == household_id
            )
        ).first()
        if exists:
            return

        user = self.session.get(User, user_id)
        household = self.session.get(Household, household_id)
        if user is None or household is None:
            return

        HouseholdMembership(household=household, user=user)
        self.session.commit()

    def remove_household_membership(self, user_id: UUID4, household_id: UUID4) -> None:
        """
        Remove the user from a household (never their primary one). Meal plans stay in the household, and
        shopping lists the user owned there go to another member.
        """
        self._release_household_data(user_id, household_id)
        self.session.execute(
            delete(HouseholdMembership).where(
                HouseholdMembership.user_id == user_id, HouseholdMembership.household_id == household_id
            )
        )
        self.session.commit()

    def set_household_memberships(
        self, user_id: UUID4, primary_household_id: UUID4, can_manage: dict[UUID4, bool]
    ) -> None:
        """
        Replace the user's memberships. `can_manage` maps each household they should belong to onto their manager
        flag there; it must include the primary household. Lists in households they are removed from are handed to
        other members.
        """
        user = self.session.get(User, user_id)
        if user is None:
            return

        if user.household_id != primary_household_id:
            user.household = self.session.get(Household, primary_household_id)  # type: ignore[assignment]
            self.session.flush()

        current = {membership.household_id: membership for membership in user.household_memberships}
        for household_id in current.keys() - can_manage.keys():
            self._release_household_data(user_id, household_id)
            user.household_memberships.remove(current[household_id])

        for household_id, flag in can_manage.items():
            if household_id in current:
                current[household_id].can_manage_household = flag
            else:
                household = self.session.get(Household, household_id)
                if household is not None:
                    HouseholdMembership(household=household, user=user, can_manage_household=flag)

        self.session.commit()

    def _release_household_data(self, user_id: UUID4, household_id: UUID4 | None = None) -> None:
        """
        Meal plans and shopping lists belong to a household that may have other members, so deleting a user (or
        removing them from a household) keeps them: meal plan entries lose their author, and lists go to another
        member of the list's household (managers first, then the longest-standing member). Lists nobody else can
        reach are deleted. Only the given household is touched, if any.
        """
        plan_query = select(GroupMealPlan).where(GroupMealPlan.user_id == user_id)
        list_query = select(ShoppingList).where(ShoppingList.user_id == user_id)
        if household_id is not None:
            plan_query = plan_query.where(GroupMealPlan.household_id == household_id)
            list_query = list_query.where(ShoppingList.household_id == household_id)

        for plan in self.session.execute(plan_query).scalars():
            plan.user_id = None

        for shopping_list in self.session.execute(list_query).scalars().all():
            successor = self.session.execute(
                select(HouseholdMembership.user_id)
                .where(
                    HouseholdMembership.household_id == shopping_list.household_id,
                    HouseholdMembership.user_id != user_id,
                )
                .order_by(HouseholdMembership.can_manage_household.desc(), HouseholdMembership.created_at)
                .limit(1)
            ).scalar_one_or_none()

            if successor is None:
                self.session.delete(shopping_list)
            else:
                shopping_list.user_id = successor

        self.session.flush()

    def get_by_username(self, username: str) -> PrivateUser | None:
        stmt = select(User).filter(User.username == username)
        dbuser = self.session.execute(stmt).scalars().one_or_none()
        return None if dbuser is None else self.schema.model_validate(dbuser)

    def get_locked_users(self) -> list[PrivateUser]:
        stmt = select(User).filter(User.locked_at != None)  # noqa E711
        results = self.session.execute(stmt).scalars().all()
        return [self.schema.model_validate(x) for x in results]


class RepositoryUserRatings(GroupRepositoryGeneric[UserRatingOut, UserToRecipe]):
    # Since users can post events on recipes that belong to other households,
    # this is a group repository, rather than a household repository.

    def get_by_user(self, user_id: UUID4, favorites_only=False) -> list[UserRatingOut]:
        stmt = select(UserToRecipe).filter(UserToRecipe.user_id == user_id)
        if favorites_only:
            stmt = stmt.filter(UserToRecipe.is_favorite)

        results = self.session.execute(stmt).scalars().all()
        return [self.schema.model_validate(x) for x in results]

    def get_by_recipe(self, recipe_id: UUID4, favorites_only=False) -> list[UserRatingOut]:
        stmt = select(UserToRecipe).filter(UserToRecipe.recipe_id == recipe_id)
        if favorites_only:
            stmt = stmt.filter(UserToRecipe.is_favorite)

        results = self.session.execute(stmt).scalars().all()
        return [self.schema.model_validate(x) for x in results]

    def get_by_user_and_recipe(self, user_id: UUID4, recipe_id: UUID4) -> UserRatingOut | None:
        stmt = select(UserToRecipe).filter(UserToRecipe.user_id == user_id, UserToRecipe.recipe_id == recipe_id)
        result = self.session.execute(stmt).scalars().one_or_none()
        return None if result is None else self.schema.model_validate(result)
