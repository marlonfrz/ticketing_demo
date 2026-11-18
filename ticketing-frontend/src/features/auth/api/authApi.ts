import client from "../../../api/client";
import type { ApiSchema } from "../../../types/api";
import type { User } from "../../../types/domain";

export type LoginCredentials = { email: string; password: string };
export type RegisterPayload = ApiSchema<"UserCreate">;
export type ResetPasswordPayload = ApiSchema<"PasswordResetRequest">;
export type ChangePasswordPayload = ApiSchema<"PasswordChangeRequest">;

export const loginRequest = async ({ email, password }: LoginCredentials) => {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  const { data } = await client.post<ApiSchema<"TokenResponse">>("/auth/login", formData, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });

  return data;
};

export const registerRequest = async ({
  email,
  full_name,
  phone,
  country_code = "ES",
  password,
  accept_terms,
  accept_privacy,
  marketing_consent = false,
  registration_source = "registration",
}: RegisterPayload) => {
  const { data } = await client.post<ApiSchema<"UserResponse">>("/auth/register", {
    email,
    full_name,
    phone,
    country_code,
    password,
    accept_terms,
    accept_privacy,
    marketing_consent,
    registration_source,
  });

  return data;
};

export const getAccountStatusRequest = async (email: string) => {
  const { data } = await client.post<ApiSchema<"AccountStatusResponse">>("/auth/account-status", { email });
  return data;
};

export const getMeRequest = async () => {
  const { data } = await client.get<User>("/auth/me");
  return data;
};

export const forgotPasswordRequest = async (email: string) => {
  const { data } = await client.post<ApiSchema<"AuthMessageResponse">>("/auth/forgot-password", { email });
  return data;
};

export const resetPasswordRequest = async (payload: ResetPasswordPayload) => {
  const { data } = await client.post<ApiSchema<"AuthMessageResponse">>("/auth/reset-password", payload);
  return data;
};

export const requestPasswordChangeRequest = async () => {
  const { data } = await client.post<ApiSchema<"AuthMessageResponse">>("/auth/request-password-change");
  return data;
};

export const changePasswordRequest = async (payload: ChangePasswordPayload) => {
  const { data } = await client.post<ApiSchema<"AuthMessageResponse">>("/auth/change-password", payload);
  return data;
};
