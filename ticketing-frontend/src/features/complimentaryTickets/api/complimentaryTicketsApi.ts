import client from "../../../api/client";
import type { ApiSchema, EntityId } from "../../../types/api";

export const getComplimentaryTicketsSummaryRequest = async (eventId: EntityId, sessionId: EntityId | null) => {
  const { data } = await client.get<ApiSchema<"ComplimentaryTicketSummaryResponse">>(`/events/${eventId}/complimentary-tickets`, {
    params: sessionId ? { session_id: sessionId } : {},
  });
  return data;
};

export const generateComplimentaryTicketsRequest = async (eventId: EntityId, payload: ApiSchema<"ComplimentaryTicketCreateRequest">) => {
  const { data } = await client.post<ApiSchema<"ComplimentaryTicketBatchResponse">>(
    `/events/${eventId}/complimentary-tickets`,
    payload
  );
  return data;
};

export const downloadComplimentaryTicketsPdfRequest = async (eventId: EntityId, orderId: EntityId, sessionId: EntityId | null): Promise<Blob> => {
  const { data } = await client.get<Blob>(
    `/events/${eventId}/complimentary-tickets/orders/${orderId}/pdf`,
    {
      params: sessionId ? { session_id: sessionId } : {},
      responseType: "blob",
    }
  );
  return data;
};
