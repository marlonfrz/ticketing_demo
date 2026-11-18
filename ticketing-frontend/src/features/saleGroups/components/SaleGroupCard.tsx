import Button from "../../../components/ui/Button";
import { getSaleGroupStatusLabel } from "../../../utils/statusLabels";
import styles from "./SaleGroupCard.module.css";
import type { SaleGroup } from "../../../types/domain";

type SaleGroupCardProps = {
  group: SaleGroup;
  canManage: boolean;
  isAdmin: boolean;
  canPublishSaleGroups: boolean;
  onEdit: () => void;
  onDelete: () => void;
  onPublish: () => void;
};

export default function SaleGroupCard({
  group,
  canManage,
  isAdmin,
  canPublishSaleGroups,
  onEdit,
  onDelete,
  onPublish,
}: SaleGroupCardProps) {
  const canEdit = group.status === "draft" || isAdmin;
  const canDelete = group.status === "draft";
  const canPublish = canManage && canPublishSaleGroups && group.status === "draft";

  return (
    <div className={styles.card}>
      <div>
        <h4 className={styles.title}>{group.name}</h4>

        {isAdmin && group.display_order ? (
          <p className={styles.text}>
            <strong>Posicion:</strong> {group.display_order}
          </p>
        ) : null}

        <p className={styles.text}>
          <strong>Estado:</strong> {getSaleGroupStatusLabel(group.status)}
        </p>

        {group.sale_starts_at ? (
          <p className={styles.text}>
            <strong>Inicio venta:</strong>{" "}
            {new Date(group.sale_starts_at).toLocaleString()}
          </p>
        ) : null}

        {group.sale_ends_at ? (
          <p className={styles.text}>
            <strong>Fin venta:</strong>{" "}
            {new Date(group.sale_ends_at).toLocaleString()}
          </p>
        ) : null}
      </div>

      {canManage ? (
        <div className={styles.actions}>
          <Button size="small" onClick={onEdit}>
            {canEdit ? "Editar" : "Ver"}
          </Button>

          <Button
            variant="danger"
            size="small"
            onClick={onDelete}
            disabled={!canDelete}
            title={!canDelete ? "Solo se puede borrar un grupo en draft" : ""}
          >
            Borrar
          </Button>

          {isAdmin && canPublishSaleGroups ? (
            <Button
              variant="primarySoft"
              size="small"
              onClick={onPublish}
              disabled={!canPublish}
              title={
                !canPublish
                  ? "Solo admin puede publicar grupos en draft"
                  : ""
              }
            >
              Publicar
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
