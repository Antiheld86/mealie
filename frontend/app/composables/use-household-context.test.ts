import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { useHouseholdContext } from "./use-household-context";

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("~/composables/api/api-client", () => ({
  useRequests: () => ({ get: mocks.get, post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() }),
}));

const households = [
  { householdId: "h1", householdName: "Home", householdSlug: "home", isPrimary: true, canManageHousehold: true },
  { householdId: "h2", householdName: "Cabin", householdSlug: "cabin", isPrimary: false, canManageHousehold: false },
];

function setup(query: Record<string, unknown> = {}) {
  vi.stubGlobal("useMealieAuth", () => ({ user: ref({ householdId: "h1", households }) }));
  vi.stubGlobal("useRoute", () => reactive({ query }));
  vi.stubGlobal("useRouter", () => ({ replace: mocks.replace }));
  return useHouseholdContext();
}

describe("useHouseholdContext", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.unstubAllGlobals());

  test("acts on the primary household by default", () => {
    const context = setup();
    expect(context.householdId.value).toBe("h1");
    expect(context.isPrimary.value).toBe(true);
  });

  test("acts on the household named in the query", () => {
    const context = setup({ householdId: "h2" });
    expect(context.householdId.value).toBe("h2");
    expect(context.isPrimary.value).toBe(false);
  });

  test("ignores a household the user doesn't belong to", () => {
    const context = setup({ householdId: "someone-elses" });
    expect(context.householdId.value).toBe("h1");
  });

  test("can manage only the households where the user is a manager", () => {
    expect(setup().canManage.value).toBe(true);
    expect(setup({ householdId: "h2" }).canManage.value).toBe(false);
  });

  test("selecting a household puts it in the query, and the primary one takes it out", () => {
    const context = setup({ tab: "x" });

    context.select("h2");
    expect(mocks.replace).toHaveBeenLastCalledWith({ query: { tab: "x", householdId: "h2" } });

    context.select("h1");
    expect(mocks.replace).toHaveBeenLastCalledWith({ query: { tab: "x" } });
  });

  test("requests act on the selected household", async () => {
    await setup({ householdId: "h2" }).api.value.households.getMemberInvitations();
    expect(mocks.get).toHaveBeenLastCalledWith(
      "/api/households/member-invitations",
      { householdId: "h2" },
      undefined,
    );

    await setup().api.value.groupWebhooks.getAll();
    expect(mocks.get.mock.lastCall?.[1]?.householdId).toBeUndefined();
  });
});
