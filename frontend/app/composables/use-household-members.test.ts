import { beforeEach, describe, expect, test, vi } from "vitest";
import { useHouseholdMembers } from "./use-household-members";
import type { UserOut } from "~/lib/api/types/user";

const mocks = vi.hoisted(() => ({
  fetchMembers: vi.fn(),
  getMemberInvitations: vi.fn(),
  inviteMember: vi.fn(),
  revokeMemberInvitation: vi.fn(),
  removeMember: vi.fn(),
  setMemberPermissions: vi.fn(),
  householdId: { value: "h2" },
}));

vi.mock("~/composables/use-household-context", () => ({
  useHouseholdContext: () => ({
    householdId: mocks.householdId,
    api: ref({
      households: {
        fetchMembers: mocks.fetchMembers,
        getMemberInvitations: mocks.getMemberInvitations,
        inviteMember: mocks.inviteMember,
        revokeMemberInvitation: mocks.revokeMemberInvitation,
        removeMember: mocks.removeMember,
        setMemberPermissions: mocks.setMemberPermissions,
      },
    }),
  }),
}));

function member(id: string, primaryHouseholdId: string, canManageHousehold = false): UserOut {
  return {
    id,
    canManage: true,
    canInvite: false,
    canOrganize: false,
    canManageHousehold,
    households: [
      { householdId: "h1", householdName: "Home", householdSlug: "home", isPrimary: primaryHouseholdId === "h1" },
      { householdId: "h2", householdName: "Cabin", householdSlug: "cabin", isPrimary: primaryHouseholdId === "h2", canManageHousehold },
    ],
  } as unknown as UserOut;
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.householdId.value = "h2";
  mocks.fetchMembers.mockResolvedValue({ data: { items: [member("u1", "h2", true), member("u2", "h1")] } });
  mocks.getMemberInvitations.mockResolvedValue({ data: [{ id: "inv1", userName: "Pat" }] });
  mocks.inviteMember.mockResolvedValue({ data: { id: "inv2" } });
  mocks.revokeMemberInvitation.mockResolvedValue({ data: { id: "inv1" } });
  mocks.removeMember.mockResolvedValue({ data: {} });
  mocks.setMemberPermissions.mockResolvedValue({ data: {} });
});

describe("useHouseholdMembers", () => {
  test("loads the members and the pending invitations", async () => {
    const { members, invitations, refresh } = useHouseholdMembers();

    await refresh();

    expect(members.value.map(m => m.id)).toEqual(["u1", "u2"]);
    expect(invitations.value.map(i => i.id)).toEqual(["inv1"]);
  });

  test("tells which members have this household as their primary one", async () => {
    const { members, refresh, isPrimaryMember } = useHouseholdMembers();
    await refresh();

    expect(isPrimaryMember(members.value[0])).toBe(true);
    expect(isPrimaryMember(members.value[1])).toBe(false);
  });

  test("reads the manager flag of this household's membership", async () => {
    const { members, refresh, canManageHousehold } = useHouseholdMembers();
    await refresh();

    expect(canManageHousehold(members.value[0])).toBe(true);
    expect(canManageHousehold(members.value[1])).toBe(false);
  });

  test("inviting reloads the invitations and reports success", async () => {
    const { invite } = useHouseholdMembers();

    expect(await invite("pat@example.com")).toBe(true);

    expect(mocks.inviteMember).toHaveBeenCalledWith("pat@example.com");
    expect(mocks.getMemberInvitations).toHaveBeenCalled();
  });

  test("reports a failed invitation", async () => {
    mocks.inviteMember.mockResolvedValue({ data: null });
    expect(await useHouseholdMembers().invite("nobody@example.com")).toBe(false);
  });

  test("revoking an invitation reloads the invitations", async () => {
    await useHouseholdMembers().revoke("inv1");
    expect(mocks.revokeMemberInvitation).toHaveBeenCalledWith("inv1");
    expect(mocks.getMemberInvitations).toHaveBeenCalled();
  });

  test("removing a member reloads the members", async () => {
    await useHouseholdMembers().remove("u2");
    expect(mocks.removeMember).toHaveBeenCalledWith("u2");
    expect(mocks.fetchMembers).toHaveBeenCalled();
  });

  test("changing permissions in another household sends the manager flag with the user's own group flags", async () => {
    const { members, refresh, setPermissions } = useHouseholdMembers();
    await refresh();

    await setPermissions(members.value[1], true);

    expect(mocks.setMemberPermissions).toHaveBeenCalledWith({
      userId: "u2",
      canManageHousehold: true,
      canManage: true,
      canInvite: false,
      canOrganize: false,
    });
  });
});
