import client from "../../../api/client";
import type { ApiSchema, EntityId } from "../../../types/api";

export const createDemoCheckoutRequest = async (orderId: EntityId) => {
  const { data } = await client.post<ApiSchema<"DemoCheckoutResponse">>(
    `/payments/demo/checkout/${orderId}`,
    {},
    {
      headers: {
        "X-Checkout-Return-Origin": window.location.origin,
      },
    }
  );
  return data;
};

export const getCheckoutSummaryRequest = async (orderId: EntityId) => {
  const { data } = await client.get<ApiSchema<"CheckoutSummaryResponse">>(
    `/orders/${orderId}/checkout-summary`
  );
  return data;
};

export const confirmDemoSessionRequest = async (sessionId: string) => {
  const { data } = await client.post<ApiSchema<"PaymentResponse">>(
    `/payments/demo/confirm-session/${sessionId}`,
    {}
  );
  return data;
};

export const downloadCheckoutTicketsPdfRequest = async (orderId: EntityId): Promise<Blob> => {
  const { data } = await client.get<Blob>(`/tickets/order/${orderId}/pdf`, {
    responseType: "blob",
  });
  return data;
};
