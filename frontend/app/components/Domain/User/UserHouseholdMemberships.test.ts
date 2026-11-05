import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import UserHouseholdMemberships from "./UserHouseholdMemberships.vue";

const mocks = vi.hoisted(() => ({
  refresh: vi.fn(),
  accept: vi.fn(),
  decline: vi.fn(),
  leave: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
}));

const state = vi.hoisted(() => ({ invitations: [] as object[] }));

vi.mock("~/composables/use-household-invitations", () => ({
  useHouseholdInvitations: () => ({
    invitations: ref(state.invitations),
    refresh: mocks.refresh,
    accept: mocks.accept,
    decline: mocks.decline,
    leave: mocks.leave,
  }),
}));
vi.mock("~/composables/use-toast", () => ({ alert: { success: mocks.success, error: mocks.error } }));

const home = { householdId: "h1", householdName: "Home", householdSlug: "home", isPrimary: true };
const cabin = { householdId: "h2", householdName: "Cabin", householdSlug: "cabin", isPrimary: false };
const invitation = { id: "inv1", householdId: "h3", householdName: "Lake House", invitedByName: "Pat" };

function mountCard(households: object[]) {
  vi.stubGlobal("useMealieAuth", () => ({ user: ref({ householdId: "h1", households }) }));
  return mount(UserHouseholdMemberships, {
    global: {
      mocks: { $globals: { icons: {} } },
      stubs: {
        VBtn: { template: "<button v-bind=\"$attrs\"><slot /></button>" },
        VList: { template: "<div><slot /></div>" },
        VListItem: { template: "<div><slot /><slot name=\"append\" /></div>" },
        BaseDialog: true,
      },
    },
  });
}

describe("UserHouseholdMemberships", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    state.invitations = [];
    mocks.accept.mockResolvedValue(true);
    mocks.decline.mockResolvedValue(true);
    mocks.leave.mockResolvedValue(true);
  });
  afterEach(() => vi.unstubAllGlobals());

  test("renders nothing for a user with one household and no invitations", async () => {
    const wrapper = mountCard([home]);
    await flushPromises();
    expect(wrapper.find("[data-test=household-memberships]").exists()).toBe(false);
  });

  test("loads the invitations when shown", async () => {
    mountCard([home]);
    await flushPromises();
    expect(mocks.refresh).toHaveBeenCalled();
  });

  test("accepting an invitation joins the household", async () => {
    state.invitations = [invitation];
    const wrapper = mountCard([home]);
    await flushPromises();

    await wrapper.find("[data-test=accept-invitation]").trigger("click");
    await flushPromises();

    expect(mocks.accept).toHaveBeenCalledWith("inv1");
    expect(mocks.success).toHaveBeenCalled();
  });

  test("declining an invitation", async () => {
    state.invitations = [invitation];
    const wrapper = mountCard([home]);
    await flushPromises();

    await wrapper.find("[data-test=decline-invitation]").trigger("click");
    await flushPromises();

    expect(mocks.decline).toHaveBeenCalledWith("inv1");
  });

  test("an invitation that fails is reported", async () => {
    state.invitations = [invitation];
    mocks.accept.mockResolvedValue(false);
    const wrapper = mountCard([home]);
    await flushPromises();

    await wrapper.find("[data-test=accept-invitation]").trigger("click");
    await flushPromises();

    expect(mocks.error).toHaveBeenCalled();
  });

  test("only households other than the primary one can be left", async () => {
    const wrapper = mountCard([home, cabin]);
    await flushPromises();

    const leaveButtons = wrapper.findAll("[data-test=leave-household]");
    expect(leaveButtons).toHaveLength(1);
    expect(leaveButtons[0].attributes("data-household")).toBe("h2");
  });
});
