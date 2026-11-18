import { useRouter } from "next/navigation";
import { type SubmitEvent, useCallback, useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";

import Button from "../../../components/ui/Button";
import {
  getCurrentValidationStationRequest,
  logoutValidationStationRequest,
  reportValidationStationIncidentRequest,
  validateTicketFromStationRequest,
  type StationValidationResult,
} from "../api/validationStationsApi";
import { ROUTES } from "../../../routes/paths";

import styles from "./ValidatorStationPage.module.css";
import { getApiErrorMessage } from "../../../api/errors";
import type { ValidationStation } from "../../../types/domain";

const READER_ID = "validator-qr-reader";
const SAME_CODE_COOLDOWN_MS = 6000;

export default function ValidatorScanPage() {
  const router = useRouter();
  const scannerRef = useRef<Html5Qrcode | null>(null);
  const scanPendingRef = useRef(false);
  const lastScanRef = useRef({ token: "", scannedAt: 0 });
  const [station, setStation] = useState<ValidationStation | null>(null);
  const [loading, setLoading] = useState(true);
  const [cameraLoading, setCameraLoading] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [manualToken, setManualToken] = useState("");
  const [result, setResult] = useState<StationValidationResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [incidentForm, setIncidentForm] = useState({ message: "", qr_token: "" });
  const [incidentMsg, setIncidentMsg] = useState("");

  const stopScanner = useCallback(async () => {
    const scanner = scannerRef.current;
    if (!scanner) return;

    try {
      if (scanner.isScanning) {
        await scanner.stop();
      }
      scanner.clear();
    } catch (error) {
      console.error("Error cerrando camara:", error);
    } finally {
      scannerRef.current = null;
      setIsScanning(false);
    }
  }, []);

  const validateToken = useCallback(async (qrToken: string) => {
    const normalizedToken = qrToken.trim();
    if (!normalizedToken || scanPendingRef.current) return;

    const now = Date.now();
    if (
      lastScanRef.current.token === normalizedToken &&
      now - lastScanRef.current.scannedAt < SAME_CODE_COOLDOWN_MS
    ) {
      return;
    }

    scanPendingRef.current = true;
    lastScanRef.current = { token: normalizedToken, scannedAt: now };
    setErrorMsg("");

    try {
      const response = await validateTicketFromStationRequest({
        qr_token: normalizedToken,
      });
      setResult(response);
      setManualToken("");
    } catch (error) {
      console.error("Error validando entrada:", error);
      setResult({
        valid: false,
        message: getApiErrorMessage(
          error,
          "No se pudo comprobar la entrada. Revisa la conexion."
        ),
        ticket: null,
      });
    } finally {
      scanPendingRef.current = false;
    }
  }, []);

  const startScanner = async () => {
    if (cameraLoading || isScanning) return;

    try {
      setCameraLoading(true);
      setResult(null);
      setErrorMsg("");
      const scanner = new Html5Qrcode(READER_ID);
      scannerRef.current = scanner;
      await scanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 230, height: 230 } },
        (decodedText) => validateToken(decodedText),
        () => {}
      );
      setIsScanning(true);
    } catch (error) {
      console.error("Error abriendo camara:", error);
      scannerRef.current = null;
      setErrorMsg(
        "No se pudo abrir la camara. Comprueba el permiso del navegador o usa el campo manual."
      );
    } finally {
      setCameraLoading(false);
    }
  };

  useEffect(() => {
    const loadStation = async () => {
      try {
        const response = await getCurrentValidationStationRequest();
        setStation(response.station);
      } catch {
        router.replace(ROUTES.validatorActivate);
      } finally {
        setLoading(false);
      }
    };

    loadStation();
    return () => {
      stopScanner();
    };
  }, [router, stopScanner]);

  const closeStation = async () => {
    await stopScanner();
    await logoutValidationStationRequest();
    router.replace(ROUTES.validatorActivate);
  };

  const submitManualToken = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    validateToken(manualToken.trim());
  };

  const submitIncident = async (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();

    try {
      setIncidentMsg("");
      await reportValidationStationIncidentRequest({
        message: incidentForm.message,
        qr_token: incidentForm.qr_token || null,
      });
      setIncidentForm({ message: "", qr_token: "" });
      setIncidentMsg("Incidencia registrada");
    } catch (error) {
      console.error("Error registrando incidencia:", error);
      setIncidentMsg(getApiErrorMessage(error, "No se pudo registrar la incidencia"));
    }
  };

  if (loading) {
    return <main className={styles.page}><p>Cargando puesto...</p></main>;
  }

  return (
    <main className={styles.scannerPage}>
      <header className={styles.scannerHeader}>
        <div>
          <p className={styles.eyebrow}>Control de acceso</p>
          <h1 className={styles.scannerTitle}>{station?.name}</h1>
          <p className={styles.stationMeta}>{station?.event_title}</p>
          <p className={styles.stationMeta}>{station?.session_label}</p>
        </div>
        <Button type="button" onClick={closeStation}>
          Cerrar puesto
        </Button>
      </header>

      <section className={styles.scannerBody}>
        {result ? (
          <div className={result.valid ? styles.successResult : styles.errorResult}>
            <span className={styles.resultSymbol}>{result.valid ? "OK" : "X"}</span>
            <h2>{result.valid ? "Entrada valida" : "Entrada rechazada"}</h2>
            <p>{result.message}</p>
            {result.ticket ? (
              <div className={styles.ticketResultMeta}>
                <small>{result.ticket.ticket_type?.name} - {result.ticket.ticket_code}</small>
                <small>Estado: {result.ticket.status}</small>
                {result.ticket.session ? (
                  <small>
                    Sesion: {result.ticket.session.location_name} -{" "}
                    {new Date(result.ticket.session.starts_at).toLocaleString()}
                  </small>
                ) : null}
              </div>
            ) : null}
            <Button className={styles.resultAction} type="button" onClick={() => setResult(null)}>
              Limpiar aviso
            </Button>
          </div>
        ) : null}

        <div className={styles.readerFrame}>
          <div id={READER_ID} className={styles.reader} />
          {!isScanning ? (
            <Button
              className={styles.cameraAction}
              variant="primary"
              type="button"
              disabled={cameraLoading}
              onClick={startScanner}
            >
              {cameraLoading ? "Abriendo camara..." : "Abrir camara"}
            </Button>
          ) : null}
        </div>
        {errorMsg ? <p className={styles.error}>{errorMsg}</p> : null}
        <form className={styles.manualForm} onSubmit={submitManualToken}>
          <label className={styles.field}>
            Codigo manual
            <input
              className={styles.input}
              value={manualToken}
              onChange={(event) => setManualToken(event.target.value)}
              placeholder="Pega o escribe el codigo"
              required
            />
          </label>
          <Button type="submit">
            Comprobar codigo
          </Button>
        </form>

        <details className={styles.incidentBox}>
          <summary>Registrar incidencia</summary>
          <form className={styles.incidentForm} onSubmit={submitIncident}>
            <label className={styles.field}>
              Codigo de la entrada
              <input
                className={styles.input}
                value={incidentForm.qr_token}
                onChange={(event) =>
                  setIncidentForm((current) => ({
                    ...current,
                    qr_token: event.target.value,
                  }))
                }
                placeholder="Opcional"
              />
            </label>
            <label className={styles.field}>
              Que ha ocurrido
              <textarea
                className={styles.input}
                value={incidentForm.message}
                onChange={(event) =>
                  setIncidentForm((current) => ({
                    ...current,
                    message: event.target.value,
                  }))
                }
                required
              />
            </label>
            {incidentMsg ? <p className={styles.incidentMsg}>{incidentMsg}</p> : null}
            <Button type="submit">
              Guardar incidencia
            </Button>
          </form>
        </details>
      </section>
    </main>
  );
}
