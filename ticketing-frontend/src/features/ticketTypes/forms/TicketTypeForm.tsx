import { type ChangeEvent, type SubmitEvent, useState } from "react";

import Button from "../../../components/ui/Button";
import styles from "./TicketTypeForm.module.css";
import type { EntityId } from "../../../types/api";
import type { SaleGroup, TicketType } from "../../../types/domain";

export type TicketTypeFormPayload = {
  stock: number;
  name?: string;
  description?: string | null;
  price?: number;
  currency?: string;
  max_per_purchase?: number;
  sale_group_id?: EntityId | null;
  sale_order?: number | null;
  is_active?: boolean;
  display_order?: number | null;
};

type TicketTypeFormState = {
  name: string;
  description: string;
  price: string | number;
  currency: string;
  stock: string;
  max_per_purchase: string;
  display_order: string;
  sale_group_id: string;
  sale_order: string;
  is_active: boolean;
};

function onlyInteger(value: string): string {
  return value.replace(/\D/g, "");
}

function normalizeDecimal(value: string): string {
  const normalized = value.replace(/[^\d,.]/g, "").replace(",", ".");
  const [integerPart = "", ...decimalParts] = normalized.split(".");
  const decimalPart = decimalParts.join("");

  return decimalParts.length > 0
    ? `${integerPart}.${decimalPart.slice(0, 2)}`
    : integerPart;
}

function toDecimalNumber(value: string | number): number {
  return Number(String(value).replace(",", "."));
}

function buildFormState(initialData: TicketType | null): TicketTypeFormState {
  if (!initialData) {
    return {
      name: "",
      description: "",
      price: "",
      currency: "EUR",
      stock: "",
      max_per_purchase: "",
      display_order: "",
      sale_group_id: "",
      sale_order: "",
      is_active: true,
    };
  }

  return {
    name: initialData.name || "",
    description: initialData.description || "",
    price: initialData.price ?? "",
    currency: initialData.currency || "EUR",
    stock: initialData.stock ? String(initialData.stock) : "",
    max_per_purchase: initialData.max_per_purchase
      ? String(initialData.max_per_purchase)
      : "",
    display_order: initialData.display_order ? String(initialData.display_order) : "",
    sale_group_id: initialData.sale_group_id || "",
    sale_order: initialData.sale_order ? String(initialData.sale_order) : "",
    is_active: initialData.is_active ?? true,
  };
}

export default function TicketTypeForm({
  initialData = null,
  saleGroups = [],
  onSubmit,
  loading = false,
  submitLabel,
  readOnly = false,
  isAdmin = false,
  stockOnly = false,
}: {
  initialData?: TicketType | null;
  saleGroups?: SaleGroup[];
  onSubmit: (payload: TicketTypeFormPayload) => void | Promise<void>;
  loading?: boolean;
  submitLabel: string;
  readOnly?: boolean;
  isAdmin?: boolean;
  stockOnly?: boolean;
}) {
  const [form, setForm] = useState(() => buildFormState(initialData));

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;

    setForm((prev) => ({
      ...prev,
      [name]:
        ["stock", "max_per_purchase", "display_order", "sale_order"].includes(name)
            ? onlyInteger(value)
            : name === "price"
              ? normalizeDecimal(value)
              : value,
    }));
  };

  const handleSubmit = (e: SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();

    const payload: TicketTypeFormPayload = {
      stock: Number(form.stock),
    };

    if (!stockOnly) {
      payload.name = form.name;
      payload.description = form.description || null;
      payload.price = toDecimalNumber(form.price);
      payload.currency = form.currency.toUpperCase();
      payload.max_per_purchase = Number(form.max_per_purchase);
      payload.sale_group_id = form.sale_group_id || null;
      payload.sale_order = form.sale_order ? Number(form.sale_order) : null;
      payload.is_active = true;
    }

    if (isAdmin && !stockOnly) {
      payload.display_order = form.display_order ? Number(form.display_order) : null;
    }

    onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} className={styles.form}>
      <div className={styles.field}>
        <label>Nombre</label>
        <input
          className={styles.input}
          name="name"
          value={form.name}
          onChange={handleChange}
          disabled={readOnly || stockOnly}
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
          disabled={readOnly || stockOnly}
        />
      </div>

      <div className={styles.field}>
        <label>Precio</label>
        <input
          className={styles.input}
          type="text"
          inputMode="decimal"
          name="price"
          value={form.price}
          onChange={handleChange}
          disabled={readOnly || stockOnly}
          required
        />
      </div>

      <div className={styles.field}>
        <label>Moneda</label>
        <input
          className={styles.input}
          name="currency"
          value={form.currency}
          onChange={handleChange}
          disabled={readOnly || stockOnly}
          maxLength={3}
          required
        />
      </div>

      <div className={styles.field}>
        <label>Stock</label>
        <input
          className={styles.input}
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          name="stock"
          value={form.stock}
          onChange={handleChange}
          disabled={readOnly}
          required
        />
      </div>

      <div className={styles.field}>
        <label>Maximo por compra</label>
        <input
          className={styles.input}
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          name="max_per_purchase"
          value={form.max_per_purchase}
          onChange={handleChange}
          disabled={readOnly || stockOnly}
          required
        />
      </div>

      {isAdmin ? (
        <div className={styles.field}>
          <label>Posicion en la venta</label>
          <input
            className={styles.input}
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            name="display_order"
            value={form.display_order}
            onChange={handleChange}
            disabled={readOnly || stockOnly || Boolean(form.sale_group_id)}
            placeholder={form.sale_group_id ? "Usa el orden dentro del grupo" : "Opcional"}
          />
        </div>
      ) : null}

      {saleGroups.length > 0 ? (
        <>
          <div className={styles.field}>
            <label>Grupo de venta</label>
            <select
              className={styles.input}
              name="sale_group_id"
              value={form.sale_group_id}
              onChange={handleChange}
              disabled={readOnly || stockOnly}
            >
              <option value="">Sin grupo</option>
              {saleGroups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
          </div>

          {form.sale_group_id ? (
            <div className={styles.field}>
              <label>Orden dentro del grupo</label>
              <input
                className={styles.input}
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                name="sale_order"
                value={form.sale_order}
                onChange={handleChange}
                disabled={readOnly || stockOnly}
                required
              />
            </div>
          ) : null}
        </>
      ) : null}

      {!readOnly ? (
        <Button type="submit" variant="primary" disabled={loading}>
          {loading ? "Guardando..." : submitLabel}
        </Button>
      ) : null}
    </form>
  );
}
