import { useState } from "react";
import Button from "../../../components/ui/Button";
import PageContainer from "../../../components/ui/PageContainer";
import useAuth from "../../../hooks/useAuth";
import { requestPasswordChangeRequest } from "../../auth/api/authApi";
import styles from "./ProfilePage.module.css";
import { getApiErrorMessage } from "../../../api/errors";

export default function ProfilePage() {
  const { user, authLoading } = useAuth();
  const [passwordLinkLoading, setPasswordLinkLoading] = useState(false);
  const [passwordLinkMsg, setPasswordLinkMsg] = useState("");
  const [passwordLinkError, setPasswordLinkError] = useState(false);

  const handleRequestPasswordChange = async () => {
    try {
      setPasswordLinkLoading(true);
      setPasswordLinkMsg("");
      setPasswordLinkError(false);
      const data = await requestPasswordChangeRequest();
      setPasswordLinkMsg(data.message);
    } catch (error) {
      setPasswordLinkError(true);
      setPasswordLinkMsg(getApiErrorMessage(error, "No se pudo enviar el enlace."));
    } finally {
      setPasswordLinkLoading(false);
    }
  };

  if (authLoading) {
    return (
      <PageContainer title="Perfil">
        <p>Cargando perfil...</p>
      </PageContainer>
    );
  }

  if (!user) {
    return (
      <PageContainer title="Perfil">
        <p>No hay sesion iniciada.</p>
      </PageContainer>
    );
  }

  return (
    <PageContainer title="Perfil">
      <div className={styles.profile}>
        <section className={styles.identity}>
          <span className={styles.avatar} aria-hidden="true">
            {user.full_name.trim().charAt(0).toUpperCase() || "U"}
          </span>
          <div>
            <h2>{user.full_name}</h2>
            <p>{user.email}</p>
          </div>
        </section>

        <section className={styles.section}>
          <h2>Datos personales</h2>
          <dl className={styles.dataList}>
            <div>
              <dt>Nombre</dt>
              <dd>{user.full_name}</dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>{user.email}</dd>
            </div>
            <div>
              <dt>Teléfono</dt>
              <dd>{user.phone || "No indicado"}</dd>
            </div>
          </dl>
        </section>

        <section className={styles.securitySection}>
          <div className={styles.securityCopy}>
            <h2>Seguridad</h2>
            <p>Te enviaremos un enlace seguro para actualizar tu contraseña.</p>
          </div>
          <Button
            className={styles.button}
            type="button"
            variant="primary"
            disabled={passwordLinkLoading}
            onClick={handleRequestPasswordChange}
          >
            {passwordLinkLoading ? "Enviando..." : "Cambiar contraseña"}
          </Button>
        </section>

        {passwordLinkMsg ? (
          <p
            className={passwordLinkError ? styles.errorMessage : styles.successMessage}
            role="status"
          >
            {passwordLinkMsg}
          </p>
        ) : null}
      </div>
    </PageContainer>
  );
}

