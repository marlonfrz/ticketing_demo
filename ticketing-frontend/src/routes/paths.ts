export const ROUTES = {
  home: "/",
  login: "/login",
  register: "/register",
  forgotPassword: "/forgot-password",
  resetPassword: "/reset-password",
  changePassword: "/change-password",
  profile: "/profile",
  myTickets: "/my-tickets",
  organize: "/organizar",
  help: "/ayuda",
  faq: "/ayuda/preguntas-frecuentes",
  promoter: "/promoter",
  adminReviews: "/admin/reviews",
  adminUsers: "/admin/users",
  adminValidationRequests: "/admin/validation-requests",
  about: "/sobre-nosotros",
  contact: "/contacto",
  terms: "/legal/condiciones",
  privacy: "/legal/privacidad",
  cookies: "/legal/cookies",
  legalNotice: "/legal/aviso-legal",
  paymentSuccess: "/payment/success",
  paymentError: "/payment/error",
  paymentDemo: "/payment/demo",
  validatorActivate: "/validator/activate",
  validatorScan: "/validator/scan",
};

export const ROUTE_PATTERNS = {
  eventDetail: "/events/:eventId",
  publicRelationsRegister: "/events/:eventId/rrpp",
  eventManage: "/events/:eventId/manage",
  eventSessionManage: "/events/:eventId/manage/sessions/:sessionId",
  checkout: "/checkout/:orderId",
  adminPromoterEvents: "/admin/promoters/:promoterId/events",
  validationStationActivity: "/validation-stations/:stationId/activity",
};

export const ROUTE_PREFIXES = {
  validator: "/validator/",
};

export const routeTo = {
  eventDetail: (eventId: EntityId) => `/events/${eventId}`,
  publicRelationsRegister: (eventId: EntityId) => `/events/${eventId}/rrpp`,
  eventManage: (
    eventId: string | number,
    params: Record<string, string | number | null | undefined> = {}
  ) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        searchParams.set(key, String(value));
      }
    });
    const query = searchParams.toString();
    return `/events/${eventId}/manage${query ? `?${query}` : ""}`;
  },
  eventSessionManage: (eventId: EntityId, sessionId: EntityId) =>
    `/events/${eventId}/manage/sessions/${sessionId}`,
  checkout: (orderId: EntityId) => `/checkout/${orderId}`,
  adminPromoterEvents: (promoterId: EntityId) =>
    `/admin/promoters/${promoterId}/events`,
  validationStationActivity: (stationId: EntityId) =>
    `/validation-stations/${stationId}/activity`,
};
import type { EntityId } from "../types/api";
