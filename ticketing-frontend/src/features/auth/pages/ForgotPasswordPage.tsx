import { type SubmitEvent, useState } from "react";
import Button from "../../../components/ui/Button";
import ButtonLink from "../../../components/ui/ButtonLink";
import PageContainer from "../../../components/ui/PageContainer";
import { ROUTES } from "../../../routes/paths";
import { forgotPasswordRequest } from "../api/authApi";
import styles from "./AuthPasswordPage.module.css";
import { getApiErrorMessage } from "../../../api/errors";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const handleSubmit = async (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      setLoading(true);
      setErrorMsg("");
      const data = await forgotPasswordRequest(email);
      setSuccessMsg(data.message);
    } catch (error) {
      setErrorMsg(getApiErrorMessage(error, "No se pudo procesar la solicitud."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageContainer title="Recuperar contraseña">
      <form className={styles.form} onSubmit={handleSubmit}>
        <p className={styles.muted}>
          Introduce tu correo y te enviaremos un enlace para crear una nueva contraseña.
        </p>
        <label className={styles.field}>
          <span className={styles.label}>Correo electronico</span>
          <input
            className={styles.input}
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>

        {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}
        {successMsg ? <p className={styles.success}>{successMsg}</p> : null}

        <div className={styles.actions}>
          <Button type="submit" variant="primary" disabled={loading}>
            {loading ? "Enviando..." : "Enviar enlace"}
          </Button>
          <ButtonLink href={ROUTES.login}>
            Volver a login
          </ButtonLink>
        </div>
      </form>
    </PageContainer>
  );
}
