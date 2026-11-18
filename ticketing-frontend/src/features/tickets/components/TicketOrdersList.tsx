import type { Order } from "../../../types/domain";
import Button from "../../../components/ui/Button";
import { getOrderEventTitle } from "../utils/ticketSearch";

import styles from "./TicketOrdersList.module.css";

type TicketOrdersListProps = {
  orders: Order[];
  downloadingOrderId: string;
  onDownload: (order: Order) => void | Promise<void>;
};

function formatDate(value?: string | null): string {
  if (!value) return "Fecha no disponible";
  return new Date(value).toLocaleString();
}

function formatMoney(value: string | number, currency = "EUR"): string {
  return `${Number(value || 0).toFixed(2)} ${currency}`;
}

function getOrderEventDate(order: Order): string | undefined {
  return order.tickets[0]?.event?.starts_at;
}

function getOrderLocation(order: Order): string | null | undefined {
  return order.tickets[0]?.event?.location_name;
}

function getTicketStatus(ticket: Order["tickets"][number]): string {
  if (ticket.used_at) return "Utilizada";
  return ticket.is_valid ? "Válida" : "No válida";
}

export default function TicketOrdersList({
  orders,
  downloadingOrderId,
  onDownload,
}: TicketOrdersListProps) {
  return (
    <div className={styles.ordersList}>
      {orders.map((order) => (
        <details key={order.id} className={styles.orderCard}>
          <summary className={styles.orderSummary}>
            <div className={styles.summaryMain}>
              <h2 className={styles.orderTitle}>{getOrderEventTitle(order)}</h2>
              <p className={styles.muted}>{formatDate(getOrderEventDate(order))}</p>
              {getOrderLocation(order) ? (
                <p className={styles.muted}>{getOrderLocation(order)}</p>
              ) : null}
            </div>
            <span className={styles.summaryAside}>
              <span className={styles.ticketCount}>
                {order.tickets.length} {order.tickets.length === 1 ? "entrada" : "entradas"}
              </span>
              <strong>{formatMoney(order.total_amount, order.currency)}</strong>
              <span className={styles.chevron} aria-hidden="true" />
            </span>
          </summary>

          <div className={styles.orderDetails}>
            <div className={styles.detailHeader}>
              <div>
                <h3>Detalle de las entradas</h3>
                <p>Pedido #{order.id.slice(0, 8).toUpperCase()}</p>
              </div>
              <Button
                type="button"
                className={styles.downloadButton}
                variant="primary"
                onClick={() => onDownload(order)}
                disabled={downloadingOrderId === order.id}
              >
                {downloadingOrderId === order.id
                  ? "Descargando..."
                  : "Descargar PDF"}
              </Button>
            </div>

            <ul className={styles.ticketList}>
              {order.tickets.map((ticket) => (
                <li key={ticket.id} className={styles.ticketItem}>
                  <div className={styles.ticketHeading}>
                    <strong>{ticket.ticket_type?.name || "Entrada"}</strong>
                    <span
                      className={
                        ticket.is_valid && !ticket.used_at
                          ? styles.validStatus
                          : styles.neutralStatus
                      }
                    >
                      {getTicketStatus(ticket)}
                    </span>
                  </div>
                  <dl className={styles.ticketData}>
                    <div>
                      <dt>Localizador</dt>
                      <dd>{ticket.ticket_code}</dd>
                    </div>
                    {ticket.recipient_name ? (
                      <div>
                        <dt>Asistente</dt>
                        <dd>{ticket.recipient_name}</dd>
                      </div>
                    ) : null}
                  </dl>
                </li>
              ))}
            </ul>
          </div>
        </details>
      ))}
    </div>
  );
}
