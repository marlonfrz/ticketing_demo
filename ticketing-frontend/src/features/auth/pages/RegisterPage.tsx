import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import Button from "../../../components/ui/Button";
import ButtonLink from "../../../components/ui/ButtonLink";
import PageContainer from "../../../components/ui/PageContainer";
import { ROUTES } from "../../../routes/paths";
import { registerRequest } from "../api/authApi";
import PasswordRequirements from "../components/PasswordRequirements";
import { isStrongPassword } from "../utils/passwordValidation";
import { getApiErrorMessage } from "../../../api/errors";

import styles from "./RegisterPage.module.css";

type RegistrationForm = {
  full_name: string;
  email: string;
  phone: string;
  password: string;
  password_confirm: string;
  accept_legal: boolean;
  marketing_consent: boolean;
};

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const {
    register,
    handleSubmit,
    setError,
    watch,
    formState: { errors },
  } = useForm<RegistrationForm>({
    mode: "onSubmit",
    reValidateMode: "onChange",
    defaultValues: {
      full_name: "",
      email: "",
      phone: "",
      password: "",
      password_confirm: "",
      accept_legal: false,
      marketing_consent: false,
    },
  });

  const password = watch("password");

  const submitRegistration = handleSubmit(async (form) => {
    if (form.password !== form.password_confirm) {
      setError("password_confirm", {
        message: "Las contrasenas no coinciden",
      });
      return;
    }
    if (!isStrongPassword(form.password)) {
      setError("password", {
        message: "La contrasena no cumple todos los requisitos",
      });
      return;
    }

    try {
      setLoading(true);
      setErrorMsg("");
      setSuccessMsg("");
      await registerRequest({
        email: form.email.trim().toLowerCase(),
        full_name: form.full_name.trim(),
        phone: form.phone.trim(),
        country_code: "ES",
        password: form.password,
        accept_terms: form.accept_legal,
        accept_privacy: form.accept_legal,
        marketing_consent: form.marketing_consent,
        registration_source: "registration",
      });
      setSuccessMsg("Usuario creado correctamente");
      window.setTimeout(() => router.push(ROUTES.login), 1000);
    } catch (error) {
      setErrorMsg(getApiErrorMessage(error, "No se pudo crear el usuario"));
    } finally {
      setLoading(false);
    }
  });

  return (
    <PageContainer title="Crear usuario">
      <form onSubmit={submitRegistration} className={styles.form}>
        <label className={styles.field}>
          <span className={styles.label}>Nombre completo</span>
          <input
            className={styles.input}
            autoComplete="name"
            {...register("full_name", {
              required: "Indica tu nombre completo",
              minLength: {
                value: 2,
                message: "Indica tu nombre completo",
              },
            })}
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Correo electronico</span>
          <input
            className={styles.input}
            type="email"
            autoComplete="email"
            {...register("email", {
              required: "Indica un correo valido",
              pattern: {
                value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                message: "Indica un correo valido",
              },
            })}
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Telefono</span>
          <input
            className={styles.input}
            type="tel"
            autoComplete="tel"
            {...register("phone", {
              required: "Indica un telefono de contacto",
              validate: (value) =>
                value.replace(/[^\d+]/g, "").length >= 6 ||
                "Indica un telefono de contacto valido",
            })}
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Contrasena</span>
          <input
            className={styles.input}
            type="password"
            autoComplete="new-password"
            {...register("password", {
              required: "Indica una contrasena",
            })}
          />
        </label>

        <PasswordRequirements password={password} />

        <label className={styles.field}>
          <span className={styles.label}>Repite la contrasena</span>
          <input
            className={styles.input}
            type="password"
            autoComplete="new-password"
            {...register("password_confirm", {
              required: "Repite la contrasena",
            })}
          />
        </label>

        <label className={styles.checkField}>
          <input
            type="checkbox"
            {...register("accept_legal", {
              required:
                "Debes aceptar las condiciones de uso y la politica de privacidad",
            })}
          />
          <span>
            Acepto las{" "}
            <Link href={ROUTES.terms} target="_blank">
              condiciones de uso
            </Link>{" "}
            y la{" "}
            <Link href={ROUTES.privacy} target="_blank">
              politica de privacidad
            </Link>
            .
          </span>
        </label>

        <label className={styles.checkField}>
          <input type="checkbox" {...register("marketing_consent")} />
          <span>
            Quiero recibir novedades, promociones y avisos sobre proximos
            eventos. Es opcional.
          </span>
        </label>

        {Object.values(errors)[0]?.message ? (
          <p className={styles.error}>{Object.values(errors)[0]?.message}</p>
        ) : null}
        {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}
        {successMsg ? <p className={styles.success}>{successMsg}</p> : null}

        <div className={styles.actions}>
          <Button type="submit" variant="primary" disabled={loading}>
            {loading ? "Creando..." : "Crear usuario"}
          </Button>
          <ButtonLink href={ROUTES.login}>
            Ir a login
          </ButtonLink>
          <ButtonLink href={ROUTES.home}>
            Volver
          </ButtonLink>
        </div>
      </form>
    </PageContainer>
  );
}
