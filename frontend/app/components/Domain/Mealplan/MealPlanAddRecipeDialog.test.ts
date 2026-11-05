import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import MealPlanAddRecipeDialog from "./MealPlanAddRecipeDialog.vue";

const mocks = vi.hoisted(() => ({
  createOne: vi.fn(),
}));

vi.mock("~/composables/api", () => ({
  useUserApi: () => ({ mealplans: { createOne: mocks.createOne } }),
}));
vi.mock("~/composables/use-toast", () => ({
  alert: { success: vi.fn(), error: vi.fn() },
}));
vi.mock("~/composables/use-group-mealplan", () => ({
  useMealPlanEntryDates: () => ({
    isWeekEntry: ref(false),
    weekRange: computed(() => ({ start: new Date(), end: new Date() })),
    entryDatesPayload: computed(() => ({ date: "2026-11-05", endDate: null })),
    pickerModel: ref(new Date()),
    pickerMultiple: computed(() => false),
  }),
}));

interface DialogVm {
  householdId: string | null;
  addRecipeToPlan: () => Promise<void>;
}

describe("MealPlanAddRecipeDialog household", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.createOne.mockResolvedValue({ response: { status: 201 } });
    vi.stubGlobal("usePlanTypeOptions", () => []);
    vi.stubGlobal("useRouter", () => ({ push: vi.fn() }));
    vi.stubGlobal("useMealieAuth", () => ({ user: ref({ householdId: "h1", households: [] }) }));
  });

  afterEach(() => vi.unstubAllGlobals());

  function mountDialog() {
    const wrapper = mount({ ...MealPlanAddRecipeDialog, render: () => null }, {
      props: { recipeId: "r1", modelValue: true },
    });
    return { wrapper, vm: wrapper.vm as unknown as DialogVm };
  }

  test("adds the recipe to the chosen household", async () => {
    const { wrapper, vm } = mountDialog();
    vm.householdId = "h2";

    await vm.addRecipeToPlan();

    expect(mocks.createOne).toHaveBeenCalledWith(expect.objectContaining({ recipeId: "r1", householdId: "h2" }));
    wrapper.unmount();
  });

  test("adds the recipe to the primary household by default", async () => {
    const { wrapper, vm } = mountDialog();

    await vm.addRecipeToPlan();

    expect(mocks.createOne).toHaveBeenCalledWith(expect.objectContaining({ householdId: "h1" }));
    wrapper.unmount();
  });
});
