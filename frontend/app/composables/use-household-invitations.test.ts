import { beforeEach, describe, expect, test, vi } from "vitest";
import { useHouseholdInvitations } from "./use-household-invitations";

const mocks = vi.hoisted(() => ({
  getHouseholdInvitations: vi.fn(),
  acceptHouseholdInvitation: vi.fn(),
  declineHouseholdInvitation: vi.fn(),
  leaveHousehold: vi.fn(),
  getSession: vi.fn(),
}));

vi.mock("~/composables/api", () => ({
  useUserApi: () => ({
    users: {
      getHouseholdInvitations: mocks.getHouseholdInvitations,
      acceptHouseholdInvitation: mocks.acceptHouseholdInvitation,
      declineHouseholdInvitation: mocks.declineHouseholdInvitation,
      leaveHousehold: mocks.leaveHousehold,
    },
  }),
}));

const invitation = { id: "inv1", householdId: "h2", householdName: "Cabin" };

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("useMealieAuth", () => ({ getSession: mocks.getSession }));
  mocks.getHouseholdInvitations.mockResolvedValue({ data: [invitation] });
  mocks.acceptHouseholdInvitation.mockResolvedValue({ data: invitation });
  mocks.declineHouseholdInvitation.mockResolvedValue({ data: invitation });
  mocks.leaveHousehold.mockResolvedValue({ data: { message: "" } });
});

describe("useHouseholdInvitations", () => {
  test("loads the pending invitations", async () => {
    const { invitations, refresh } = useHouseholdInvitations();
    await refresh();
    expect(invitations.value).toEqual([invitation]);
  });

  test("accepting joins the household, so the signed-in user is reloaded", async () => {
    const { accept } = useHouseholdInvitations();

    expect(await accept("inv1")).toBe(true);

    expect(mocks.acceptHouseholdInvitation).toHaveBeenCalledWith("inv1");
    expect(mocks.getSession).toHaveBeenCalled();
    expect(mocks.getHouseholdInvitations).toHaveBeenCalled();
  });

  test("declining changes nothing about the user's households", async () => {
    const { decline } = useHouseholdInvitations();

    expect(await decline("inv1")).toBe(true);

    expect(mocks.declineHouseholdInvitation).toHaveBeenCalledWith("inv1");
    expect(mocks.getSession).not.toHaveBeenCalled();
  });

  test("reports an invitation that can't be answered, without reloading the user", async () => {
    mocks.acceptHouseholdInvitation.mockResolvedValue({ data: null });
    const { accept } = useHouseholdInvitations();

    expect(await accept("gone")).toBe(false);

    expect(mocks.getSession).not.toHaveBeenCalled();
  });

  test("leaving a household reloads the signed-in user", async () => {
    const { leave } = useHouseholdInvitations();

    expect(await leave("h2")).toBe(true);

    expect(mocks.leaveHousehold).toHaveBeenCalledWith("h2");
    expect(mocks.getSession).toHaveBeenCalled();
  });
});
