import client from "../../../api/client";
import type { ApiSchema, EntityId } from "../../../types/api";
import type { SaleGroup, SaleGroupCreate, SaleGroupUpdate, TicketType } from "../../../types/domain";

export const getSaleGroupsByEventRequest = async (eventId: EntityId, sessionId: EntityId | null = null) => {
  const { data } = await client.get<SaleGroup[]>(`/events/${eventId}/sale-groups`, {
    params: sessionId ? { session_id: sessionId } : {},
  });
  return data;
};

export const createSaleGroupRequest = async (eventId: EntityId, payload: SaleGroupCreate) => {
  const { data } = await client.post<SaleGroup>(`/events/${eventId}/sale-groups`, payload);
  return data;
};

export const updateSaleGroupRequest = async (eventId: EntityId, saleGroupId: EntityId, payload: SaleGroupUpdate) => {
  const { data } = await client.put<SaleGroup>(
    `/events/${eventId}/sale-groups/${saleGroupId}`,
    payload
  );
  return data;
};

export const deleteSaleGroupRequest = async (eventId: EntityId, saleGroupId: EntityId) => {
  const { data } = await client.delete<ApiSchema<"StatusActionResponse">>(
    `/events/${eventId}/sale-groups/${saleGroupId}`
  );
  return data;
};

export const publishSaleGroupRequest = async (eventId: EntityId, saleGroupId: EntityId) => {
  const { data } = await client.post<SaleGroup>(
    `/events/${eventId}/sale-groups/${saleGroupId}/publish`
  );
  return data;
};

export const assignTicketTypeToSaleGroupRequest = async (
  eventId: EntityId,
  ticketTypeId: EntityId,
  payload: ApiSchema<"AssignTicketTypeToSaleGroupRequest">
) => {
  const { data } = await client.post<TicketType>(
    `/events/${eventId}/sale-groups/ticket-types/${ticketTypeId}/assign`,
    payload
  );

  return data;
};

export const removeTicketTypeFromSaleGroupRequest = async (
  eventId: EntityId,
  ticketTypeId: EntityId
) => {
  const { data } = await client.post<ApiSchema<"RemoveTicketTypeFromSaleGroupResponse">>(
    `/events/${eventId}/sale-groups/ticket-types/${ticketTypeId}/remove`
  );

  return data;
};
