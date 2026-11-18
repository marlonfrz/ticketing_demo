import { type ChangeEvent, type SubmitEvent, useState } from "react";
import Image from "next/image";

import Button from "../../../components/ui/Button";
import { getMediaUrl } from "../../../utils/media";
import { hasUnsavedChanges } from "../utils/formState";
import styles from "./EventForm.module.css";
import type { EventSessionCreate, ManagedEvent } from "../../../types/domain";

const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

export type EventFormData = {
  title: string;
  description: string | null;
  initial_session?: EventSessionCreate;
};

export type EventFormSubmission = {
  eventData: EventFormData;
  imageFile: File | null;
};

type EventFormState = {
  title: string;
  description: string;
  location_name: string;
  location_address: string;
  starts_at: string;
  ends_at: string;
  capacity: string;
};

function toDatetimeLocal(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset();
  const localDate = new Date(date.getTime() - offset * 60000);
  return localDate.toISOString().slice(0, 16);
}

function fromDatetimeLocal(value: string): string | null {
  if (!value) return null;
  return new Date(value).toISOString();
}

function onlyInteger(value: string): string {
  return value.replace(/\D/g, "");
}

function validateImageFile(file: File): string | null {
  if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
    return "Formato no permitido. Usa JPG, PNG o WEBP.";
  }
  if (file.size > MAX_IMAGE_BYTES) {
    const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
    return `La imagen pesa ${sizeMb} MB y el máximo es 8 MB. Redúcela e inténtalo de nuevo.`;
  }
  return null;
}

function buildFormState(initialData: ManagedEvent | null): EventFormState {
  const initialSession = initialData?.sessions?.[0] || null;

  if (!initialData) {
    return {
      title: "",
      description: "",
      location_name: "",
      location_address: "",
      starts_at: "",
      ends_at: "",
      capacity: "",
    };
  }

  return {
    title: initialData.title || "",
    description: initialData.description || "",
    location_name: initialSession?.location_name || "",
    location_address: initialSession?.location_address || "",
    starts_at: toDatetimeLocal(initialSession?.starts_at),
    ends_at: toDatetimeLocal(initialSession?.ends_at),
    capacity: initialSession?.capacity ? String(initialSession.capacity) : "",
  };
}

export default function EventForm({
  initialData = null,
  onSubmit,
  loading = false,
  submitLabel,
  readOnly = false,
  onDirtyChange,
}: {
  initialData?: ManagedEvent | null;
  onSubmit: (submission: EventFormSubmission) => void | Promise<void>;
  loading?: boolean;
  submitLabel: string;
  readOnly?: boolean;
  onDirtyChange?: (isDirty: boolean) => void;
}) {
  const [initialForm] = useState(() => buildFormState(initialData));
  const [form, setForm] = useState(initialForm);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageError, setImageError] = useState("");
  const [imagePreview, setImagePreview] = useState(() =>
    getMediaUrl(initialData?.image_url)
  );
  const isCreate = !initialData;

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    const nextForm = {
      ...form,
      [name]: name === "capacity" ? onlyInteger(value) : value,
    };

    setForm(nextForm);
    onDirtyChange?.(hasUnsavedChanges(nextForm, initialForm, imageFile !== null));
  };

  const handleImageChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;

    if (!file) {
      setImageFile(null);
      setImageError("");
      setImagePreview(getMediaUrl(initialData?.image_url));
      onDirtyChange?.(hasUnsavedChanges(form, initialForm));
      return;
    }

    const validationError = validateImageFile(file);
    if (validationError) {
      e.target.value = "";
      setImageFile(null);
      setImageError(validationError);
      setImagePreview(getMediaUrl(initialData?.image_url));
      onDirtyChange?.(hasUnsavedChanges(form, initialForm));
      return;
    }

    setImageFile(file);
    setImageError("");
    setImagePreview(URL.createObjectURL(file));
    onDirtyChange?.(true);
  };

  const handleSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();

    const eventData: EventFormData = {
      title: form.title,
      description: form.description || null,
    };

    if (isCreate) {
      eventData.initial_session = {
        location_name: form.location_name,
        location_address: form.location_address || null,
        starts_at: fromDatetimeLocal(form.starts_at) || "",
        ends_at: form.ends_at ? fromDatetimeLocal(form.ends_at) : null,
        capacity: Number(form.capacity),
      };
    }

    onSubmit({ eventData, imageFile });
  };

  return (
    <form onSubmit={handleSubmit} className={styles.form}>
      <div className={styles.field}>
        <label>Titulo</label>
        <input
          className={styles.input}
          name="title"
          value={form.title}
          onChange={handleChange}
          disabled={readOnly}
          required
        />
      </div>

      <div className={styles.field}>
        <label>Descripcion</label>
        <textarea
          className={styles.textarea}
          name="description"
          value={form.description}
          onChange={handleChange}
          disabled={readOnly}
        />
      </div>

      {isCreate ? (
        <>
          <div className={styles.field}>
            <label>Nombre de ubicacion</label>
            <input
              className={styles.input}
              name="location_name"
              value={form.location_name}
              onChange={handleChange}
              disabled={readOnly}
              required
            />
          </div>

          <div className={styles.field}>
            <label>Direccion</label>
            <input
              className={styles.input}
              name="location_address"
              value={form.location_address}
              onChange={handleChange}
              disabled={readOnly}
            />
          </div>

          <div className={styles.field}>
            <label>Inicio del evento</label>
            <input
              className={styles.input}
              type="datetime-local"
              name="starts_at"
              value={form.starts_at}
              onChange={handleChange}
              disabled={readOnly}
              required
            />
          </div>

          <div className={styles.field}>
            <label>Fin del evento</label>
            <input
              className={styles.input}
              type="datetime-local"
              name="ends_at"
              value={form.ends_at}
              onChange={handleChange}
              disabled={readOnly}
            />
          </div>

          <div className={styles.field}>
            <label>Aforo</label>
            <input
              className={styles.input}
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              name="capacity"
              value={form.capacity}
              onChange={handleChange}
              disabled={readOnly}
              required
            />
          </div>
        </>
      ) : null}

      <div className={styles.field}>
        <label>Imagen del evento</label>
        {imagePreview ? (
          <Image
            className={styles.imagePreview}
            src={imagePreview}
            alt={`Imagen de ${form.title || "evento"}`}
            width={1200}
            height={675}
            sizes="(max-width: 700px) 100vw, 650px"
            quality={92}
            unoptimized={imagePreview.startsWith("blob:")}
          />
        ) : (
          <div className={styles.emptyPreview}>Sin imagen cargada</div>
        )}
        <input
          className={styles.input}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleImageChange}
        />
        {imageError ? <p className={styles.error}>{imageError}</p> : null}
        <small className={styles.helpText}>
          Opcional. JPG, PNG o WEBP de hasta 8 MB. Lo optimizamos
          automaticamente para web.
        </small>
      </div>

      {!readOnly ? (
        <Button className={styles.button} type="submit" variant="primary" disabled={loading}>
          {loading ? "Guardando..." : submitLabel}
        </Button>
      ) : imageFile ? (
        <Button className={styles.button} type="submit" variant="primary" disabled={loading}>
          {loading ? "Guardando..." : "Guardar imagen"}
        </Button>
      ) : null}
    </form>
  );
}
