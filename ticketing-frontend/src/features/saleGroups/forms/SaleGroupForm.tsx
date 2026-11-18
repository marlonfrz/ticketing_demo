import { type ChangeEvent, type SubmitEvent, useState } from "react";

import Button from "../../../components/ui/Button";
import styles from "./SaleGroupForm.module.css";
import type { SaleGroup, SaleGroupCreate } from "../../../types/domain";

export type SaleGroupFormPayload = Omit<SaleGroupCreate, "session_id">;
type SaleGroupFormState = {
  name: string;
  strategy: string;
  display_order: string | number;
  is_active: boolean;
};

function buildFormState(initialData: SaleGroup | null): SaleGroupFormState {
  if (!initialData) {
    return {
      name: "",
      strategy: "stock_cascade",
      display_order: "",
      is_active: true,
    };
  }

  return {
    name: initialData.name || "",
    strategy: initialData.strategy || "stock_cascade",
    display_order: initialData.display_order || "",
    is_active: initialData.is_active ?? true,
  };
}

export default function SaleGroupForm({
  initialData = null,
  onSubmit,
  loading = false,
  submitLabel,
  readOnly = false,
  isAdmin = false,
}: {
  initialData?: SaleGroup | null;
  onSubmit: (payload: SaleGroupFormPayload) => void | Promise<void>;
  loading?: boolean;
  submitLabel: string;
  readOnly?: boolean;
  isAdmin?: boolean;
}) {
  const [form, setForm] = useState(() => buildFormState(initialData));

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;

    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();

    const payload: SaleGroupFormPayload = {
      name: form.name,
      strategy: form.strategy || "stock_cascade",
      is_active: true,
      ticket_types: [],
    };

    if (isAdmin) {
      payload.display_order = form.display_order ? Number(form.display_order) : null;
    }

    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} className={styles.form}>
      <div className={styles.field}>
        <label>Nombre del grupo</label>
        <input
          className={styles.input}
          name="name"
          value={form.name}
          onChange={handleChange}
          disabled={readOnly}
          required
        />
      </div>

      {isAdmin ? (
        <div className={styles.field}>
          <label>Posicion en la venta</label>
          <input
            className={styles.input}
            type="number"
            min="1"
            name="display_order"
            value={form.display_order}
            onChange={handleChange}
            disabled={readOnly}
            placeholder="Opcional"
          />
        </div>
      ) : null}

      {!readOnly ? (
        <Button type="submit" variant="primary" disabled={loading}>
          {loading ? "Guardando..." : submitLabel}
        </Button>
      ) : null}
    </form>
  );
}
