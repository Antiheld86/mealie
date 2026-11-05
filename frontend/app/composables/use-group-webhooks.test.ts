import { flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { useGroupWebhooks } from "./use-group-webhooks";

const homeGetAll = vi.fn();
const cabinGetAll = vi.fn();
const cabinCreateOne = vi.fn();

const context = vi.hoisted(() => ({
  householdId: null as unknown as Ref<string>,
  api: null as unknown as Ref<unknown>,
}));

vi.mock("~/composables/use-household-context", () => ({
  useHouseholdContext: () => context,
}));

function apiFor(getAll: typeof homeGetAll, createOne = vi.fn()) {
  return { groupWebhooks: { getAll, createOne } };
}

beforeEach(() => {
  vi.clearAllMocks();
  homeGetAll.mockResolvedValue({ data: { items: [{ id: "home-hook" }] } });
  cabinGetAll.mockResolvedValue({ data: { items: [{ id: "cabin-hook" }] } });
  cabinCreateOne.mockResolvedValue({ data: { id: "new" } });
  context.householdId = ref("h1");
  context.api = ref(apiFor(homeGetAll));

  vi.stubGlobal("useAsyncKey", () => "key");
  vi.stubGlobal("useAsyncData", (_key: string, fn: () => Promise<unknown>) => {
    const data = ref<unknown>(null);
    fn().then((result) => {
      data.value = result;
    });
    return { data };
  });
});

describe("useGroupWebhooks household", () => {
  test("loads the webhooks of the household in context", async () => {
    const { webhooks } = useGroupWebhooks();
    await flushPromises();

    expect(webhooks.value).toEqual([{ id: "home-hook" }]);
  });

  test("reloads the webhooks when another household is selected", async () => {
    const { webhooks } = useGroupWebhooks();
    await flushPromises();

    context.api.value = apiFor(cabinGetAll);
    context.householdId.value = "h2";
    await flushPromises();

    expect(cabinGetAll).toHaveBeenCalled();
    expect(webhooks.value).toEqual([{ id: "cabin-hook" }]);
  });

  test("creates webhooks in the household in context", async () => {
    const { actions } = useGroupWebhooks();
    context.api.value = apiFor(cabinGetAll, cabinCreateOne);
    context.householdId.value = "h2";

    await actions.createOne();

    expect(cabinCreateOne).toHaveBeenCalled();
  });
});
