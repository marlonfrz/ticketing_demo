import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Button from "../../../components/ui/Button";
import ButtonLink from "../../../components/ui/ButtonLink";
import PageContainer from "../../../components/ui/PageContainer";
import { ROUTES } from "../../../routes/paths";
import {
  createDemoCheckoutRequest,
  getCheckoutSummaryRequest,
} from "../api/checkoutApi";
import CheckoutSummary from "../components/CheckoutSummary";
import ReservationCountdown from "../components/ReservationCountdown";

import styles from "./CheckoutPage.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { ApiSchema } from "../../../types/api";

type CheckoutSummary = ApiSchema<"CheckoutSummaryResponse">;

export default function CheckoutPage() {
  const orderId = useParams<{ orderId: string }>()?.orderId;
  const [reservation, setReservation] = useState<CheckoutSummary | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [loadingPayment, setLoadingPayment] = useState(false);
  const [expired, setExpired] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const loadSummary = async () => {
      try {
        setLoadingSummary(true);
        setErrorMsg("");

        if (!orderId) return;
        const data = await getCheckoutSummaryRequest(orderId);

        setReservation(data);
      } catch (error) {
        console.error("Error cargando checkout:", error);
        setErrorMsg(getApiErrorMessage(error, "No se pudo cargar el resumen del checkout"));
      } finally {
        setLoadingSummary(false);
      }
    };

    if (orderId) {
      loadSummary();
    }
  }, [orderId]);

  const handlePay = async () => {
    if (!orderId) return;
    try {
      setLoadingPayment(true);
      setErrorMsg("");

      const data = await createDemoCheckoutRequest(orderId);
      window.location.href = data.checkout_url;
    } catch (error) {
      console.error("Error creando checkout de demostración:", error);
      setErrorMsg(getApiErrorMessage(error, "No se pudo iniciar el pago de demostración"));
    } finally {
      setLoadingPayment(false);
    }
  };

  if (loadingSummary) {
    return (
      <PageContainer title="Checkout">
        <p>Cargando resumen de compra...</p>
      </PageContainer>
    );
  }

  if (errorMsg && !reservation) {
    return (
      <PageContainer title="Checkout">
        <p className={styles.error}>{errorMsg}</p>
        <ButtonLink className={styles.action} href={ROUTES.home}>
          Volver a eventos
        </ButtonLink>
      </PageContainer>
    );
  }

  if (!reservation) {
    return (
      <PageContainer title="Checkout">
        <p>No hay datos de reserva para mostrar.</p>
        <ButtonLink className={styles.action} href={ROUTES.home}>
          Volver a eventos
        </ButtonLink>
      </PageContainer>
    );
  }

  const canPay =
    reservation.status === "pending" &&
    reservation.payment_status === "pending" &&
    !expired;

  return (
    <PageContainer title="Checkout">
      {reservation.expires_at ? (
        <ReservationCountdown
          expiresAt={reservation.expires_at}
          onExpired={() => setExpired(true)}
        />
      ) : null}

      <CheckoutSummary reservation={reservation} />

      {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}

      {expired ? (
        <p className={styles.error}>
          La reserva ha expirado. Vuelve al evento y selecciona las entradas de
          nuevo.
        </p>
      ) : null}

      {reservation.status !== "pending" ? (
        <p className={styles.error}>
          Este pedido ya no está pendiente de pago.
        </p>
      ) : null}

      {canPay ? (
        <Button
          className={styles.action}
          variant="primary"
          onClick={handlePay}
          disabled={loadingPayment}
        >
          {loadingPayment ? "Redirigiendo..." : "Continuar al pago"}
        </Button>
      ) : null}
    </PageContainer>
  );
}
