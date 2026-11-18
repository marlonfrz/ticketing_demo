import PageContainer from "../../../components/ui/PageContainer";

import styles from "./LegalPage.module.css";

export default function ContactPage() {
  return (
    <PageContainer title="Contacto y soporte">
      <section className={styles.content}>
        <p className={styles.intro}>
          Si tienes una incidencia con una compra, una entrada o un evento,
          contacta con soporte aportando la informacion necesaria para localizar
          el pedido.
        </p>

        <div className={styles.section}>
          <h2>Canales de contacto</h2>
          <dl className={styles.dataList}>
            <div>
              <dt>Soporte general</dt>
              <dd>
                <span className={styles.placeholder}>[soporte@dominio.com]</span>
              </dd>
            </div>
            <div>
              <dt>Consultas legales o privacidad</dt>
              <dd>
                <span className={styles.placeholder}>[legal@dominio.com]</span>
              </dd>
            </div>
            <div>
              <dt>Horario de atencion</dt>
              <dd>
                <span className={styles.placeholder}>[HORARIO DE SOPORTE]</span>
              </dd>
            </div>
          </dl>
        </div>

        <div className={styles.section}>
          <h2>Soporte para compradores</h2>
          <p>
            Para revisar una compra podemos pedirte el email, telefono,
            localizador de entrada, numero de pedido o el evento relacionado.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Que datos conviene incluir</h2>
          <ul className={styles.contactList}>
            <li>
              <strong>Compras:</strong> email usado, telefono, evento, fecha de
              la sesion y localizador si lo tienes.
            </li>
            <li>
              <strong>Promotores:</strong> nombre del evento, sesion afectada y
              descripcion clara de la incidencia.
            </li>
            <li>
              <strong>Validacion:</strong> puesto de validacion, hora aproximada
              del error y mensaje mostrado en pantalla.
            </li>
          </ul>
        </div>

        <div className={styles.section}>
          <h2>Tiempos de respuesta</h2>
          <p>
            El tiempo de respuesta dependera del volumen de solicitudes y de la
            cercania del evento. Las incidencias relacionadas con acceso a un
            evento activo tendran prioridad operativa.
          </p>
        </div>

        <p className={styles.note}>
          Esta vista debe completarse con correos reales, horario de soporte y
          politica interna de prioridad antes de publicar la plataforma.
        </p>
      </section>
    </PageContainer>
  );
}
