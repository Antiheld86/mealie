import { useHouseholdContext } from "~/composables/use-household-context";
import type { ReadHouseholdMemberInvitation } from "~/lib/api/types/household";
import type { UserOut } from "~/lib/api/types/user";

/**
 * The members of the household a page acts on (see `useHouseholdContext`): who belongs to it, who is invited,
 * and what each member may do there. Members include users whose primary household is a different one.
 */
export function useHouseholdMembers() {
  const { householdId, api } = useHouseholdContext();

  const members = ref<UserOut[]>([]);
  const invitations = ref<ReadHouseholdMemberInvitation[]>([]);

  function membership(user: UserOut) {
    return user.households?.find(household => household.householdId === householdId.value);
  }

  /** Members whose primary household this is can't be removed from it */
  function isPrimaryMember(user: UserOut) {
    return !!membership(user)?.isPrimary;
  }

  function canManageHousehold(user: UserOut) {
    return !!membership(user)?.canManageHousehold;
  }

  async function refreshMembers() {
    const { data } = await api.value.households.fetchMembers();
    if (data) {
      members.value = data.items;
    }
  }

  async function refreshInvitations() {
    const { data } = await api.value.households.getMemberInvitations();
    if (data) {
      invitations.value = data;
    }
  }

  async function refresh() {
    await Promise.all([refreshMembers(), refreshInvitations()]);
  }

  /** Invites an existing user of the group by email. Returns whether the invitation was created. */
  async function invite(email: string) {
    const { data } = await api.value.households.inviteMember(email);
    if (data) {
      await refreshInvitations();
    }
    return !!data;
  }

  async function revoke(invitationId: string) {
    const { data } = await api.value.households.revokeMemberInvitation(invitationId);
    if (data) {
      await refreshInvitations();
    }
  }

  async function remove(userId: string) {
    const { data } = await api.value.households.removeMember(userId);
    if (data) {
      await refreshMembers();
    }
  }

  /**
   * Sets whether the member can manage this household. The group-level permissions belong to the user, not to
   * the household, so they're sent as they are and the server only applies them in the user's primary household.
   */
  async function setPermissions(user: UserOut, canManageHousehold: boolean) {
    await api.value.households.setMemberPermissions({
      userId: user.id,
      canManageHousehold,
      canManage: user.canManage,
      canInvite: user.canInvite,
      canOrganize: user.canOrganize,
    });
  }

  watch(householdId, refresh);

  return { members, invitations, refresh, isPrimaryMember, canManageHousehold, invite, revoke, remove, setPermissions };
}
