import type { components } from "./api.generated";

export type ApiSchema<Name extends keyof components["schemas"]> =
  components["schemas"][Name];

export type EntityId = string;
export type ApiScope = "admin" | "promoter";

export type PaginationQuery = {
  page?: number;
  q?: string;
};
