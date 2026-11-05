import type { AxiosRequestConfig } from "axios";
import type { ApiRequestInstance } from "~/lib/api/types/non-generated";

/**
 * Wraps API requests so that every call acts on the given household, by adding `householdId` to its query.
 * Household management routes act on the user's primary household unless told otherwise. Without a household
 * the requests are returned as they are. A request that already names a household keeps it.
 */
export function scopeToHousehold(requests: ApiRequestInstance, householdId?: string | null): ApiRequestInstance {
  if (!householdId) {
    return requests;
  }

  const namesHousehold = (url: string) => /[?&]householdId=/.test(url);

  function scope(url: string, config?: AxiosRequestConfig): AxiosRequestConfig | undefined {
    if (namesHousehold(url) || config?.params?.householdId) {
      return config;
    }
    return { ...config, params: { ...config?.params, householdId } };
  }

  return {
    get: (url, params, config) => {
      const query = (params ?? {}) as Record<string, unknown>;
      return requests.get(url, namesHousehold(url) || query.householdId ? params : { ...query, householdId }, config);
    },
    post: (url, data, config) => requests.post(url, data, scope(url, config)),
    put: (url, data, config) => requests.put(url, data, scope(url, config)),
    patch: (url, data, config) => requests.patch(url, data, scope(url, config)),
    delete: (url, config) => requests.delete(url, scope(url, config)),
  };
}
