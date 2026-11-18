import { useRouter, useSearchParams } from "next/navigation";
import { type ChangeEvent, type SubmitEvent, useState } from "react";

import Button from "../../../components/ui/Button";
import PageContainer from "../../../components/ui/PageContainer";
import { ROUTES } from "../../../routes/paths";
import PasswordRequirements from "../components/PasswordRequirements";
import { isStrongPassword } from "../utils/passwordValidation";
import { changePasswordRequest } from "../api/authApi";
import styles from "./AuthPasswordPage.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import useAuth from "../../../hooks/useAuth";

export default function ChangePasswordPage() {
  const router = useRouter();
  const { logout } = useAuth();
  const searchParams = useSearchParams();
  const token = searchParams?.get("token") || "";
  const [form, setForm] = useState({
    current_password: "",
    new_password: "",
    new_password_confirm: "",
  });
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token) {
      setErrorMsg("El enlace no incluye un token valido.");
      return;
    }
    if (form.new_password !== form.new_password_confirm) {
      setErrorMsg("Las contraseñas nuevas no coinciden.");
      return;
    }
    if (!isStrongPassword(form.new_password)) {
      setErrorMsg("La contraseña no cumple todos los requisitos.");
      return;
    }

    try {
      setLoading(true);
      setErrorMsg("");
      await changePasswordRequest({ token, ...form });
      await logout();
      router.replace(ROUTES.login);
    } catch (error) {
      setErrorMsg(getApiErrorMessage(error, "No se pudo cambiar la contraseña."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageContainer title="Cambiar contraseña">
      <form className={styles.form} onSubmit={handleSubmit}>
        <label className={styles.field}>
          <span className={styles.label}>Contraseña actual</span>
          <input
            className={styles.input}
            type="password"
            name="current_password"
            value={form.current_password}
            onChange={handleChange}
            required
          />
        </label>
        <label className={styles.field}>
          <span className={styles.label}>Nueva contraseña</span>
          <input
            className={styles.input}
            type="password"
            name="new_password"
            value={form.new_password}
            onChange={handleChange}
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
            onChange={handleChange}
            required
          />
        </label>
        {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}
        <Button type="submit" variant="primary" disabled={loading}>
          {loading ? "Guardando..." : "Cambiar contraseña"}
        </Button>
      </form>
    </PageContainer>
  );
}
