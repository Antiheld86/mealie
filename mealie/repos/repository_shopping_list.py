from pydantic import UUID4

from mealie.db.models.household.shopping_list import ShoppingList
from mealie.schema.household.group_shopping_list import ShoppingListOut, ShoppingListUpdate

from .repository_generic import HouseholdRepositoryGeneric


class RepositoryShoppingList(HouseholdRepositoryGeneric[ShoppingListOut, ShoppingList]):
    def update(self, item_id: UUID4, data: ShoppingListUpdate) -> ShoppingListOut:  # type: ignore
        data_dict = data.model_dump()
        if data_dict.get("household_id") is None:
            # an update that doesn't name a household keeps the list where it is
            data_dict.pop("household_id", None)
        return super().update(item_id, data_dict)
