"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import Button from "../../../components/ui/Button";
import ButtonLink from "../../../components/ui/ButtonLink";
import PageContainer from "../../../components/ui/PageContainer";
import { ROUTES } from "../../../routes/paths";

import styles from "./DemoPaymentPage.module.css";

export default function DemoPaymentPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams?.get("session_id") ?? "";
  const [processing, setProcessing] = useState(false);

  const completePayment = () => {
    if (!sessionId || processing) return;
    setProcessing(true);
    router.push(
      `${ROUTES.paymentSuccess}?session_id=${encodeURIComponent(sessionId)}`
    );
  };

  return (
    <PageContainer title="Pago de demostración">
      <div className={styles.content}>
        <p>
          Este checkout pertenece a Ticketing Demo. La compra
          no genera ningún cargo real.
        </p>

        {!sessionId ? (
          <p className={styles.error}>La sesión de pago no es válida.</p>
        ) : null}

        <div className={styles.actions}>
          <Button
            type="button"
            variant="primary"
            disabled={!sessionId || processing}
            onClick={completePayment}
          >
            {processing ? "Procesando..." : "Completar compra de prueba"}
          </Button>
          <ButtonLink href={ROUTES.paymentError}>Cancelar</ButtonLink>
        </div>
      </div>
    </PageContainer>
  );
}
