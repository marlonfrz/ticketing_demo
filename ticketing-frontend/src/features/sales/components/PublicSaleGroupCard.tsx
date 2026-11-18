import PublicTicketOptionCard from "./PublicTicketOptionCard";

import styles from "./PublicSaleGroupCard.module.css";
import type { EntityId } from "../../../types/api";
import type { SalesOptionItem } from "../api/salesApi";

type SaleGroupOption = Extract<SalesOptionItem, { type: "sale_group" }>;
type PublicSaleGroupCardProps = {
  group: SaleGroupOption;
  selectedQuantities: Record<EntityId, number>;
  selectedGroupIds: Set<EntityId>;
  onChangeQuantity: (ticketId: EntityId, quantity: number) => void;
};

export default function PublicSaleGroupCard({
  group,
  selectedQuantities,
  selectedGroupIds,
  onChangeQuantity,
}: PublicSaleGroupCardProps) {
  return (
    <div className={styles.group}>
      <div className={styles.header}>
        <h3 className={styles.title}>{group.name}</h3>
      </div>

      <div className={styles.list}>
        {group.ticket_types.map((ticket) => {
          const selectedQuantity = selectedQuantities[ticket.id] || 0;
          const disabledByGroup = Boolean(
            ticket.sale_group_id &&
            selectedGroupIds.has(ticket.sale_group_id) &&
            selectedQuantity === 0
          );

          return (
            <PublicTicketOptionCard
              key={ticket.id}
              ticket={ticket}
              quantity={selectedQuantity}
              disabledByGroup={disabledByGroup}
              onChangeQuantity={(quantity) =>
                onChangeQuantity(ticket.id, quantity)
              }
            />
          );
        })}
      </div>
    </div>
  );
}
