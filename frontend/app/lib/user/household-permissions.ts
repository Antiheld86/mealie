import type { UserOut } from "~/lib/api/types/user";

/** Whether the user can manage at least one household they belong to, or is an admin */
export function canManageAnyHousehold(user: Pick<UserOut, "admin" | "canManageHousehold" | "households"> | null | undefined) {
  if (!user) {
    return false;
  }
  return !!user.admin || !!user.canManageHousehold || !!user.households?.some(household => household.canManageHousehold);
}
