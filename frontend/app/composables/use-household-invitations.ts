import { useUserApi } from "~/composables/api";
import type { ReadHouseholdMemberInvitation } from "~/lib/api/types/household";

/**
 * The signed-in user's invitations to join other households, and joining or leaving households.
 * The user's households are part of their session, so it's reloaded whenever they change.
 */
export function useHouseholdInvitations() {
  const api = useUserApi();
  const auth = useMealieAuth();

  const invitations = ref<ReadHouseholdMemberInvitation[]>([]);

  async function refresh() {
    const { data } = await api.users.getHouseholdInvitations();
    if (data) {
      invitations.value = data;
    }
  }

  /** Each returns whether the server accepted the change */
  async function accept(invitationId: string) {
    const { data } = await api.users.acceptHouseholdInvitation(invitationId);
    if (data) {
      await auth.getSession();
    }
    await refresh();
    return !!data;
  }

  async function decline(invitationId: string) {
    const { data } = await api.users.declineHouseholdInvitation(invitationId);
    await refresh();
    return !!data;
  }

  async function leave(householdId: string) {
    const { data } = await api.users.leaveHousehold(householdId);
    if (data) {
      await auth.getSession();
    }
    return !!data;
  }

  return { invitations, refresh, accept, decline, leave };
}
