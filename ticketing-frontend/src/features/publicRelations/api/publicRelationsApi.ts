import client from "../../../api/client";
import type { ApiSchema, EntityId } from "../../../types/api";

export const getPublicRelationsRegisterInfoRequest = async (eventId: EntityId) => {
  const { data } = await client.get<ApiSchema<"PublicRelationsRegisterInfoResponse">>(`/events/${eventId}/public-relations/register-info`);
  return data;
};

export const registerPublicRelationsRequest = async (eventId: EntityId, payload: ApiSchema<"PublicRelationsRegisterRequest">) => {
  const { data } = await client.post<ApiSchema<"PublicRelationsRegisterResponse">>(`/events/${eventId}/public-relations/register`, payload);
  return data;
};

export const getPublicRelationsSummaryRequest = async (eventId: EntityId) => {
  const { data } = await client.get<ApiSchema<"PublicRelationsSummaryResponse">[]>(`/events/${eventId}/public-relations`);
  return data;
};
