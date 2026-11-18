import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type ChangeEvent, type SubmitEvent, useState } from "react";
import Button from "../../../components/ui/Button";
import ButtonLink from "../../../components/ui/ButtonLink";
import PageContainer from "../../../components/ui/PageContainer";
import useAuth from "../../../hooks/useAuth";
import { ROUTES } from "../../../routes/paths";
import { getApiErrorMessage } from "../../../api/errors";
import { getSafeRedirect } from "../utils/safeRedirect";

import styles from "./LoginPage.module.css";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;

    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();

    try {
      setLoading(true);
      setErrorMsg("");

      await login(form);
      router.push(
        getSafeRedirect(searchParams?.get("next") ?? null, window.location.origin) ??
          ROUTES.home
      );
    } catch (error) {
      setErrorMsg(getApiErrorMessage(error, "No se pudo iniciar sesión"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageContainer title="Login">
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.field}>
          <label className={styles.label}>Correo electrónico</label>
          <input
            className={styles.input}
            type="email"
            name="email"
            value={form.email}
            onChange={handleChange}
            placeholder="correo@ejemplo.com"
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label}>Contraseña</label>
          <input
            className={styles.input}
            type="password"
            name="password"
            value={form.password}
            onChange={handleChange}
            placeholder="Tu contraseña"
          />
          <Link className={styles.textButton} href={ROUTES.forgotPassword}>
            He olvidado mi contraseña
          </Link>
        </div>

        {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

        <div className={styles.actions}>
          <Button type="submit" variant="primary" disabled={loading}>
            {loading ? "Entrando..." : "Entrar"}
          </Button>

          <ButtonLink href={ROUTES.register}>
            Crear usuario
          </ButtonLink>

          <ButtonLink href={ROUTES.home}>
            Volver
          </ButtonLink>
        </div>
      </form>
    </PageContainer>
  );
}
