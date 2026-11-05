import { BaseCRUDAPI } from "../base/base-clients";
import type {
  ForgotPassword,
  PasswordResetToken,
  UnlockResults,
  UserHouseholdMembershipOut,
  UserHouseholdMembershipsUpdate,
  UserIn,
  UserOut,
} from "~/lib/api/types/user";

const prefix = "/api";

const routes = {
  adminUsers: `${prefix}/admin/users`,
  adminUsersId: (tag: string) => `${prefix}/admin/users/${tag}`,
  adminResetLockedUsers: (force: boolean) => `${prefix}/admin/users/unlock?force=${force ? "true" : "false"}`,
  adminUsersIdHouseholds: (id: string) => `${prefix}/admin/users/${id}/households`,
  adminPasswordResetToken: `${prefix}/admin/users/password-reset-token`,
};

export class AdminUsersApi extends BaseCRUDAPI<UserIn, UserOut, UserOut> {
  baseRoute: string = routes.adminUsers;
  itemRoute = routes.adminUsersId;

  async unlockAllUsers(force = false) {
    return await this.requests.post<UnlockResults>(routes.adminResetLockedUsers(force), {});
  }

  async generatePasswordResetToken(payload: ForgotPassword) {
    return await this.requests.post<PasswordResetToken>(routes.adminPasswordResetToken, payload);
  }

  async getHouseholds(userId: string) {
    return await this.requests.get<UserHouseholdMembershipOut[]>(routes.adminUsersIdHouseholds(userId));
  }

  /** Replaces every household the user belongs to, including which one is their primary household */
  async setHouseholds(userId: string, payload: UserHouseholdMembershipsUpdate) {
    return await this.requests.put<UserHouseholdMembershipOut[], UserHouseholdMembershipsUpdate>(
      routes.adminUsersIdHouseholds(userId),
      payload,
    );
  }
}
