from datetime import UTC, datetime

from pydantic import UUID4, BaseModel

from mealie.db.models.household import GroupMealPlan
from mealie.schema.meal_plan.new_meal import ReadPlanEntry

from .repository_generic import HouseholdRepositoryGeneric


class RepositoryMeals(HouseholdRepositoryGeneric[ReadPlanEntry, GroupMealPlan]):
    def update(self, match_value: str | int | UUID4, new_data: dict | BaseModel) -> ReadPlanEntry:
        # The author of an entry can't be changed through an update
        new_data = new_data if isinstance(new_data, dict) else new_data.model_dump()
        new_data["user_id"] = self._query_one(match_value=match_value).user_id
        if new_data.get("household_id") is None:
            # an update that doesn't name a household keeps the entry where it is
            new_data.pop("household_id", None)
        return super().update(match_value, new_data)

    def get_today(self, tz=UTC) -> list[ReadPlanEntry]:
        if not self.household_id and self.household_ids is None:
            raise Exception("household_id not set")

        today = datetime.now(tz=tz).date()
        stmt = self._query(with_options=False).filter(
            GroupMealPlan.date == today,
            GroupMealPlan.end_date.is_(None),  # week entries aren't planned for a specific day
        )
        if self.household_id:
            stmt = stmt.filter(GroupMealPlan.household_id == self.household_id)
        plans = self.session.execute(stmt).scalars().all()
        return [self.schema.model_validate(x) for x in plans]

    def get_meals_by_date_range(self, start_date: datetime, end_date: datetime) -> list[ReadPlanEntry]:
        if not self.household_id and self.household_ids is None:
            raise Exception("household_id not set")

        stmt = self._query(with_options=False).filter(
            GroupMealPlan.date >= start_date.date(),
            GroupMealPlan.date <= end_date.date(),
            GroupMealPlan.end_date.is_(None),  # week entries aren't planned for a specific day
        )
        if self.household_id:
            stmt = stmt.filter(GroupMealPlan.household_id == self.household_id)
        plans = self.session.execute(stmt).scalars().all()
        return [self.schema.model_validate(x) for x in plans]
