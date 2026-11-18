import client from "../../../api/client";
import type { ApiSchema, EntityId, PaginationQuery } from "../../../types/api";

export type AdminUserSearchQuery = PaginationQuery & { role?: string };
export type AdminEventSearchQuery = PaginationQuery & { eventStatus?: string };
export type ReviewActionPayload = Partial<
  ApiSchema<"AdminEventFeeRequest"> & ApiSchema<"AdminReviewReasonRequest">
>;
export type SupportOrder = {
  id: EntityId;
  status: string;
  total_amount: string;
  currency: string;
  created_at: string;
  event: { id: EntityId; title: string } | null;
  payment: {
    status: string;
    provider: string;
    provider_order_id: string | null;
    provider_payment_id: string | null;
  } | null;
  customer: {
    full_name: string | null;
    email: string | null;
    phone: string | null;
    source: "guest" | "account";
  };
  tickets: Array<{
    id: EntityId;
    ticket_code: string;
    ticket_type_name: string | null;
    session: {
      id: EntityId;
      location_name: string;
      starts_at: string;
    } | null;
    status: string;
    source: string;
    is_valid: boolean;
  }>;
};

export const getAdminDashboardRequest = async () => {
  const { data } = await client.get<ApiSchema<"AdminDashboardResponse">>("/admin/dashboard");
  return data;
};

export const getAdminUsersRequest = async () => {
  const { data } = await client.get<ApiSchema<"AdminUserItemResponse">[]>("/admin/users");
  return data;
};

export const searchAdminUsersRequest = async ({ q, role, page = 1 }: AdminUserSearchQuery) => {
  const { data } = await client.get<ApiSchema<"AdminPaginatedUsersResponse">>("/admin/users/search", {
    params: {
      q: q || undefined,
      role: role || undefined,
      page,
      page_size: 10,
    },
  });
  return data;
};

export const searchAdminEventsRequest = async ({ q, eventStatus, page = 1 }: AdminEventSearchQuery) => {
  const { data } = await client.get<ApiSchema<"AdminPaginatedEventsResponse">>("/admin/events/search", {
    params: {
      q: q || undefined,
      event_status: eventStatus || undefined,
      page,
      page_size: 10,
    },
  });
  return data;
};

export const getAdminPromoterEventsRequest = async (promoterId: EntityId) => {
  const { data } = await client.get<ApiSchema<"AdminPromoterEventsResponse">>(`/admin/promoters/${promoterId}/events`);
  return data;
};

export const createAdminPromoterRequest = async (payload: ApiSchema<"AdminCreateUserRequest">) => {
  const { data } = await client.post<ApiSchema<"AdminCreateUserResponse">>("/admin/users/promoters", payload);
  return data;
};

export const createAdminUserRequest = async (payload: ApiSchema<"AdminCreateUserRequest">) => {
  const { data } = await client.post<ApiSchema<"AdminCreateUserResponse">>("/admin/users/admins", payload);
  return data;
};

export const searchSupportOrdersRequest = async (query: string) => {
  const { data } = await client.get<SupportOrder[]>("/admin/orders/support", {
    params: { q: query },
  });
  return data;
};

export const updateSupportOrderContactRequest = async (orderId: EntityId, payload: ApiSchema<"AdminOrderContactUpdateRequest">) => {
  const { data } = await client.put<SupportOrder>(`/admin/orders/${orderId}/contact`, payload);
  return data;
};

export const resendSupportOrderTicketsRequest = async (orderId: EntityId) => {
  const { data } = await client.post<ApiSchema<"TicketSendResponse">>(`/admin/orders/${orderId}/resend-tickets`);
  return data;
};

export const getEventReviewQueueRequest = async () => {
  const { data } = await client.get<ApiSchema<"AdminEventItemResponse">[]>("/admin/events/review-queue");
  return data;
};

export const approveEventReviewRequest = async (eventId: EntityId, payload?: ReviewActionPayload) => {
  const { data } = await client.post<ApiSchema<"StatusActionResponse">>(`/admin/events/${eventId}/approve-review`, payload);
  return data;
};

export const updateEventFeeRequest = async (eventId: EntityId, payload: ApiSchema<"AdminEventFeeRequest">) => {
  const { data } = await client.put<ApiSchema<"AdminEventItemResponse">>(`/admin/events/${eventId}/fee`, payload);
  return data;
};

export const requestEventChangesRequest = async (eventId: EntityId, _payload?: ReviewActionPayload) => {
  const { data } = await client.post<ApiSchema<"StatusActionResponse">>(`/admin/events/${eventId}/request-changes`);
  return data;
};

export const cancelEventReviewRequest = async (eventId: EntityId, _payload?: ReviewActionPayload) => {
  const { data } = await client.post<ApiSchema<"StatusActionResponse">>(`/admin/events/${eventId}/cancel-review`);
  return data;
};

export const approveEventSessionReviewRequest = async (sessionId: EntityId, payload?: ReviewActionPayload) => {
  const { data } = await client.post<ApiSchema<"StatusActionResponse">>(`/admin/event-sessions/${sessionId}/approve-review`, payload);
  return data;
};

export const requestEventSessionChangesRequest = async (sessionId: EntityId, payload?: ReviewActionPayload) => {
  const { data } = await client.post<ApiSchema<"StatusActionResponse">>(`/admin/event-sessions/${sessionId}/request-changes`, payload);
  return data;
};

export const getValidationQuotaRequestsAdminRequest = async (requestStatus?: string) => {
  const { data } = await client.get<ApiSchema<"ValidationQuotaRequestResponse">[]>("/admin/validation-quota-requests", {
    params: requestStatus ? { request_status: requestStatus } : undefined,
  });
  return data;
};

export const reviewValidationQuotaRequestAdminRequest = async (
  requestId: EntityId,
  payload: ApiSchema<"ValidationQuotaRequestReview">
) => {
  const { data } = await client.post<ApiSchema<"ValidationQuotaRequestResponse">>(
    `/admin/validation-quota-requests/${requestId}/review`,
    payload
  );
  return data;
};
