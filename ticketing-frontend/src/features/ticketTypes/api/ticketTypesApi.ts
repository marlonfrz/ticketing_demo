import client from "../../../api/client";
import type { ApiSchema, EntityId } from "../../../types/api";
import type { TicketType, TicketTypeCreate, TicketTypeUpdate } from "../../../types/domain";

export const getTicketTypesByEventRequest = async (eventId: EntityId, sessionId: EntityId | null = null) => {
  const { data } = await client.get<TicketType[]>(`/events/${eventId}/ticket-types`, {
    params: sessionId ? { session_id: sessionId } : {},
  });
  return data;
};

export const createTicketTypeRequest = async (eventId: EntityId, payload: TicketTypeCreate) => {
  const { data } = await client.post<TicketType>(`/events/${eventId}/ticket-types`, payload);
  return data;
};

export const updateTicketTypeRequest = async (ticketTypeId: EntityId, payload: TicketTypeUpdate) => {
  const { data } = await client.put<TicketType>(`/ticket-types/${ticketTypeId}`, payload);
  return data;
};

export const deleteTicketTypeRequest = async (ticketTypeId: EntityId) => {
  const { data } = await client.delete<ApiSchema<"StatusActionResponse">>(`/ticket-types/${ticketTypeId}`);
  return data;
};

export const publishTicketTypeRequest = async (ticketTypeId: EntityId) => {
  const { data } = await client.post<TicketType>(`/ticket-types/${ticketTypeId}/publish`);
  return data;
};
