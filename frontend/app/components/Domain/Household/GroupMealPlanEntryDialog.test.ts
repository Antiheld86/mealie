import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { nextTick } from "vue";
import GroupMealPlanEntryDialog from "./GroupMealPlanEntryDialog.vue";
import HouseholdSelect from "./HouseholdSelect.vue";
import type { ReadPlanEntry } from "~/lib/api/types/meal-plan";

vi.mock("~/composables/use-mealplan-rules", () => ({
  useMealplanRules: () => ({ rules: ref([]) }),
  buildRuleQueryFilter: () => null,
}));

vi.mock("~/composables/use-households", () => ({
  useHouseholdSelf: () => ({ household: ref({ preferences: { firstDayOfWeek: 0 } }) }),
}));

function mountDialog(entry: ReadPlanEntry | null = null) {
  const wrapper = mount(GroupMealPlanEntryDialog, {
    props: { modelValue: false, entry, date: new Date(2026, 10, 5) },
    shallow: true,
    global: {
      mocks: { $globals: { icons: {} } },
      stubs: {
        HouseholdSelect,
        BaseDialog: { name: "BaseDialog", template: "<div><slot /></div>" },
        RecipeSelector: { template: "<div />", methods: { reset: () => undefined } },
      },
    },
  });
  return wrapper;
}

function planEntry(overrides: Partial<ReadPlanEntry> = {}): ReadPlanEntry {
  return {
    id: "entry",
    groupId: "g1",
    householdId: "h1",
    userId: "u1",
    date: "2026-11-05",
    entryType: "dinner",
    title: "Soup",
    text: "",
    recipeScale: 1,
    ...overrides,
  } as ReadPlanEntry;
}

describe("GroupMealPlanEntryDialog household", () => {
  beforeEach(() => {
    vi.stubGlobal("useMealieAuth", () => ({
      user: ref({
        householdId: "h1",
        households: [
          { householdId: "h1", householdName: "Home", householdSlug: "home", isPrimary: true },
          { householdId: "h2", householdName: "Cabin", householdSlug: "cabin", isPrimary: false },
        ],
      }),
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  async function open(wrapper: ReturnType<typeof mountDialog>) {
    await wrapper.setProps({ modelValue: true });
    await flushPromises();
  }

  test("a new entry is created in the chosen household", async () => {
    const wrapper = mountDialog();
    await open(wrapper);

    wrapper.findComponent(HouseholdSelect).vm.$emit("update:modelValue", "h2");
    await nextTick();
    wrapper.findComponent({ name: "BaseDialog" }).vm.$emit("submit");

    expect(wrapper.emitted("create")?.[0][0]).toMatchObject({ householdId: "h2" });
  });

  test("a new entry defaults to the primary household", async () => {
    const wrapper = mountDialog();
    await open(wrapper);
    wrapper.findComponent({ name: "BaseDialog" }).vm.$emit("submit");

    expect(wrapper.emitted("create")?.[0][0]).toMatchObject({ householdId: "h1" });
  });

  test("an existing entry can be moved to another household", async () => {
    const wrapper = mountDialog(planEntry({ householdId: "h1" }));
    await open(wrapper);

    wrapper.findComponent(HouseholdSelect).vm.$emit("update:modelValue", "h2");
    await nextTick();
    wrapper.findComponent({ name: "BaseDialog" }).vm.$emit("submit");

    expect(wrapper.emitted("update")?.[0][0]).toMatchObject({ id: "entry", householdId: "h2" });
  });
});
