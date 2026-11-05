import { mount } from "@vue/test-utils";
import { ref } from "vue";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import ShoppingListsPage from "./index.vue";

const mocks = vi.hoisted(() => ({
  getAll: vi.fn(),
  createOne: vi.fn(),
  fetchMembers: vi.fn(),
}));

vi.mock("~/composables/api", () => ({
  useUserApi: () => ({
    shopping: { lists: { getAll: mocks.getAll, createOne: mocks.createOne } },
    households: { fetchMembers: mocks.fetchMembers },
  }),
}));
vi.mock("~/composables/use-users/preferences", () => ({
  useShoppingListPreferences: () => ref({ viewAllLists: true }),
}));

interface PageVm {
  state: { createName: string; createHouseholdId: string | null };
  createOne: () => Promise<void>;
  toggleOwnerDialog: (list: { id: string; householdId: string; userId: string }) => Promise<void>;
}

describe("shopping lists page households", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getAll.mockResolvedValue({ data: { items: [] } });
    mocks.createOne.mockResolvedValue({ data: { id: "new" } });
    mocks.fetchMembers.mockResolvedValue({ data: { items: [] } });

    vi.stubGlobal("definePageMeta", vi.fn());
    vi.stubGlobal("useSeoMeta", vi.fn());
    vi.stubGlobal("useRoute", () => ({ query: {} }));
    vi.stubGlobal("useAsyncKey", () => "key");
    vi.stubGlobal("useAsyncData", () => ({ data: ref([]) }));
    vi.stubGlobal("useMealieAuth", () => ({ user: ref({ id: "u1", householdId: "h1" }) }));
  });

  afterEach(() => vi.unstubAllGlobals());

  function mountPage() {
    const wrapper = mount({ ...ShoppingListsPage, render: () => null });
    return { wrapper, vm: wrapper.vm as unknown as PageVm };
  }

  test("a new list is created in the chosen household", async () => {
    const { wrapper, vm } = mountPage();
    vm.state.createName = "Groceries";
    vm.state.createHouseholdId = "h2";

    await vm.createOne();

    expect(mocks.createOne).toHaveBeenCalledWith({ name: "Groceries", householdId: "h2" });
    wrapper.unmount();
  });

  test("the owner can be chosen from the members of the list's household", async () => {
    const { wrapper, vm } = mountPage();

    await vm.toggleOwnerDialog({ id: "l1", householdId: "h2", userId: "u1" });

    expect(mocks.fetchMembers).toHaveBeenCalledWith(1, -1, { householdId: "h2" });
    wrapper.unmount();
  });
});
