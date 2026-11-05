import { BaseCRUDAPI } from "../base/base-clients";
import type { ReadHouseholdMemberInvitation } from "~/lib/api/types/household";
import type {
  ChangePassword,
  DeleteTokenResponse,
  LongLiveTokenIn,
  LongLiveTokenOut,
  ResetPassword,
  UserBase,
  UserIn,
  UserOut,
  UserRatingOut,
  UserRatingSummary,
} from "~/lib/api/types/user";

export interface UserRatingsSummaries {
  ratings: UserRatingSummary[];
}

export interface UserRatingsOut {
  ratings: UserRatingOut[];
}

const prefix = "/api";

const routes = {
  usersSelf: `${prefix}/users/self`,
  householdInvitations: `${prefix}/users/self/household-invitations`,
  householdInvitationsId: (id: string) => `${prefix}/users/self/household-invitations/${id}`,
  usersSelfHouseholdsIdLeave: (id: string) => `${prefix}/users/self/households/${id}/leave`,
  ratingsSelf: `${prefix}/users/self/ratings`,
  passwordReset: `${prefix}/users/reset-password`,
  passwordChange: `${prefix}/users/password`,
  users: `${prefix}/users`,

  usersIdImage: (id: string) => `${prefix}/users/${id}/image`,
  usersIdResetPassword: (id: string) => `${prefix}/users/${id}/reset-password`,
  usersId: (id: string) => `${prefix}/users/${id}`,
  usersIdFavorites: (id: string) => `${prefix}/users/${id}/favorites`,
  usersIdFavoritesSlug: (id: string, slug: string) => `${prefix}/users/${id}/favorites/${slug}`,
  usersIdRatings: (id: string) => `${prefix}/users/${id}/ratings`,
  usersIdRatingsSlug: (id: string, slug: string) => `${prefix}/users/${id}/ratings/${slug}`,
  usersSelfFavoritesId: (id: string) => `${prefix}/users/self/favorites/${id}`,
  usersSelfRatingsId: (id: string) => `${prefix}/users/self/ratings/${id}`,

  usersApiTokens: `${prefix}/users/api-tokens`,
  usersApiTokensTokenId: (token_id: string | number) => `${prefix}/users/api-tokens/${token_id}`,
};

export class UserApi extends BaseCRUDAPI<UserIn, UserOut, UserBase> {
  baseRoute: string = routes.users;
  itemRoute = (itemid: string) => routes.usersId(itemid);

  /** Pending invitations to join another household */
  async getHouseholdInvitations() {
    return await this.requests.get<ReadHouseholdMemberInvitation[]>(routes.householdInvitations);
  }

  async acceptHouseholdInvitation(invitationId: string) {
    return await this.requests.post<ReadHouseholdMemberInvitation>(
      `${routes.householdInvitationsId(invitationId)}/accept`,
      {},
    );
  }

  async declineHouseholdInvitation(invitationId: string) {
    return await this.requests.post<ReadHouseholdMemberInvitation>(
      `${routes.householdInvitationsId(invitationId)}/decline`,
      {},
    );
  }

  /** Leaves a household that isn't the user's primary one */
  async leaveHousehold(householdId: string) {
    return await this.requests.post(routes.usersSelfHouseholdsIdLeave(householdId), {});
  }

  async addFavorite(id: string, slug: string) {
    return await this.requests.post(routes.usersIdFavoritesSlug(id, slug), {});
  }

  async removeFavorite(id: string, slug: string) {
    return await this.requests.delete(routes.usersIdFavoritesSlug(id, slug));
  }

  async getFavorites(id: string) {
    return await this.requests.get<UserRatingsOut>(routes.usersIdFavorites(id));
  }

  async getSelfFavorites() {
    return await this.requests.get<UserRatingsSummaries>(routes.ratingsSelf);
  }

  async getRatings(id: string) {
    return await this.requests.get<UserRatingsOut>(routes.usersIdRatings(id));
  }

  async setRating(id: string, slug: string, rating: number | null, isFavorite: boolean | null) {
    return await this.requests.post(routes.usersIdRatingsSlug(id, slug), { rating, isFavorite });
  }

  async getSelfRatings() {
    return await this.requests.get<UserRatingsSummaries>(routes.ratingsSelf);
  }

  async changePassword(changePassword: ChangePassword) {
    return await this.requests.put(routes.passwordChange, changePassword);
  }

  async createAPIToken(tokenName: LongLiveTokenIn) {
    return await this.requests.post<LongLiveTokenOut>(routes.usersApiTokens, tokenName);
  }

  async deleteAPIToken(tokenId: number) {
    return await this.requests.delete<DeleteTokenResponse>(routes.usersApiTokensTokenId(tokenId));
  }

  userProfileImage(id: string) {
    if (!id || id === undefined) return;
    return `/api/users/${id}/image`;
  }

  async resetPassword(payload: ResetPassword) {
    return await this.requests.post(routes.passwordReset, payload);
  }
}
