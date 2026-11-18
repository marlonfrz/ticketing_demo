import client from "../../../api/client";
import type { ApiSchema, EntityId } from "../../../types/api";
import type { Event, EventCreate, EventUpdate } from "../../../types/domain";

export const getMyEventsRequest = async () => {
  const { data } = await client.get<Event[]>("/events/me");
  return data;
};

export const createEventRequest = async (payload: EventCreate) => {
  const { data } = await client.post<Event>("/events", payload);
  return data;
};

export const updateEventRequest = async (eventId: EntityId, payload: EventUpdate) => {
  const { data } = await client.put<Event>(`/events/${eventId}`, payload);
  return data;
};

export const uploadEventImageRequest = async (eventId: EntityId, imageFile: File) => {
  const formData = new FormData();
  formData.append("image", imageFile);

  const { data } = await client.post<Event>(`/events/${eventId}/image`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const publishEventRequest = async (eventId: EntityId) => {
  const { data } = await client.post<ApiSchema<"StatusActionResponse">>(`/events/${eventId}/publish`);
  return data;
};

export const submitEventReviewRequest = async (eventId: EntityId) => {
  const { data } = await client.post<ApiSchema<"StatusActionResponse">>(`/events/${eventId}/submit-review`);
  return data;
};

export const unpublishEventRequest = async (eventId: EntityId) => {
  const { data } = await client.post<ApiSchema<"StatusActionResponse">>(`/events/${eventId}/unpublish`);
  return data;
};

export const finishEventRequest = async (eventId: EntityId) => {
  const { data } = await client.post<ApiSchema<"StatusActionResponse">>(`/events/${eventId}/finish`);
  return data;
};

export const deleteEventRequest = async (eventId: EntityId) => {
  const { data } = await client.delete<ApiSchema<"StatusActionResponse">>(`/events/${eventId}`);
  return data;
};
