import type { ApiSchema, EntityId } from "./api";

export type User = ApiSchema<"MeResponse">;
export type UserRole = string;
export type Event = ApiSchema<"EventResponse">;
export type EventCreate = ApiSchema<"EventCreate">;
export type EventUpdate = ApiSchema<"EventUpdate">;
export type EventSession = ApiSchema<"EventSessionResponse">;
export type EventSessionCreate = ApiSchema<"EventSessionCreate">;
export type EventSessionUpdate = ApiSchema<"EventSessionUpdate">;
export type TicketType = ApiSchema<"TicketTypeResponse">;
export type TicketTypeCreate = ApiSchema<"TicketTypeCreate">;
export type TicketTypeUpdate = ApiSchema<"TicketTypeUpdate">;
export type SaleGroup = ApiSchema<"TicketSaleGroupResponse">;
export type SaleGroupCreate = ApiSchema<"TicketSaleGroupCreate">;
export type SaleGroupUpdate = ApiSchema<"TicketSaleGroupUpdate">;
export type Order = ApiSchema<"OrderResponse">;
export type Ticket = ApiSchema<"TicketResponse">;
export type AdminEvent = ApiSchema<"AdminEventItemResponse">;
export type ValidationStation = ApiSchema<"ValidationStationResponse">;
export type ValidationManagement = ApiSchema<"ValidationSessionManagementResponse">;
export type ValidationActivity = ApiSchema<"ValidationStationActivityResponse">;

export type FinancialSummary = {
  currency: string;
  tickets_sold: number;
  gross_revenue: string | number;
  promoter_revenue: string | number;
  platform_revenue: string | number;
  tickets_revenue: string | number;
  management_fee_revenue: string | number;
  complimentary_tickets_total: number;
  complimentary_tickets_by_type: Array<{
    ticket_type_id: EntityId;
    ticket_type_name: string;
    quantity: number;
  }>;
};

export type ManagedEvent = Omit<Event, "financial_summary"> & {
  financial_summary?: FinancialSummary | null;
  sale_groups?: SaleGroup[];
  ticket_types?: TicketType[];
};
