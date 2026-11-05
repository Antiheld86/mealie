import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ref } from "vue";
import type { UserOut } from "~/lib/api/types/user";

const user = ref<Partial<UserOut> | null>(null);
const navigateTo = vi.fn((to: unknown) => to);

describe("can-manage-household-only middleware", () => {
  beforeEach(() => {
    vi.resetModules();
    navigateTo.mockClear();
    vi.stubGlobal("defineNuxtRouteMiddleware", (fn: unknown) => fn);
    vi.stubGlobal("useMealieAuth", () => ({ user }));
    vi.stubGlobal("navigateTo", navigateTo);
  });

  afterEach(() => vi.unstubAllGlobals());

  async function run() {
    const middleware = (await import("../can-manage-household-only")).default as unknown as () => unknown;
    return middleware();
  }

  test("lets through someone who manages their primary household", async () => {
    user.value = { canManageHousehold: true, households: [] };
    expect(await run()).toBeUndefined();
  });

  test("lets through someone who only manages another household they belong to", async () => {
    user.value = {
      canManageHousehold: false,
      households: [
        { householdId: "h1", householdName: "Home", householdSlug: "home", isPrimary: true, canManageHousehold: false },
        { householdId: "h2", householdName: "Cabin", householdSlug: "cabin", isPrimary: false, canManageHousehold: true },
      ],
    };
    expect(await run()).toBeUndefined();
  });

  test("sends everyone else to the home page", async () => {
    user.value = {
      canManageHousehold: false,
      households: [
        { householdId: "h1", householdName: "Home", householdSlug: "home", isPrimary: true, canManageHousehold: false },
      ],
    };
    expect(await run()).toBe("/");
    expect(navigateTo).toHaveBeenCalledWith("/");
  });
});
