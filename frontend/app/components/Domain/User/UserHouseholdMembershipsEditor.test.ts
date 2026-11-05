import { mount } from "@vue/test-utils";
import { describe, expect, test } from "vitest";
import UserHouseholdMembershipsEditor from "./UserHouseholdMembershipsEditor.vue";
import type { UserHouseholdMembershipUpdate } from "~/lib/api/types/user";

const households = [
  { id: "h1", name: "Home" },
  { id: "h2", name: "Cabin" },
  { id: "h3", name: "Lake House" },
];

const Checkbox = {
  props: ["modelValue", "disabled"],
  emits: ["update:modelValue"],
  template: "<input type=\"checkbox\" :checked=\"modelValue\" :disabled=\"disabled\" @change=\"$emit('update:modelValue', $event.target.checked)\" />",
};

function mountEditor(modelValue: UserHouseholdMembershipUpdate[], primaryHouseholdId = "h1") {
  return mount(UserHouseholdMembershipsEditor, {
    props: { modelValue, households, primaryHouseholdId },
    global: {
      mocks: { $globals: { icons: {} } },
      stubs: { VCheckbox: Checkbox, VSwitch: Checkbox },
    },
  });
}

function row(wrapper: ReturnType<typeof mountEditor>, id: string) {
  return {
    member: wrapper.find(`[data-test="member-${id}"]`),
    manager: wrapper.find(`[data-test="manager-${id}"]`),
  };
}

function lastUpdate(wrapper: ReturnType<typeof mountEditor>) {
  return wrapper.emitted("update:modelValue")?.at(-1)?.[0] as UserHouseholdMembershipUpdate[];
}

describe("UserHouseholdMembershipsEditor", () => {
  test("lists every household of the group with the user's memberships ticked", () => {
    const wrapper = mountEditor([
      { householdId: "h1", canManageHousehold: false },
      { householdId: "h2", canManageHousehold: true },
    ]);

    expect(row(wrapper, "h1").member.element).toHaveProperty("checked", true);
    expect(row(wrapper, "h2").member.element).toHaveProperty("checked", true);
    expect(row(wrapper, "h3").member.element).toHaveProperty("checked", false);
    expect(row(wrapper, "h2").manager.element).toHaveProperty("checked", true);
  });

  test("the primary household is always a membership and can't be removed", () => {
    const wrapper = mountEditor([{ householdId: "h1", canManageHousehold: false }]);

    expect(row(wrapper, "h1").member.attributes("disabled")).toBeDefined();
    expect(row(wrapper, "h2").member.attributes("disabled")).toBeUndefined();
  });

  test("ticking a household adds a membership without manager rights", async () => {
    const wrapper = mountEditor([{ householdId: "h1", canManageHousehold: false }]);

    await row(wrapper, "h3").member.setValue(true);

    expect(lastUpdate(wrapper)).toEqual([
      { householdId: "h1", canManageHousehold: false },
      { householdId: "h3", canManageHousehold: false },
    ]);
  });

  test("unticking a household removes the membership", async () => {
    const wrapper = mountEditor([
      { householdId: "h1", canManageHousehold: false },
      { householdId: "h2", canManageHousehold: true },
    ]);

    await row(wrapper, "h2").member.setValue(false);

    expect(lastUpdate(wrapper)).toEqual([{ householdId: "h1", canManageHousehold: false }]);
  });

  test("the manager switch changes only that membership", async () => {
    const wrapper = mountEditor([
      { householdId: "h1", canManageHousehold: false },
      { householdId: "h2", canManageHousehold: false },
    ]);

    await row(wrapper, "h2").manager.setValue(true);

    expect(lastUpdate(wrapper)).toEqual([
      { householdId: "h1", canManageHousehold: false },
      { householdId: "h2", canManageHousehold: true },
    ]);
  });

  test("a household can only be managed by someone who belongs to it", () => {
    const wrapper = mountEditor([{ householdId: "h1", canManageHousehold: false }]);
    expect(row(wrapper, "h3").manager.attributes("disabled")).toBeDefined();
  });

  test("choosing another primary household makes the user a member of it", async () => {
    const wrapper = mountEditor([{ householdId: "h1", canManageHousehold: false }]);

    await wrapper.setProps({ primaryHouseholdId: "h3" });

    expect(lastUpdate(wrapper)).toEqual([
      { householdId: "h1", canManageHousehold: false },
      { householdId: "h3", canManageHousehold: false },
    ]);
  });
});
