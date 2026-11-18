import client from "../../../api/client";
import type { ApiSchema, EntityId } from "../../../types/api";

export const createReservationWithOrderRequest = async (
  eventId: EntityId,
  items: ApiSchema<"ReservationItemCreate">[],
  customer: ApiSchema<"ReservationCustomerCreate"> | null = null,
  publicRelationsCode: string | null = null
) => {
  const { data } = await client.post<ApiSchema<"ReservationWithOrderResponse">>(`/events/${eventId}/reservations/with-order`, {
    items,
    customer,
    public_relations_code: publicRelationsCode,
  });

  return data;
};
