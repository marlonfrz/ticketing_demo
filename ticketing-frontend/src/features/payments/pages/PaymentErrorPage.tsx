import PageContainer from "../../../components/ui/PageContainer";
import ButtonLink from "../../../components/ui/ButtonLink";
import { ROUTES } from "../../../routes/paths";

import styles from "./PaymentErrorPage.module.css";

export default function PaymentErrorPage() {
  return (
    <PageContainer title="Pago cancelado">
      <p>No se ha completado el cobro. Puedes volver a los eventos cuando quieras.</p>

      <div className={styles.actions}>
        <ButtonLink href={ROUTES.home}>
          Volver al inicio
        </ButtonLink>
      </div>
    </PageContainer>
  );
}
