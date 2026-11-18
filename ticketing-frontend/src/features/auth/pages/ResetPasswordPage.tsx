import { useRouter, useSearchParams } from "next/navigation";
import { type ChangeEvent, type SubmitEvent, useState } from "react";

import Button from "../../../components/ui/Button";
import PageContainer from "../../../components/ui/PageContainer";
import { ROUTES } from "../../../routes/paths";
import PasswordRequirements from "../components/PasswordRequirements";
import { isStrongPassword } from "../utils/passwordValidation";
import { resetPasswordRequest } from "../api/authApi";
import styles from "./AuthPasswordPage.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import useAuth from "../../../hooks/useAuth";

type PasswordFormState = { new_password: string; new_password_confirm: string };
type PasswordFormProps = {
  form: PasswordFormState;
  loading: boolean;
  errorMsg: string;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onSubmit: (event: SubmitEvent<HTMLFormElement>) => void;
};

export default function ResetPasswordPage() {
  const router = useRouter();
  const { logout } = useAuth();
  const searchParams = useSearchParams();
  const token = searchParams?.get("token") || "";
  const [form, setForm] = useState({ new_password: "", new_password_confirm: "" });
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) {
      setErrorMsg("El enlace no incluye un token valido.");
      return;
    }
    if (form.new_password !== form.new_password_confirm) {
      setErrorMsg("Las contraseñas no coinciden.");
      return;
    }
    if (!isStrongPassword(form.new_password)) {
      setErrorMsg("La contraseña no cumple todos los requisitos.");
      return;
    }

    try {
      setLoading(true);
      setErrorMsg("");
      await resetPasswordRequest({ token, ...form });
      await logout();
      router.replace(ROUTES.login);
    } catch (error) {
      setErrorMsg(getApiErrorMessage(error, "No se pudo cambiar la contraseña."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageContainer title="Crear nueva contraseña">
      <PasswordForm
        form={form}
        loading={loading}
        errorMsg={errorMsg}
        onChange={(event) =>
          setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
        }
        onSubmit={handleSubmit}
      />
    </PageContainer>
  );
}

function PasswordForm({ form, loading, errorMsg, onChange, onSubmit }: PasswordFormProps) {
  return (
    <form className={styles.form} onSubmit={onSubmit}>
      <label className={styles.field}>
        <span className={styles.label}>Nueva contraseña</span>
        <input
          className={styles.input}
          type="password"
          name="new_password"
          value={form.new_password}
          onChange={onChange}
          required
        />
      </label>
      <PasswordRequirements password={form.new_password} />
      <label className={styles.field}>
        <span className={styles.label}>Repite la nueva contraseña</span>
        <input
          className={styles.input}
          type="password"
          name="new_password_confirm"
          value={form.new_password_confirm}
          onChange={onChange}
          required
        />
      </label>
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}
      <Button type="submit" variant="primary" disabled={loading}>
        {loading ? "Guardando..." : "Cambiar contraseña"}
      </Button>
    </form>
  );
}
