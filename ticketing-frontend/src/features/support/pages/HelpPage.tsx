import Link from "next/link";

import PageContainer from "../../../components/ui/PageContainer";
import { ROUTES } from "../../../routes/paths";
import { SUPPORT_EMAIL } from "../config";

import styles from "./HelpPage.module.css";

export default function HelpPage() {
  return (
    <PageContainer title="¿Necesitas ayuda?">
      <div className={styles.content}>
        <p className={styles.lead}>
          Queremos ayudarte a resolver cualquier incidencia con tu compra, tus
          entradas o el acceso a un evento.
        </p>

        <section className={styles.section}>
          <h2>Consulta primero las preguntas frecuentes</h2>
          <p>
            Hemos reunido las respuestas a los problemas más habituales sobre
            pagos, entradas, reservas y cancelaciones.
          </p>
          <Link className={styles.link} href={ROUTES.faq}>
            Ver preguntas frecuentes
          </Link>
        </section>

        <section className={styles.section}>
          <h2>Contacta con soporte</h2>
          <p>
            Si no encuentras la respuesta, escríbenos a{" "}
            <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>. Incluye el
            nombre del evento y el localizador de la compra o entrada cuando lo
            tengas para que podamos ayudarte más rápido.
          </p>
        </section>

        <section className={styles.section}>
          <h2>¿Quieres organizar un evento?</h2>
          <p>
            Las propuestas de nuevos eventos se gestionan desde un formulario
            específico para que lleguen directamente al equipo adecuado.
          </p>
          <Link className={styles.link} href={ROUTES.organize}>
            Enviar una propuesta
          </Link>
        </section>
      </div>
    </PageContainer>
  );
}
