import { useEffect, useRef, useState } from "react";

import styles from "./ReservationCountdown.module.css";

function getRemainingSeconds(expiresAt: string | null): number {
  if (!expiresAt) return 0;

  const diff = new Date(expiresAt).getTime() - Date.now();
  return Math.max(0, Math.floor(diff / 1000));
}

function formatTime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;

  return `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

type ReservationCountdownProps = {
  expiresAt: string;
  onExpired?: () => void;
};

export default function ReservationCountdown({ expiresAt, onExpired }: ReservationCountdownProps) {
  const [remaining, setRemaining] = useState(() =>
    getRemainingSeconds(expiresAt)
  );

  const onExpiredRef = useRef(onExpired);
  useEffect(() => {
    onExpiredRef.current = onExpired;
  }, [onExpired]);

  useEffect(() => {
    const interval = setInterval(() => {
      const next = getRemainingSeconds(expiresAt);
      setRemaining(next);

      if (next <= 0) {
        clearInterval(interval);
        onExpiredRef.current?.();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [expiresAt]);

  return (
    <p className={remaining <= 60 ? styles.warning : styles.text}>
      Tiempo restante para completar la compra:{" "}
      <strong>{formatTime(remaining)}</strong>
    </p>
  );
}
