import client from "../../../api/client";
import type { EntityId } from "../../../types/api";

export type SalesTicketOption = {
  id: EntityId;
  sale_group_id?: EntityId | null;
  name: string;
  description: string | null;
  price: string;
  currency: string;
  status: string;
  sale_starts_at: string | null;
  sale_ends_at: string | null;
  sale_unlocked_at: string | null;
  display_order: number | null;
  sale_order: number | null;
  max_per_purchase: number;
  max_selectable_quantity: number;
  available_quantity: number;
  availability_status: string;
  is_low_stock: boolean;
  sale_group_strategy?: string | null;
};

export type SalesOptionItem =
  | {
      type: "ticket_type";
      display_order: number | null;
      ticket_type: SalesTicketOption;
    }
  | {
      type: "sale_group";
      id: EntityId;
      name: string;
      strategy: string;
      display_order: number | null;
      sale_starts_at: string | null;
      sale_ends_at: string | null;
      ticket_types: SalesTicketOption[];
    };

export type SalesOptionsResponse = {
  event_id: EntityId;
  session_id: EntityId | null;
  items: SalesOptionItem[];
};

export const getEventSalesOptionsRequest = async (eventId: EntityId, sessionId: EntityId | null = null) => {
  const { data } = await client.get<SalesOptionsResponse>(`/events/${eventId}/sales-options`, {
    params: sessionId ? { session_id: sessionId } : {},
  });
  return data;
};
