import Link from "next/link";
import { useParams } from "next/navigation";
import { type ChangeEvent, type SubmitEvent, useEffect, useState } from "react";
import Button from "../../../components/ui/Button";
import PageContainer from "../../../components/ui/PageContainer";
import { ROUTES } from "../../../routes/paths";
import {
  getPublicRelationsRegisterInfoRequest,
  registerPublicRelationsRequest,
} from "../api/publicRelationsApi";

import styles from "./PublicRelationsRegisterPage.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { ApiSchema } from "../../../types/api";

function buildAbsoluteUrl(path: string): string {
  return `${window.location.origin}${path}`;
}

export default function PublicRelationsRegisterPage() {
  const eventId = useParams<{ eventId: string }>()?.eventId;
  const [eventInfo, setEventInfo] = useState<ApiSchema<"PublicRelationsRegisterInfoResponse"> | null>(null);
  const [result, setResult] = useState<ApiSchema<"PublicRelationsRegisterResponse"> | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [copied, setCopied] = useState(false);
  const [form, setForm] = useState({
    full_name: "",
    phone: "",
    email: "",
    social_handle: "",
    accept_privacy: false,
  });

  useEffect(() => {
    const loadInfo = async () => {
      if (!eventId) return;
      try {
        setLoading(true);
        setErrorMsg("");
        const data = await getPublicRelationsRegisterInfoRequest(eventId);
        setEventInfo(data);
      } catch (error) {
        console.error("Error cargando registro RRPP:", error);
        setErrorMsg(getApiErrorMessage(error, "No se pudo cargar el registro RRPP"));
      } finally {
        setLoading(false);
      }
    };

    loadInfo();
  }, [eventId]);

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setForm((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const handleSubmit = async (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (submitting || !eventId) return;

    try {
      setSubmitting(true);
      setErrorMsg("");
      setCopied(false);
      const data = await registerPublicRelationsRequest(eventId, {
        ...form,
        email: form.email.trim() || null,
        social_handle: form.social_handle.trim() || null,
      });
      setResult(data);
    } catch (error) {
      console.error("Error registrando RRPP:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo completar el registro"));
    } finally {
      setSubmitting(false);
    }
  };

  const copySalesLink = async () => {
    if (!result?.sales_url) return;
    try {
      await navigator.clipboard.writeText(buildAbsoluteUrl(result.sales_url));
      setCopied(true);
    } catch {
      setErrorMsg("No se pudo copiar el enlace");
    }
  };

  return (
    <PageContainer title="Registro RRPP">
      <section className={styles.wrapper}>
        {loading ? <p>Cargando...</p> : null}
        {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

        {!loading && eventInfo ? (
          <>
            <div className={styles.header}>
              <h2>{eventInfo.event_title}</h2>
              <p>
                Registrate como RRPP de este evento para recibir tu enlace personal
                de venta.
              </p>
            </div>

            {result ? (
              <div className={styles.resultBox}>
                <h3>Tu enlace esta listo</h3>
                <p>
                  Comparte este enlace. Las compras pagadas desde el quedaran
                  atribuidas a tu registro.
                </p>
                <code>{buildAbsoluteUrl(result.sales_url)}</code>
                <Button variant="primary" type="button" onClick={copySalesLink}>
                  {copied ? "Copiado" : "Copiar enlace"}
                </Button>
                <Link className={styles.secondaryLink} href={result.sales_url}>
                  Ver evento
                </Link>
              </div>
            ) : (
              <form className={styles.form} onSubmit={handleSubmit}>
                <label className={styles.field}>
                  Nombre completo
                  <input
                    className={styles.input}
                    name="full_name"
                    value={form.full_name}
                    onChange={handleChange}
                    required
                  />
                </label>

                <label className={styles.field}>
                  Telefono
                  <input
                    className={styles.input}
                    name="phone"
                    type="tel"
                    value={form.phone}
                    onChange={handleChange}
                    required
                  />
                </label>

                <label className={styles.field}>
                  Email
                  <input
                    className={styles.input}
                    name="email"
                    type="email"
                    value={form.email}
                    onChange={handleChange}
                  />
                </label>

                <label className={styles.field}>
                  Instagram o red social
                  <input
                    className={styles.input}
                    name="social_handle"
                    value={form.social_handle}
                    onChange={handleChange}
                    placeholder="@usuario"
                  />
                </label>

                <label className={styles.checkLabel}>
                  <input
                    type="checkbox"
                    name="accept_privacy"
                    checked={form.accept_privacy}
                    onChange={handleChange}
                    required
                  />
                  <span>
                    Acepto la{" "}
                    <Link href={ROUTES.privacy} target="_blank">
                      politica de privacidad
                    </Link>
                    .
                  </span>
                </label>

                <Button variant="primary" type="submit" disabled={submitting}>
                  {submitting ? "Registrando..." : "Crear enlace RRPP"}
                </Button>
              </form>
            )}
          </>
        ) : null}
      </section>
    </PageContainer>
  );
}
