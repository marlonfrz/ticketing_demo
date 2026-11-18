import Link from "next/link";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import Button from "../../../components/ui/Button";
import Modal from "../../../components/ui/Modal";
import useAuth from "../../../hooks/useAuth";
import { ROUTES } from "../../../routes/paths";
import {
  forgotPasswordRequest,
  registerRequest,
} from "../api/authApi";
import PasswordRequirements from "./PasswordRequirements";
import { isStrongPassword } from "../utils/passwordValidation";
import { getApiErrorMessage } from "../../../api/errors";

import styles from "./PurchaseAccountModal.module.css";

type PurchaseCustomer = {
  email: string;
  full_name: string;
  phone: string;
  country_code?: string | null;
};

type PurchaseAccountModalProps = {
  isOpen: boolean;
  accountExists: boolean;
  accountCanLogin: boolean;
  customer: PurchaseCustomer;
  onClose: () => void;
  onContinueGuest: () => void;
  onAuthenticated: () => void | Promise<void>;
};

type LoginForm = { password: string };
type RegistrationForm = {
  password: string;
  password_confirm: string;
  accept_legal: boolean;
  marketing_consent: boolean;
};

export default function PurchaseAccountModal({
  isOpen,
  accountExists,
  accountCanLogin,
  customer,
  onClose,
  onContinueGuest,
  onAuthenticated,
}: PurchaseAccountModalProps) {
  const { login } = useAuth();
  const [mode, setMode] = useState<
    "offer" | "register" | "login" | "recovery" | "unavailable"
  >(
    accountExists ? (accountCanLogin ? "login" : "unavailable") : "offer"
  );
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const loginForm = useForm<LoginForm>({
    mode: "onSubmit",
    defaultValues: { password: "" },
  });
  const registerForm = useForm<RegistrationForm>({
    mode: "onSubmit",
    defaultValues: {
      password: "",
      password_confirm: "",
      accept_legal: false,
      marketing_consent: false,
    },
  });
  const resetLoginForm = loginForm.reset;
  const resetRegisterForm = registerForm.reset;

  useEffect(() => {
    if (!isOpen) return;
    setMode(
      accountExists ? (accountCanLogin ? "login" : "unavailable") : "offer"
    );
    setErrorMsg("");
    setSuccessMsg("");
    resetLoginForm({ password: "" });
    resetRegisterForm({
      password: "",
      password_confirm: "",
      accept_legal: false,
      marketing_consent: false,
    });
  }, [accountCanLogin, accountExists, isOpen, resetLoginForm, resetRegisterForm]);

  const submitLogin = loginForm.handleSubmit(async ({ password }) => {
    try {
      setLoading(true);
      setErrorMsg("");
      await login({ email: customer.email, password });
      await onAuthenticated();
    } catch (error) {
      setErrorMsg(getApiErrorMessage(error, "No se pudo iniciar sesion"));
    } finally {
      setLoading(false);
    }
  });

  const submitRegistration = registerForm.handleSubmit(async (values) => {
    if (values.password !== values.password_confirm) {
      registerForm.setError("password_confirm", {
        message: "Las contrasenas no coinciden",
      });
      return;
    }
    if (!isStrongPassword(values.password)) {
      registerForm.setError("password", {
        message: "La contrasena no cumple todos los requisitos",
      });
      return;
    }

    try {
      setLoading(true);
      setErrorMsg("");
      await registerRequest({
        email: customer.email,
        full_name: customer.full_name,
        phone: customer.phone,
        country_code: customer.country_code || "ES",
        password: values.password,
        accept_terms: values.accept_legal,
        accept_privacy: values.accept_legal,
        marketing_consent: values.marketing_consent,
        registration_source: "guest_checkout",
      });
      await login({ email: customer.email, password: values.password });
      await onAuthenticated();
    } catch (error) {
      setErrorMsg(getApiErrorMessage(error, "No se pudo crear la cuenta"));
    } finally {
      setLoading(false);
    }
  });

  const requestPasswordReset = async () => {
    try {
      setLoading(true);
      setErrorMsg("");
      const response = await forgotPasswordRequest(customer.email);
      setSuccessMsg(response.message);
      setMode("recovery");
    } catch (error) {
      setErrorMsg(getApiErrorMessage(error, "No se pudo enviar el enlace"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={loading ? undefined : onClose}
      title={
        accountExists
          ? accountCanLogin
            ? "Ya tienes una cuenta"
            : "Cuenta no disponible"
          : "Guarda tus entradas"
      }
    >
      <div className={styles.content}>
        {mode === "offer" ? (
          <>
            <p>
              El correo <strong>{customer?.email}</strong> no tiene una cuenta.
              Puedes crearla con los datos que acabas de indicar para recuperar
              tus entradas desde tu perfil.
            </p>
            <div className={styles.actions}>
              <Button
                variant="primary"
                type="button"
                onClick={() => setMode("register")}
              >
                Crear cuenta
              </Button>
              <Button
                type="button"
                onClick={onContinueGuest}
              >
                Continuar como invitado
              </Button>
            </div>
          </>
        ) : null}

        {mode === "register" ? (
          <form className={styles.form} onSubmit={submitRegistration}>
            <div className={styles.contactSummary}>
              <span>{customer.full_name}</span>
              <span>{customer.email}</span>
              <span>{customer.phone}</span>
            </div>
            <label className={styles.field}>
              Contrasena
              <input
                className={styles.input}
                type="password"
                autoComplete="new-password"
                {...registerForm.register("password", {
                  required: "Indica una contrasena",
                })}
              />
            </label>
            <PasswordRequirements password={registerForm.watch("password")} />
            <label className={styles.field}>
              Repite la contrasena
              <input
                className={styles.input}
                type="password"
                autoComplete="new-password"
                {...registerForm.register("password_confirm", {
                  required: "Repite la contrasena",
                })}
              />
            </label>
            {registerForm.formState.errors.password?.message ? (
              <p className={styles.error}>
                {registerForm.formState.errors.password.message}
              </p>
            ) : null}
            {registerForm.formState.errors.password_confirm?.message ? (
              <p className={styles.error}>
                {registerForm.formState.errors.password_confirm.message}
              </p>
            ) : null}
            <label className={styles.checkField}>
              <input
                type="checkbox"
                {...registerForm.register("accept_legal", {
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
              <input
                type="checkbox"
                {...registerForm.register("marketing_consent")}
              />
              <span>
                Quiero recibir novedades, promociones y avisos sobre proximos
                eventos. Es opcional.
              </span>
            </label>
            {registerForm.formState.errors.accept_legal?.message ? (
              <p className={styles.error}>
                {registerForm.formState.errors.accept_legal.message}
              </p>
            ) : null}
            <div className={styles.actions}>
              <Button
                variant="primary"
                type="submit"
                disabled={loading}
              >
                {loading ? "Creando..." : "Crear cuenta y continuar"}
              </Button>
              <Button
                type="button"
                disabled={loading}
                onClick={() => setMode("offer")}
              >
                Volver
              </Button>
            </div>
          </form>
        ) : null}

        {mode === "login" ? (
          <form className={styles.form} onSubmit={submitLogin}>
            <p>
              Hemos encontrado una cuenta con <strong>{customer?.email}</strong>.
              Inicia sesion para asociar la compra a tu perfil.
            </p>
            <label className={styles.field}>
              Contrasena
              <input
                className={styles.input}
                type="password"
                autoComplete="current-password"
                {...loginForm.register("password", {
                  required: "Indica tu contrasena",
                })}
              />
            </label>
            {loginForm.formState.errors.password?.message ? (
              <p className={styles.error}>
                {loginForm.formState.errors.password.message}
              </p>
            ) : null}
            <Button
              variant="primary"
              type="submit"
              disabled={loading}
            >
              {loading ? "Entrando..." : "Iniciar sesion y continuar"}
            </Button>
            <Button
              className={styles.textAction}
              variant="ghost"
              size="small"
              type="button"
              disabled={loading}
              onClick={requestPasswordReset}
            >
              He olvidado mi contrasena
            </Button>
          </form>
        ) : null}

        {mode === "unavailable" ? (
          <>
            <p>
              La cuenta asociada a <strong>{customer.email}</strong> no puede
              iniciar sesion en este momento. Puedes completar esta compra como
              invitado sin perder las entradas seleccionadas.
            </p>
            <Button
              variant="primary"
              type="button"
              disabled={loading}
              onClick={onContinueGuest}
            >
              Continuar como invitado
            </Button>
          </>
        ) : null}

        {mode === "recovery" ? (
          <>
            <p className={styles.success}>{successMsg}</p>
            <p>
              No perderas la seleccion de entradas. Cuando hayas recuperado la
              cuenta, vuelve a este modal para iniciar sesion.
            </p>
            <Button
              type="button"
              onClick={() => setMode("login")}
            >
              Volver al inicio de sesion
            </Button>
          </>
        ) : null}

        {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}
      </div>
    </Modal>
  );
}
