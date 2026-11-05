import { beforeEach, describe, expect, test, vi } from "vitest";
import { scopeToHousehold } from "./household-scope";
import type { ApiRequestInstance } from "~/lib/api/types/non-generated";

const requests = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
};
const base = requests as unknown as ApiRequestInstance;

beforeEach(() => vi.clearAllMocks());

describe("scopeToHousehold", () => {
  test("leaves the requests alone without a household", () => {
    expect(scopeToHousehold(base, null)).toBe(base);
    expect(scopeToHousehold(base, undefined)).toBe(base);
  });

  test("adds the household to the query of every kind of request", async () => {
    const scoped = scopeToHousehold(base, "h2");

    await scoped.get("/api/x", { page: 1 });
    expect(requests.get).toHaveBeenCalledWith("/api/x", { page: 1, householdId: "h2" }, undefined);

    await scoped.post("/api/x", { a: 1 });
    await scoped.put("/api/x", { a: 1 });
    await scoped.patch("/api/x", { a: 1 });
    for (const method of [requests.post, requests.put, requests.patch]) {
      expect(method).toHaveBeenCalledWith("/api/x", { a: 1 }, { params: { householdId: "h2" } });
    }

    await scoped.delete("/api/x");
    expect(requests.delete).toHaveBeenCalledWith("/api/x", { params: { householdId: "h2" } });
  });

  test("keeps other request config", async () => {
    const scoped = scopeToHousehold(base, "h2");

    await scoped.post("/api/x", {}, { headers: { a: "b" }, params: { q: 1 } });

    expect(requests.post).toHaveBeenCalledWith("/api/x", {}, { headers: { a: "b" }, params: { q: 1, householdId: "h2" } });
  });

  test("doesn't override a household the request already names", async () => {
    const scoped = scopeToHousehold(base, "h2");

    await scoped.delete("/api/x?householdId=h3");
    await scoped.get("/api/x", { householdId: "h3" });

    expect(requests.delete).toHaveBeenCalledWith("/api/x?householdId=h3", undefined);
    expect(requests.get).toHaveBeenCalledWith("/api/x", { householdId: "h3" }, undefined);
  });
});
