import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import MembersPage from "./members.vue";

const mocks = vi.hoisted(() => ({
  invite: vi.fn(),
  refresh: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
}));

vi.mock("~/composables/use-household-members", () => ({
  useHouseholdMembers: () => ({
    members: ref([]),
    invitations: ref([]),
    refresh: mocks.refresh,
    invite: mocks.invite,
    revoke: vi.fn(),
    remove: vi.fn(),
    setPermissions: vi.fn(),
    isPrimaryMember: () => true,
    canManageHousehold: () => false,
  }),
}));
vi.mock("~/composables/use-household-context", () => ({
  useHouseholdContext: () => ({ canManage: ref(true), householdId: ref("h1"), household: ref({ householdName: "Home" }) }),
}));
vi.mock("~/composables/use-toast", () => ({
  alert: { success: mocks.success, error: mocks.error },
}));

interface PageVm {
  inviteDialog: boolean;
  inviteEmail: string;
  submitInvite: () => Promise<void>;
}

describe("household members page invitations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("definePageMeta", vi.fn());
    vi.stubGlobal("useSeoMeta", vi.fn());
    vi.stubGlobal("useMealieAuth", () => ({ user: ref({ id: "u1" }) }));
  });
  afterEach(() => vi.unstubAllGlobals());

  function mountPage() {
    const wrapper = mount({ ...MembersPage, render: () => null });
    return { wrapper, vm: wrapper.vm as unknown as PageVm };
  }

  test("a sent invitation closes the dialog and is confirmed", async () => {
    mocks.invite.mockResolvedValue(true);
    const { wrapper, vm } = mountPage();
    vm.inviteDialog = true;
    vm.inviteEmail = "  pat@example.com ";

    await vm.submitInvite();

    expect(mocks.invite).toHaveBeenCalledWith("pat@example.com");
    expect(vm.inviteDialog).toBe(false);
    expect(vm.inviteEmail).toBe("");
    expect(mocks.success).toHaveBeenCalled();
    wrapper.unmount();
  });

  test("a failed invitation keeps the dialog open so it can be corrected", async () => {
    mocks.invite.mockResolvedValue(false);
    const { wrapper, vm } = mountPage();
    vm.inviteDialog = true;
    vm.inviteEmail = "nobody@example.com";

    await vm.submitInvite();

    expect(vm.inviteDialog).toBe(true);
    expect(vm.inviteEmail).toBe("nobody@example.com");
    expect(mocks.error).toHaveBeenCalled();
    wrapper.unmount();
  });

  test("an empty address sends nothing", async () => {
    const { wrapper, vm } = mountPage();
    vm.inviteEmail = "   ";

    await vm.submitInvite();

    expect(mocks.invite).not.toHaveBeenCalled();
    wrapper.unmount();
  });
});
