import styles from "./CheckoutSummary.module.css";
import type { ApiSchema } from "../../../types/api";

function formatTotal(value: string | number | null | undefined): string {
  return Number(value).toFixed(2);
}

export default function CheckoutSummary({ reservation }: { reservation: ApiSchema<"CheckoutSummaryResponse"> }) {
  const managementFee = reservation.management_fee ?? 0;

  return (
    <div className={styles.card}>
      <h2 className={styles.title}>Resumen de compra</h2>

      <div className={styles.list}>
        {reservation.items.map((item) => (
          <div key={item.ticket_type_id} className={styles.row}>
            <span>
              {item.quantity} × {item.ticket_type_name}
            </span>
            <strong>
              {formatTotal(item.subtotal)} {reservation.currency}
            </strong>
          </div>
        ))}
      </div>

      <div className={styles.row}>
        <span>Gastos de gestion</span>
        <strong>
          {formatTotal(managementFee)} {reservation.currency}
        </strong>
      </div>

      <div className={styles.total}>
        <span>Total</span>
        <strong>
          {formatTotal(reservation.total_amount)} {reservation.currency}
        </strong>
      </div>
    </div>
  );
}
