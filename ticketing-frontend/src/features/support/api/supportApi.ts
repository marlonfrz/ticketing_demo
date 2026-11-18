import client from "../../../api/client";
import type { ApiSchema } from "../../../types/api";

export type OrganizerContactPayload = ApiSchema<"OrganizerContactRequest">;

export const sendOrganizerContactRequest = async (
  payload: OrganizerContactPayload
) => {
  const { data } = await client.post<ApiSchema<"ContactMessageResponse">>(
    "/contact/organizer",
    payload
  );
  return data;
};
