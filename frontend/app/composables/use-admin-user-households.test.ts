import { beforeEach, describe, expect, test, vi } from "vitest";
import { useAdminUserHouseholds } from "./use-admin-user-households";

const mocks = vi.hoisted(() => ({
  getHouseholds: vi.fn(),
  setHouseholds: vi.fn(),
}));

vi.mock("~/composables/api", () => ({
  useAdminApi: () => ({ users: { getHouseholds: mocks.getHouseholds, setHouseholds: mocks.setHouseholds } }),
}));

const options = [
  { id: "h1", name: "Home" },
  { id: "h2", name: "Cabin" },
];

function membership(householdId: string, canManageHousehold = false, isPrimary = false) {
  return { householdId, householdName: householdId, householdSlug: householdId, canManageHousehold, isPrimary };
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.getHouseholds.mockResolvedValue({ data: [membership("h1", false, true), membership("h2", true)] });
  mocks.setHouseholds.mockImplementation(async (_id: string, payload: { households: { householdId: string }[] }) => ({
    data: payload.households.map(h => membership(h.householdId)),
  }));
});

function setup(primaryName = "Home") {
  return useAdminUserHouseholds("u1", ref(options), ref(primaryName));
}

describe("useAdminUserHouseholds", () => {
  test("loads the memberships as an editable list", async () => {
    const { memberships, load } = setup();

    await load();

    expect(memberships.value).toEqual([
      { householdId: "h1", canManageHousehold: false },
      { householdId: "h2", canManageHousehold: true },
    ]);
  });

  test("the primary household is the one the page has selected, by name", () => {
    expect(setup("Cabin").primaryHouseholdId.value).toBe("h2");
    expect(setup("Unknown").primaryHouseholdId.value).toBe("");
  });

  test("saving replaces the memberships, including the primary household", async () => {
    const { memberships, load, save } = setup("Cabin");
    await load();
    memberships.value = [{ householdId: "h2", canManageHousehold: true }];

    expect(await save()).toBe(true);

    expect(mocks.setHouseholds).toHaveBeenCalledWith("u1", {
      primaryHouseholdId: "h2",
      households: [{ householdId: "h2", canManageHousehold: true }],
    });
  });

  test("saving is refused, and reported, when the server rejects the memberships", async () => {
    mocks.setHouseholds.mockResolvedValue({ data: null });
    const { load, save } = setup();
    await load();

    expect(await save()).toBe(false);
  });

  test("can save for a user whose id is only known after they were created", async () => {
    const userId = ref("");
    const { memberships, save } = useAdminUserHouseholds(userId, ref(options), ref("Home"));
    memberships.value = [{ householdId: "h1", canManageHousehold: false }];

    userId.value = "new-user";
    await save();

    expect(mocks.setHouseholds).toHaveBeenCalledWith("new-user", expect.anything());
  });

  test("nothing is saved before the primary household is known", async () => {
    const { save } = setup("Unknown");
    expect(await save()).toBe(true);
    expect(mocks.setHouseholds).not.toHaveBeenCalled();
  });
});
