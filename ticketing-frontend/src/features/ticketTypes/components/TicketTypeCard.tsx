import Button from "../../../components/ui/Button";
import { getTicketStatusLabel } from "../../../utils/statusLabels";
import { formatMoney } from "../../../utils/money";
import styles from "./TicketTypeCard.module.css";
import type { TicketType } from "../../../types/domain";

type TicketTypeCardProps = {
  ticketType: TicketType;
  canManage: boolean;
  canDeleteTickets?: boolean;
  stockOnly?: boolean;
  isAdmin?: boolean;
  onEdit: () => void;
  onDelete: () => void;
};

export default function TicketTypeCard({
  ticketType,
  canManage,
  canDeleteTickets = true,
  stockOnly = false,
  isAdmin = false,
  onEdit,
  onDelete,
}: TicketTypeCardProps) {
  const canEdit = ticketType.status === "draft" || isAdmin;
  const canDelete =
    ticketType.status === "draft" &&
    ticketType.sold_count === 0;

  return (
    <div className={styles.card}>
      <div>
        <h4 className={styles.title}>{ticketType.name}</h4>

        {ticketType.description ? (
          <p className={styles.text}>{ticketType.description}</p>
        ) : null}

        <p className={styles.text}>
          <strong>Precio:</strong> {formatMoney(ticketType.price, ticketType.currency)}
        </p>
        <p className={styles.text}>
          <strong>Stock:</strong> {ticketType.stock}
        </p>
        <p className={styles.text}>
          <strong>Vendidas:</strong> {ticketType.sold_count}
        </p>
        <p className={styles.text}>
          <strong>Máx. por compra:</strong> {ticketType.max_per_purchase}
        </p>
        <p className={styles.text}>
          <strong>Estado:</strong> {getTicketStatusLabel(ticketType.status)}
        </p>
      </div>

      {canManage ? (
        <div className={styles.actions}>
          <Button size="small" onClick={onEdit}>
            {stockOnly ? "Ajustar stock" : canEdit ? "Editar" : "Ver"}
          </Button>

          {canDeleteTickets ? (
            <Button
              variant="danger"
              size="small"
              onClick={onDelete}
              disabled={!canDelete}
              title={
                !canDelete
                  ? "Solo se puede borrar un tipo de entrada en borrador y sin ventas"
                  : ""
              }
            >
              Borrar
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
