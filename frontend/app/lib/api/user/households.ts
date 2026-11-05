import { BaseCRUDAPIReadOnly } from "../base/base-clients";
import type { PaginationData } from "../types/non-generated";
import { route, type QueryValue } from "../base/route";
import type { UserOut } from "~/lib/api/types/user";
import type {
  HouseholdInDB,
  HouseholdStatistics,
  ReadHouseholdPreferences,
  SetPermissions,
  UpdateHouseholdPreferences,
  CreateInviteToken,
  ReadHouseholdMemberInvitation,
  ReadInviteToken,
  HouseholdSummary,
  HouseholdRecipeSummary,
} from "~/lib/api/types/household";

const prefix = "/api";

const routes = {
  households: `${prefix}/groups/households`,
  householdsSelf: `${prefix}/households/self`,
  members: `${prefix}/households/members`,
  membersId: (userId: string) => `${prefix}/households/members/${userId}`,
  memberInvitations: `${prefix}/households/member-invitations`,
  memberInvitationsId: (id: string) => `${prefix}/households/member-invitations/${id}`,
  permissions: `${prefix}/households/permissions`,

  preferences: `${prefix}/households/preferences`,
  statistics: `${prefix}/households/statistics`,
  invitation: `${prefix}/households/invitations`,

  householdsId: (id: string | number) => `${prefix}/groups/households/${id}`,
  householdsSelfRecipesSlug: (recipeSlug: string) => `${prefix}/households/self/recipes/${recipeSlug}`,
};

/** The query parameter that selects the household to act on; without it the user's primary household is used */
function householdQuery(householdId?: string) {
  return householdId ? { householdId } : null;
}

export class HouseholdAPI extends BaseCRUDAPIReadOnly<HouseholdSummary> {
  baseRoute = routes.households;
  itemRoute = routes.householdsId;
  /** Returns the Household Data for the Current User
   */
  async getCurrentUserHousehold() {
    return await this.requests.get<HouseholdInDB>(routes.householdsSelf);
  }

  async getCurrentUserHouseholdRecipe(recipeSlug: string) {
    return await this.requests.get<HouseholdRecipeSummary>(routes.householdsSelfRecipesSlug(recipeSlug));
  }

  async setPreferences(payload: UpdateHouseholdPreferences) {
    // TODO: This should probably be a patch request, which isn't offered by the API currently
    return await this.requests.put<ReadHouseholdPreferences, UpdateHouseholdPreferences>(routes.preferences, payload);
  }

  async createInvitation(payload: CreateInviteToken) {
    return await this.requests.post<ReadInviteToken>(routes.invitation, payload);
  }

  async fetchMembers(page = 1, perPage = -1, params = {} as Record<string, QueryValue>) {
    return await this.requests.get<PaginationData<UserOut>>(routes.members, { page, perPage, ...params });
  }

  /** @param householdId the household to act on; defaults to the user's primary household */
  async setMemberPermissions(payload: SetPermissions, householdId?: string) {
    // TODO: This should probably be a patch request, which isn't offered by the API currently
    return await this.requests.put<UserOut, SetPermissions>(route(routes.permissions, householdQuery(householdId)), payload);
  }

  /** Pending invitations of existing users to join the household */
  async getMemberInvitations(householdId?: string) {
    return await this.requests.get<ReadHouseholdMemberInvitation[]>(route(routes.memberInvitations, householdQuery(householdId)));
  }

  /** Invites an existing user of the same group, by email address */
  async inviteMember(email: string, householdId?: string) {
    return await this.requests.post<ReadHouseholdMemberInvitation>(
      route(routes.memberInvitations, householdQuery(householdId)),
      { email },
    );
  }

  async revokeMemberInvitation(invitationId: string, householdId?: string) {
    return await this.requests.delete<ReadHouseholdMemberInvitation>(
      route(routes.memberInvitationsId(invitationId), householdQuery(householdId)),
    );
  }

  /** Removes a user from the household; users can't be removed from their primary household */
  async removeMember(userId: string, householdId?: string) {
    return await this.requests.delete(route(routes.membersId(userId), householdQuery(householdId)));
  }

  async statistics() {
    return await this.requests.get<HouseholdStatistics>(routes.statistics);
  }
}
