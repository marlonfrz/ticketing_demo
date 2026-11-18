import client from "../../../api/client";
import type { ApiSchema, EntityId } from "../../../types/api";
import type {
  EventSession,
  EventSessionCreate,
  EventSessionUpdate,
} from "../../../types/domain";

export const getEventSessionsRequest = async (eventId: EntityId) => {
  const { data } = await client.get<EventSession[]>(`/events/${eventId}/sessions`);
  return data;
};

export const createEventSessionRequest = async (eventId: EntityId, payload: EventSessionCreate) => {
  const { data } = await client.post<EventSession>(`/events/${eventId}/sessions`, payload);
  return data;
};

export const updateEventSessionRequest = async (sessionId: EntityId, payload: EventSessionUpdate) => {
  const { data } = await client.put<EventSession>(`/event-sessions/${sessionId}`, payload);
  return data;
};

export const duplicateEventSessionRequest = async (sessionId: EntityId) => {
  const { data } = await client.post<EventSession>(`/event-sessions/${sessionId}/duplicate`);
  return data;
};

export const publishEventSessionRequest = async (sessionId: EntityId) => {
  const { data } = await client.post<EventSession>(`/event-sessions/${sessionId}/publish`);
  return data;
};

export const publishAllEventSessionsRequest = async (eventId: EntityId) => {
  const { data } = await client.post<ApiSchema<"StatusActionResponse">>(`/events/${eventId}/sessions/publish`);
  return data;
};

export const unpublishEventSessionRequest = async (sessionId: EntityId) => {
  const { data } = await client.post<EventSession>(`/event-sessions/${sessionId}/unpublish`);
  return data;
};

export const finishEventSessionRequest = async (sessionId: EntityId) => {
  const { data } = await client.post<EventSession>(`/event-sessions/${sessionId}/finish`);
  return data;
};

export const submitEventSessionReviewRequest = async (sessionId: EntityId) => {
  const { data } = await client.post<ApiSchema<"StatusActionResponse">>(`/event-sessions/${sessionId}/submit-review`);
  return data;
};

export const submitAllEventSessionsReviewRequest = async (eventId: EntityId) => {
  const { data } = await client.post<ApiSchema<"StatusActionResponse">>(`/events/${eventId}/sessions/submit-review`);
  return data;
};

export const deleteEventSessionRequest = async (sessionId: EntityId) => {
  const { data } = await client.delete<ApiSchema<"StatusActionResponse">>(`/event-sessions/${sessionId}`);
  return data;
};
