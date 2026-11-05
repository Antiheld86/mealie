import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import HouseholdPage from "./index.vue";

const mocks = vi.hoisted(() => ({
  getCurrentUserHousehold: vi.fn(),
  setPreferences: vi.fn(),
  refreshSelf: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
}));

const context = vi.hoisted(() => ({
  isPrimary: null as unknown as Ref<boolean>,
  householdId: null as unknown as Ref<string>,
}));

vi.mock("~/composables/use-household-context", () => ({
  useHouseholdContext: () => ({
    ...context,
    api: ref({
      households: {
        getCurrentUserHousehold: mocks.getCurrentUserHousehold,
        setPreferences: mocks.setPreferences,
      },
    }),
  }),
}));
vi.mock("~/composables/use-households", () => ({
  useHouseholdSelf: () => ({ actions: { refresh: mocks.refreshSelf } }),
}));
vi.mock("~/composables/use-toast", () => ({ alert: { success: mocks.success, error: mocks.error } }));

interface PageVm {
  household: { id: string; preferences: { privateHousehold: boolean } } | null;
  refHouseholdEditForm: { validate: () => boolean } | null;
  handleSubmit: () => Promise<void>;
}

describe("household settings page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    context.isPrimary = ref(true);
    context.householdId = ref("h1");
    mocks.getCurrentUserHousehold.mockResolvedValue({ data: { id: "h1", preferences: { privateHousehold: false } } });
    mocks.setPreferences.mockResolvedValue({ data: { privateHousehold: true } });
    vi.stubGlobal("definePageMeta", vi.fn());
    vi.stubGlobal("useSeoMeta", vi.fn());
  });
  afterEach(() => vi.unstubAllGlobals());

  async function mountPage() {
    const wrapper = mount({ ...HouseholdPage, render: () => null });
    await flushPromises();
    return { wrapper, vm: wrapper.vm as unknown as PageVm };
  }

  test("shows the preferences of the household in context", async () => {
    const { wrapper, vm } = await mountPage();
    expect(vm.household?.id).toBe("h1");
    wrapper.unmount();
  });

  test("reloads when another household is selected", async () => {
    const { wrapper } = await mountPage();
    mocks.getCurrentUserHousehold.mockResolvedValue({ data: { id: "h2", preferences: { privateHousehold: true } } });

    context.householdId.value = "h2";
    await flushPromises();

    expect((wrapper.vm as unknown as PageVm).household?.id).toBe("h2");
    wrapper.unmount();
  });

  test("saves the preferences and refreshes the cached household when it's the primary one", async () => {
    const { wrapper, vm } = await mountPage();
    vm.refHouseholdEditForm = { validate: () => true };

    await vm.handleSubmit();

    expect(mocks.setPreferences).toHaveBeenCalledWith({ privateHousehold: false });
    expect(mocks.refreshSelf).toHaveBeenCalled();
    expect(mocks.success).toHaveBeenCalled();
    wrapper.unmount();
  });

  test("leaves the cached primary household alone when another one was edited", async () => {
    context.isPrimary.value = false;
    const { wrapper, vm } = await mountPage();
    vm.refHouseholdEditForm = { validate: () => true };

    await vm.handleSubmit();

    expect(mocks.setPreferences).toHaveBeenCalled();
    expect(mocks.refreshSelf).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});
