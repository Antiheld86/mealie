import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import HouseholdContextSelect from "./HouseholdContextSelect.vue";

const mocks = vi.hoisted(() => ({ replace: vi.fn() }));

vi.mock("~/composables/api/api-client", () => ({
  useRequests: () => ({}),
}));

const home = { householdId: "h1", householdName: "Home", householdSlug: "home", isPrimary: true };
const cabin = { householdId: "h2", householdName: "Cabin", householdSlug: "cabin", isPrimary: false };

function mountSelect(households: object[], query: Record<string, unknown> = {}) {
  vi.stubGlobal("useMealieAuth", () => ({ user: ref({ householdId: "h1", households }) }));
  vi.stubGlobal("useRoute", () => reactive({ query }));
  vi.stubGlobal("useRouter", () => ({ replace: mocks.replace }));

  return mount(HouseholdContextSelect, {
    global: {
      mocks: { $globals: { icons: { household: "household" } } },
      stubs: {
        VSelect: {
          props: ["modelValue", "items"],
          emits: ["update:modelValue"],
          template: "<select class=\"household-select\" :data-value=\"modelValue\" @change=\"$emit('update:modelValue', 'h2')\" />",
        },
      },
    },
  });
}

describe("HouseholdContextSelect", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => vi.unstubAllGlobals());

  test("is hidden for a user with one household", () => {
    expect(mountSelect([home]).find(".household-select").exists()).toBe(false);
  });

  test("shows the household the page acts on", () => {
    const wrapper = mountSelect([home, cabin], { householdId: "h2" });
    expect(wrapper.find(".household-select").attributes("data-value")).toBe("h2");
  });

  test("choosing a household puts it in the URL", async () => {
    const wrapper = mountSelect([home, cabin]);
    await wrapper.find(".household-select").trigger("change");
    expect(mocks.replace).toHaveBeenCalledWith({ query: { householdId: "h2" } });
  });
});
