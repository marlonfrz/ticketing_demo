import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type SubmitEvent, useState } from "react";

import Button from "../../../components/ui/Button";
import { activateValidationStationRequest } from "../api/validationStationsApi";
import { ROUTES } from "../../../routes/paths";

import styles from "./ValidatorStationPage.module.css";
import { getApiErrorMessage } from "../../../api/errors";

export default function ValidatorActivatePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [responsibleName, setResponsibleName] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const token = searchParams?.get("token") || "";

  const activateStation = async (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token || loading) return;

    try {
      setLoading(true);
      setErrorMsg("");
      await activateValidationStationRequest({
        token,
        responsible_name: responsibleName || null,
      });
      router.replace(ROUTES.validatorScan);
    } catch (error) {
      console.error("Error activando puesto:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo activar el puesto. Solicita un enlace nuevo."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className={styles.page}>
      <section className={styles.panel}>
        <p className={styles.eyebrow}>Control de acceso</p>
        <h1 className={styles.title}>Activar puesto</h1>
        <p className={styles.text}>
          Este enlace vinculara el puesto a este movil. Solo se puede utilizar
          una vez.
        </p>

        {!token ? (
          <>
            <p className={styles.error}>El enlace no incluye un token valido.</p>
            <Link className={styles.secondaryLink} href={ROUTES.home}>Volver al inicio</Link>
          </>
        ) : (
          <form className={styles.form} onSubmit={activateStation}>
            <label className={styles.field}>
              Responsable del dispositivo
              <input
                className={styles.input}
                value={responsibleName}
                onChange={(event) => setResponsibleName(event.target.value)}
                placeholder="Opcional"
              />
            </label>
            {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}
            <Button variant="primary" type="submit" disabled={loading}>
              {loading ? "Activando..." : "Activar este movil"}
            </Button>
          </form>
        )}
      </section>
    </main>
  );
}
