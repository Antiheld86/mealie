import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { nextTick } from "vue";
import HouseholdSelect from "./HouseholdSelect.vue";
import type { UserHouseholdMembershipOut } from "~/lib/api/types/user";

const primary: UserHouseholdMembershipOut = {
  householdId: "h1",
  householdName: "Home",
  householdSlug: "home",
  isPrimary: true,
};
const other: UserHouseholdMembershipOut = {
  householdId: "h2",
  householdName: "Cabin",
  householdSlug: "cabin",
  isPrimary: false,
};

function mountSelect(households: UserHouseholdMembershipOut[], modelValue?: string | null) {
  vi.stubGlobal("useMealieAuth", () => ({ user: ref({ households }) }));

  const updates: (string | null | undefined)[] = [];
  const wrapper = mount(HouseholdSelect, {
    props: {
      "modelValue": modelValue,
      "onUpdate:modelValue": (value: string | null | undefined) => updates.push(value),
    },
    global: {
      mocks: { $globals: { icons: { household: "household" } } },
      stubs: {
        VSelect: {
          props: ["modelValue", "items", "label"],
          template: "<div class=\"household-select\">{{ items.map(i => i.householdName).join(',') }}</div>",
        },
      },
    },
  });
  return { wrapper, updates };
}

describe("HouseholdSelect", () => {
  beforeEach(() => {
    vi.stubGlobal("useI18n", () => ({ t: (key: string) => key }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("is hidden when the user only belongs to one household", async () => {
    const { wrapper } = mountSelect([primary]);
    await nextTick();
    expect(wrapper.find(".household-select").exists()).toBe(false);
  });

  test("lists every household when the user belongs to several", async () => {
    const { wrapper } = mountSelect([primary, other]);
    await nextTick();
    expect(wrapper.find(".household-select").text()).toBe("Home,Cabin");
  });

  test("defaults to the primary household", async () => {
    const { updates } = mountSelect([other, primary]);
    await nextTick();
    expect(updates).toEqual(["h1"]);
  });

  test("keeps a household that was already chosen", async () => {
    const { updates } = mountSelect([primary, other], "h2");
    await nextTick();
    expect(updates).toEqual([]);
  });
});
