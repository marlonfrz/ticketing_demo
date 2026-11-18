import { useMemo } from "react";

import { getAvailabilityStatusLabel } from "../../../utils/statusLabels";
import { formatMoney } from "../../../utils/money";
import styles from "./PublicTicketOptionCard.module.css";
import type { SalesTicketOption } from "../api/salesApi";

type PublicTicketOptionCardProps = {
  ticket: SalesTicketOption;
  quantity: number;
  onChangeQuantity: (quantity: number) => void;
  disabledByGroup?: boolean;
};

export default function PublicTicketOptionCard({
  ticket,
  quantity,
  onChangeQuantity,
  disabledByGroup = false,
}: PublicTicketOptionCardProps) {
  const maxQuantity = Math.max(
    0,
    Math.min(
      Number(ticket.max_selectable_quantity || 0),
      Number(ticket.max_per_purchase || ticket.max_selectable_quantity || 0)
    )
  );
  const isAvailable = ["available", "low_stock"].includes(
    ticket.availability_status
  );

  const isDisabled = !isAvailable || disabledByGroup;

  const options = useMemo(() => {
    return Array.from({ length: maxQuantity + 1 }, (_, index) => index);
  }, [maxQuantity]);

  return (
    <div className={`${styles.card} ${isDisabled ? styles.disabled : ""}`}>
      <div>
        <h4 className={styles.title}>{ticket.name}</h4>

        {ticket.description ? (
          <p className={styles.description}>{ticket.description}</p>
        ) : null}

        <p className={styles.price}>
          {formatMoney(ticket.price, ticket.currency)}
        </p>

        <p className={ticket.is_low_stock ? styles.lowStock : styles.status}>
          {disabledByGroup
            ? "Bloqueado por otro tramo del mismo grupo"
            : getAvailabilityStatusLabel(ticket.availability_status)}
        </p>

        {isAvailable ? (
          <p className={styles.stock}>Maximo por compra: {maxQuantity}</p>
        ) : null}
      </div>

      <div className={styles.selectorBox}>
        <label className={styles.label}>Cantidad</label>
        <select
          className={styles.select}
          value={quantity}
          onChange={(e) => onChangeQuantity(Number(e.target.value))}
          disabled={isDisabled}
        >
          {options.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
