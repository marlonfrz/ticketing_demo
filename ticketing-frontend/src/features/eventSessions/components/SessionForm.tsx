import type { ChangeEvent, SubmitEvent } from "react";

import Button from "../../../components/ui/Button";
import type { EventSession, EventSessionCreate } from "../../../types/domain";

import styles from "./SessionForm.module.css";

export type SessionFormState = {
  title: string;
  location_name: string;
  location_address: string;
  starts_at: string;
  ends_at: string;
  capacity: string;
};

type SessionFormProps = {
  form: SessionFormState;
  loading: boolean;
  mode: "create" | "edit";
  onCancel: () => void;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onSubmit: (event: SubmitEvent<HTMLFormElement>) => void;
};

function toInputDate(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 16);
}

function fromInputDate(value: string): string | null {
  return value ? new Date(value).toISOString() : null;
}

export function buildInitialSessionForm(): SessionFormState {
  return {
    title: "",
    location_name: "",
    location_address: "",
    starts_at: "",
    ends_at: "",
    capacity: "",
  };
}

export function buildSessionForm(session: EventSession): SessionFormState {
  return {
    title: session.title || "",
    location_name: session.location_name || "",
    location_address: session.location_address || "",
    starts_at: toInputDate(session.starts_at),
    ends_at: toInputDate(session.ends_at),
    capacity: session.capacity ? String(session.capacity) : "",
  };
}

export function onlyInteger(value: string): string {
  return value.replace(/\D/g, "");
}

export function buildSessionPayload(form: SessionFormState): EventSessionCreate {
  return {
    title: null,
    location_name: form.location_name,
    location_address: form.location_address || null,
    starts_at: fromInputDate(form.starts_at) || "",
    ends_at: fromInputDate(form.ends_at),
    capacity: Number(form.capacity),
  };
}

export default function SessionForm({
  form,
  loading,
  mode,
  onCancel,
  onChange,
  onSubmit,
}: SessionFormProps) {
  const isEdit = mode === "edit";

  return (
    <form className={styles.form} onSubmit={onSubmit}>
      <label className={styles.field}>
        Lugar
        <input
          className={styles.input}
          name="location_name"
          value={form.location_name}
          onChange={onChange}
          required
        />
      </label>
      <label className={styles.field}>
        Dirección
        <input
          className={styles.input}
          name="location_address"
          value={form.location_address}
          onChange={onChange}
        />
      </label>
      <label className={styles.field}>
        Inicio
        <input
          className={styles.input}
          type="datetime-local"
          name="starts_at"
          value={form.starts_at}
          onChange={onChange}
          required
        />
      </label>
      <label className={styles.field}>
        Fin
        <input
          className={styles.input}
          type="datetime-local"
          name="ends_at"
          value={form.ends_at}
          onChange={onChange}
        />
      </label>
      <label className={styles.field}>
        Aforo
        <input
          className={styles.input}
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          name="capacity"
          value={form.capacity}
          onChange={onChange}
          required
        />
      </label>
      <div className={styles.formActions}>
        <Button
          className={styles.button}
          type="submit"
          variant="primary"
          disabled={loading}
        >
          {loading
            ? "Guardando..."
            : isEdit
              ? "Guardar cambios"
              : "Guardar sesión"}
        </Button>
        <Button
          className={styles.secondaryButton}
          variant="secondary"
          disabled={loading}
          onClick={onCancel}
        >
          Cancelar
        </Button>
      </div>
    </form>
  );
}
