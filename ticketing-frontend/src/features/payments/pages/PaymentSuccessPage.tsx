import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Button from "../../../components/ui/Button";
import ButtonLink from "../../../components/ui/ButtonLink";
import PageContainer from "../../../components/ui/PageContainer";
import { ROUTES } from "../../../routes/paths";
import {
  confirmDemoSessionRequest,
  downloadCheckoutTicketsPdfRequest,
} from "../../checkout/api/checkoutApi";

import styles from "./PaymentSuccessPage.module.css";
import { getApiErrorMessage } from "../../../api/errors";

export default function PaymentSuccessPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams?.get("session_id") ?? "";
  const [statusMsg, setStatusMsg] = useState(() =>
    sessionId
      ? "Confirmando pago..."
      : "No se puede verificar el pago sin una sesión válida."
  );
  const [errorMsg, setErrorMsg] = useState(() =>
    sessionId
      ? ""
      : "Vuelve al checkout para completar el proceso."
  );
  const [paymentConfirmed, setPaymentConfirmed] = useState(false);
  const [orderId, setOrderId] = useState("");
  const [downloading, setDownloading] = useState(false);
  const confirmationStarted = useRef(false);

  useEffect(() => {
    if (confirmationStarted.current) return;
    if (!sessionId) return;

    confirmationStarted.current = true;

    const confirmPayment = async () => {
      try {
        const payment = await confirmDemoSessionRequest(sessionId);
        setOrderId(payment.order_id);
        setPaymentConfirmed(true);
        setStatusMsg("Pago confirmado. Tus entradas se han generado y se enviaran por email.");
      } catch (error) {
        setStatusMsg("No hemos podido verificar el resultado del pago.");
        setErrorMsg(
          getApiErrorMessage(
            error,
            "No se pudo confirmar el pedido automáticamente."
          )
        );
      }
    };

    confirmPayment();
  }, [sessionId]);

  const downloadTickets = async () => {
    if (!orderId || downloading) return;

    try {
      setDownloading(true);
      setErrorMsg("");
      const blob = await downloadCheckoutTicketsPdfRequest(orderId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `entradas-${orderId.slice(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error descargando entradas:", error);
      setErrorMsg(
        getApiErrorMessage(
          error,
          "No se pudo descargar el PDF. Si no recibes el correo, contacta con soporte."
        )
      );
    } finally {
      setDownloading(false);
    }
  };

  return (
    <PageContainer title={paymentConfirmed ? "Pago correcto" : "Estado del pago"}>
      <p>{statusMsg}</p>
      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      <div className={styles.actions}>
        {orderId ? (
          <Button type="button" variant="primary" disabled={downloading} onClick={downloadTickets}>
            {downloading ? "Descargando..." : "Descargar entradas PDF"}
          </Button>
        ) : null}
        <ButtonLink href={ROUTES.home}>
          Volver al inicio
        </ButtonLink>
      </div>
    </PageContainer>
  );
}
