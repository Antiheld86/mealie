import { beforeEach, describe, expect, test, vi } from "vitest";
import { AdminUsersApi } from "./admin/admin-users";
import { HouseholdAPI } from "./user/households";
import { UserApi } from "./user/users";
import type { ApiRequestInstance } from "~/lib/api/types/non-generated";

const requests = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("HouseholdAPI memberships", () => {
  const api = new HouseholdAPI(requests as unknown as ApiRequestInstance);

  test("lists pending invitations of the selected household", async () => {
    await api.getMemberInvitations("h2");
    expect(requests.get).toHaveBeenCalledWith("/api/households/member-invitations?householdId=h2");
  });

  test("lists pending invitations of the primary household when none is selected", async () => {
    await api.getMemberInvitations();
    expect(requests.get).toHaveBeenCalledWith("/api/households/member-invitations");
  });

  test("invites a user by email to the selected household", async () => {
    await api.inviteMember("user@example.com", "h2");
    expect(requests.post).toHaveBeenCalledWith("/api/households/member-invitations?householdId=h2", {
      email: "user@example.com",
    });
  });

  test("revokes an invitation", async () => {
    await api.revokeMemberInvitation("inv1", "h2");
    expect(requests.delete).toHaveBeenCalledWith("/api/households/member-invitations/inv1?householdId=h2");
  });

  test("removes a member from the selected household", async () => {
    await api.removeMember("u1", "h2");
    expect(requests.delete).toHaveBeenCalledWith("/api/households/members/u1?householdId=h2");
  });

  test("changes member permissions in the selected household", async () => {
    const payload = { userId: "u1", canManageHousehold: true, canManage: false, canInvite: false, canOrganize: false };
    await api.setMemberPermissions(payload, "h2");
    expect(requests.put).toHaveBeenCalledWith("/api/households/permissions?householdId=h2", payload);
  });
});

describe("UserApi household memberships", () => {
  const api = new UserApi(requests as unknown as ApiRequestInstance);

  test("lists, accepts and declines invitations", async () => {
    await api.getHouseholdInvitations();
    expect(requests.get).toHaveBeenCalledWith("/api/users/self/household-invitations");

    await api.acceptHouseholdInvitation("inv1");
    expect(requests.post).toHaveBeenCalledWith("/api/users/self/household-invitations/inv1/accept", {});

    await api.declineHouseholdInvitation("inv1");
    expect(requests.post).toHaveBeenCalledWith("/api/users/self/household-invitations/inv1/decline", {});
  });

  test("leaves a household", async () => {
    await api.leaveHousehold("h2");
    expect(requests.post).toHaveBeenCalledWith("/api/users/self/households/h2/leave", {});
  });
});

describe("AdminUsersApi households", () => {
  const api = new AdminUsersApi(requests as unknown as ApiRequestInstance);

  test("reads and replaces the households of a user", async () => {
    await api.getHouseholds("u1");
    expect(requests.get).toHaveBeenCalledWith("/api/admin/users/u1/households");

    const payload = { primaryHouseholdId: "h1", households: [{ householdId: "h1", canManageHousehold: false }] };
    await api.setHouseholds("u1", payload);
    expect(requests.put).toHaveBeenCalledWith("/api/admin/users/u1/households", payload);
  });
});
