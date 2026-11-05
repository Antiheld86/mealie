import { canManageAnyHousehold } from "~/lib/user/household-permissions";

const { user } = useMealieAuth();
export default defineNuxtRouteMiddleware(() => {
  // If the user is not allowed to manage any of their households redirect to the home page
  if (!canManageAnyHousehold(user.value)) {
    return navigateTo("/");
  }
});
