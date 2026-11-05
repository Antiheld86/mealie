import { useRequests } from "~/composables/api/api-client";
import { UserApi } from "~/lib/api";
import { scopeToHousehold } from "~/lib/api/base/household-scope";

/**
 * The household a household management page acts on: the one named by `?householdId=` in the URL if the user
 * belongs to it, otherwise their primary household. `api` sends its requests to that household.
 */
export function useHouseholdContext() {
  const { user } = useMealieAuth();
  const route = useRoute();
  const router = useRouter();
  const requests = useRequests();

  const households = computed(() => user.value?.households ?? []);
  const primaryHouseholdId = computed(() => user.value?.householdId ?? null);

  const householdId = computed(() => {
    const requested = route.query.householdId;
    const isMember = typeof requested === "string" && households.value.some(h => h.householdId === requested);
    return isMember ? requested : primaryHouseholdId.value;
  });
  const isPrimary = computed(() => householdId.value === primaryHouseholdId.value);
  const household = computed(() => households.value.find(h => h.householdId === householdId.value));
  const canManage = computed(() => !!user.value?.admin || !!household.value?.canManageHousehold);

  // the primary household is the default, so it stays out of the URL
  const api = computed(() => new UserApi(scopeToHousehold(requests, isPrimary.value ? null : householdId.value)));

  function select(id: string) {
    const { householdId: _current, ...query } = route.query;
    router.replace({ query: id === primaryHouseholdId.value ? query : { ...query, householdId: id } });
  }

  return { households, householdId, isPrimary, household, canManage, api, select };
}
