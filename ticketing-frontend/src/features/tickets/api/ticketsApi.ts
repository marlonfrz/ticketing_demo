import client from "../../../api/client";
import type { EntityId } from "../../../types/api";
import type { Order } from "../../../types/domain";

export const getMyOrdersRequest = async () => {
  const { data } = await client.get<Order[]>("/orders/my-orders");
  return data;
};

export const downloadOrderTicketsPdfRequest = async (
  orderId: EntityId
): Promise<Blob> => {
  const { data } = await client.get<Blob>(`/tickets/order/${orderId}/pdf`, {
    responseType: "blob",
  });
  return data;
};
