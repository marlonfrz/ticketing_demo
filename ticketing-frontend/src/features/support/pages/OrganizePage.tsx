"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";

import { getApiErrorMessage } from "../../../api/errors";
import Button from "../../../components/ui/Button";
import PageContainer from "../../../components/ui/PageContainer";
import { sendOrganizerContactRequest } from "../api/supportApi";
import { SUPPORT_EMAIL } from "../config";

import styles from "./OrganizePage.module.css";

type OrganizerContactForm = {
  name: string;
  email: string;
  phone: string;
  description: string;
  website: string;
};

export default function OrganizePage() {
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<OrganizerContactForm>({
    defaultValues: {
      name: "",
      email: "",
      phone: "",
      description: "",
      website: "",
    },
  });

  const submitContact = handleSubmit(async (form) => {
    try {
      setSubmitting(true);
      setErrorMessage("");
      setSuccessMessage("");
      const response = await sendOrganizerContactRequest({
        name: form.name.trim(),
        email: form.email.trim().toLowerCase(),
        phone: form.phone.trim() || null,
        description: form.description.trim(),
        website: form.website.trim() || null,
      });
      setSuccessMessage(response.message);
      reset();
    } catch (error) {
      setErrorMessage(
        getApiErrorMessage(
          error,
          "No pudimos enviar la solicitud. Inténtalo de nuevo en unos minutos."
        )
      );
    } finally {
      setSubmitting(false);
    }
  });

  const firstError = Object.values(errors)[0]?.message;

  return (
    <PageContainer title="Organiza tu evento con nosotros">
      <div className={styles.layout}>
        <section className={styles.introduction}>
          <p className={styles.lead}>
            Cuéntanos qué quieres organizar. Podemos ayudarte a crear el evento,
            preparar sus sesiones y poner las entradas a la venta.
          </p>
          <div className={styles.steps}>
            <p><strong>1.</strong> Recibimos tu propuesta.</p>
            <p><strong>2.</strong> Revisamos contigo las necesidades del evento.</p>
            <p><strong>3.</strong> Preparamos la publicación y la venta de entradas.</p>
          </div>
          <p className={styles.contactAlternative}>
            También puedes escribirnos a{" "}
            <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>.
          </p>
        </section>

        <form className={styles.form} onSubmit={submitContact} noValidate>
          <div className={styles.fieldGrid}>
            <label className={styles.field}>
              <span>Nombre</span>
              <input
                autoComplete="name"
                {...register("name", {
                  required: "Indica tu nombre.",
                  minLength: { value: 2, message: "El nombre es demasiado corto." },
                  maxLength: { value: 120, message: "El nombre es demasiado largo." },
                })}
              />
            </label>

            <label className={styles.field}>
              <span>Email</span>
              <input
                type="email"
                autoComplete="email"
                {...register("email", {
                  required: "Indica tu email.",
                  pattern: {
                    value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                    message: "Indica un email válido.",
                  },
                })}
              />
            </label>
          </div>

          <label className={styles.field}>
            <span>Teléfono <small>Opcional</small></span>
            <input
              type="tel"
              autoComplete="tel"
              {...register("phone", {
                maxLength: { value: 30, message: "El teléfono es demasiado largo." },
                validate: (value) =>
                  !value ||
                  value.replace(/\D/g, "").length >= 6 ||
                  "Indica un teléfono válido.",
              })}
            />
          </label>

          <label className={styles.field}>
            <span>Háblanos del evento</span>
            <textarea
              rows={7}
              placeholder="Tipo de evento, fecha aproximada, ubicación, aforo estimado y cualquier detalle que debamos conocer."
              {...register("description", {
                required: "Describe brevemente el evento.",
                minLength: {
                  value: 20,
                  message: "Añade un poco más de información sobre el evento.",
                },
                maxLength: {
                  value: 3000,
                  message: "La descripción no puede superar los 3000 caracteres.",
                },
              })}
            />
          </label>

          <label className={styles.honeypot} aria-hidden="true">
            Sitio web
            <input tabIndex={-1} autoComplete="off" {...register("website")} />
          </label>

          {firstError ? <p className={styles.error}>{firstError}</p> : null}
          {errorMessage ? <p className={styles.error}>{errorMessage}</p> : null}
          {successMessage ? (
            <p className={styles.success} role="status">{successMessage}</p>
          ) : null}

          <div className={styles.actions}>
            <Button type="submit" variant="primary" disabled={submitting}>
              {submitting ? "Enviando..." : "Enviar propuesta"}
            </Button>
          </div>
        </form>
      </div>
    </PageContainer>
  );
}
