import { getTicketStatusLabel } from "../../../utils/statusLabels";
import { formatMoney } from "../../../utils/money";
import styles from "./SaleGroupTicketBoard.module.css";
import type { EntityId } from "../../../types/api";
import type { SaleGroup, TicketType } from "../../../types/domain";

function getTicketsByGroup(ticketTypes: TicketType[], groupId: EntityId): TicketType[] {
  return ticketTypes
    .filter((ticket) => ticket.sale_group_id === groupId)
    .sort((a, b) => {
      const orderA = a.sale_order ?? 9999;
      const orderB = b.sale_order ?? 9999;
      return orderA - orderB;
    });
}

function getUngroupedTickets(ticketTypes: TicketType[]): TicketType[] {
  return ticketTypes
    .filter((ticket) => !ticket.sale_group_id)
    .sort((a, b) => {
      const orderA = a.display_order ?? 9999;
      const orderB = b.display_order ?? 9999;
      if (orderA !== orderB) return orderA - orderB;
      return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    });
}

type SaleGroupTicketBoardProps = {
  groups: SaleGroup[];
  ticketTypes: TicketType[];
  isAdmin?: boolean;
  showHelp?: boolean;
};

export default function SaleGroupTicketBoard({
  groups,
  ticketTypes,
  isAdmin = false,
  showHelp = true,
}: SaleGroupTicketBoardProps) {
  const ungroupedTickets = getUngroupedTickets(ticketTypes);

  return (
    <div className={styles.wrapper}>
      <h3 className={styles.title}>Resumen de grupos y orden de entradas</h3>

      {showHelp ? (
        <p className={styles.help}>
          {isAdmin
            ? "El grupo y la posición de cada entrada se configuran al crearla o editarla."
            : "Las entradas se muestran ordenadas por grupo y por creación."}
        </p>
      ) : null}

      <div className={styles.columns}>
        <div className={styles.column}>
          <h4 className={styles.columnTitle}>Entradas sin grupo</h4>

          {ungroupedTickets.length === 0 ? (
            <p className={styles.empty}>No hay entradas sin grupo.</p>
          ) : null}

          <div className={styles.ticketList}>
            {ungroupedTickets.map((ticket) => (
              <TicketSummary key={ticket.id} ticket={ticket} isAdmin={isAdmin} />
            ))}
          </div>
        </div>

        {groups.map((group) => {
          const ticketsInGroup = getTicketsByGroup(ticketTypes, group.id);

          return (
            <div key={group.id} className={styles.column}>
              <h4 className={styles.columnTitle}>{group.name}</h4>

              {ticketsInGroup.length === 0 ? (
                <p className={styles.empty}>No hay entradas asignadas.</p>
              ) : null}

              <div className={styles.ticketList}>
                {ticketsInGroup.map((ticket) => (
                  <TicketSummary key={ticket.id} ticket={ticket} isAdmin={isAdmin} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TicketSummary({ ticket, isAdmin }: { ticket: TicketType; isAdmin: boolean }) {
  return (
    <div className={styles.ticket}>
      <strong>{ticket.sale_order ? `${ticket.sale_order}. ` : ""}</strong>
      {isAdmin && !ticket.sale_group_id && ticket.display_order
        ? `${ticket.display_order}. `
        : ""}
      {ticket.name}

      <div className={styles.ticketMeta}>
        {formatMoney(ticket.price, ticket.currency)} - stock {ticket.stock} -{" "}
        {getTicketStatusLabel(ticket.status)}
      </div>
    </div>
  );
}
