import { useAdminApi } from "~/composables/api";
import type { UserHouseholdMembershipOut, UserHouseholdMembershipUpdate } from "~/lib/api/types/user";

interface HouseholdOption {
  id: string;
  name: string;
}

function toUpdates(memberships: UserHouseholdMembershipOut[]): UserHouseholdMembershipUpdate[] {
  return memberships.map(({ householdId, canManageHousehold }) => ({
    householdId,
    canManageHousehold: !!canManageHousehold,
  }));
}

/**
 * The households of a user as an admin edits them. The primary household is picked in the user form by name;
 * saving sends it together with every other membership.
 */
export function useAdminUserHouseholds(
  userId: MaybeRef<string>,
  households: Ref<HouseholdOption[] | null | undefined>,
  primaryHouseholdName: Ref<string | undefined>,
) {
  const adminApi = useAdminApi();

  const memberships = ref<UserHouseholdMembershipUpdate[]>([]);
  const primaryHouseholdId = computed(
    () => households.value?.find(household => household.name === primaryHouseholdName.value)?.id ?? "",
  );

  async function load() {
    const { data } = await adminApi.users.getHouseholds(toValue(userId));
    if (data) {
      memberships.value = toUpdates(data);
    }
  }

  /** Returns whether the memberships were saved (or there was nothing to save) */
  async function save() {
    if (!primaryHouseholdId.value) {
      return true;
    }

    const { data } = await adminApi.users.setHouseholds(toValue(userId), {
      primaryHouseholdId: primaryHouseholdId.value,
      households: memberships.value,
    });
    if (data) {
      memberships.value = toUpdates(data);
    }
    return !!data;
  }

  return { memberships, primaryHouseholdId, load, save };
}
