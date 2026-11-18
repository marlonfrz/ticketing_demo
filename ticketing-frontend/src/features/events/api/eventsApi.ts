import client from "../../../api/client";
import type { EntityId } from "../../../types/api";
import type { ManagedEvent } from "../../../types/domain";

export const getManageEventByIdRequest = async (eventId: EntityId) => {
  const { data } = await client.get<ManagedEvent>(`/events/${eventId}/manage`);
  return data;
};
