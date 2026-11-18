import client from "../../../api/client";
import type { ApiSchema, ApiScope, EntityId } from "../../../types/api";

export type ValidationActivityQuery = {
  limit?: number;
  offset?: number;
  result?: string;
  ticket_code?: string;
};

export type StationValidationResult = Omit<
  ApiSchema<"TicketValidationResponse">,
  "ticket"
> & {
  ticket?: ApiSchema<"TicketResponse"> | null;
};

const managementBasePath = (scope: ApiScope, sessionId: EntityId) =>
  `/${scope}/event-sessions/${sessionId}/validation-stations`;

const quotaBasePath = (scope: ApiScope, sessionId: EntityId) =>
  `/${scope}/event-sessions/${sessionId}/validation-quota-requests`;

const stationActionPath = (scope: ApiScope, stationId: EntityId, action: "revoke" | "regenerate-link") =>
  `/${scope}/validation-stations/${stationId}/${action}`;

const stationActivityPath = (scope: ApiScope, stationId: EntityId) =>
  `/${scope}/validation-stations/${stationId}/activity`;

export const getValidationSessionManagementRequest = async (
  sessionId: EntityId,
  scope: ApiScope = "promoter"
) => {
  const { data } = await client.get<ApiSchema<"ValidationSessionManagementResponse">>(
    managementBasePath(scope, sessionId)
  );
  return data;
};

export const createValidationQuotaRequest = async (
  sessionId: EntityId,
  payload: ApiSchema<"ValidationQuotaRequestCreate">,
  scope: ApiScope = "promoter"
) => {
  const { data } = await client.post<ApiSchema<"ValidationQuotaRequestResponse">>(
    quotaBasePath(scope, sessionId),
    payload
  );
  return data;
};

export const createValidationStationRequest = async (
  sessionId: EntityId,
  payload: ApiSchema<"ValidationStationCreate">,
  scope: ApiScope = "promoter"
) => {
  const { data } = await client.post<ApiSchema<"ValidationStationLinkResponse">>(
    managementBasePath(scope, sessionId),
    payload
  );
  return data;
};

export const revokeValidationStationRequest = async (
  stationId: EntityId,
  scope: ApiScope = "promoter"
) => {
  const { data } = await client.post<ApiSchema<"ValidationStationResponse">>(
    stationActionPath(scope, stationId, "revoke")
  );
  return data;
};

export const regenerateValidationStationLinkRequest = async (
  stationId: EntityId,
  scope: ApiScope = "promoter"
) => {
  const { data } = await client.post<ApiSchema<"ValidationStationLinkResponse">>(
    stationActionPath(scope, stationId, "regenerate-link")
  );
  return data;
};

export const getValidationStationActivityRequest = async (
  stationId: EntityId,
  scope: ApiScope = "promoter",
  params: ValidationActivityQuery = {}
) => {
  const { data } = await client.get<ApiSchema<"ValidationStationActivityListResponse">>(stationActivityPath(scope, stationId), {
    params,
  });
  return data;
};

export const activateValidationStationRequest = async (payload: ApiSchema<"ValidationStationActivate">) => {
  const { data } = await client.post<ApiSchema<"ValidationStationSessionResponse">>("/validator-stations/activate", payload);
  return data;
};

export const getCurrentValidationStationRequest = async () => {
  const { data } = await client.get<ApiSchema<"ValidationStationSessionResponse">>("/validator-stations/me");
  return data;
};

export const validateTicketFromStationRequest = async (payload: ApiSchema<"ValidationStationScanRequest">) => {
  const { data } = await client.post<StationValidationResult>("/validator-stations/validate", payload);
  return data;
};

export const logoutValidationStationRequest = async () => {
  const { data } = await client.post<{ success: boolean }>("/validator-stations/logout");
  return data;
};

export const reportValidationStationIncidentRequest = async (payload: ApiSchema<"ValidationStationIncidentRequest">) => {
  const { data } = await client.post<ApiSchema<"ValidationStationActivityResponse">>("/validator-stations/incidents", payload);
  return data;
};
