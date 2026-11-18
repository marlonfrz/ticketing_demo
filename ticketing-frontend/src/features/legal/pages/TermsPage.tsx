import PageContainer from "../../../components/ui/PageContainer";

import styles from "./LegalPage.module.css";

export default function TermsPage() {
  return (
    <PageContainer title="Condiciones de uso y compra">
      <section className={styles.content}>
        <p className={styles.intro}>
          Estas condiciones regulan el acceso, uso de la plataforma y compra de
          entradas a traves del servicio.
        </p>

        <div className={styles.section}>
          <h2>Identificacion del servicio</h2>
          <p>
            La plataforma permite publicar eventos, seleccionar sesiones,
            comprar entradas, recibirlas en PDF, gestionar invitaciones,
            solicitar validadores y consultar informacion asociada a pedidos y
            ventas.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Cuenta de usuario</h2>
          <p>
            La creacion de una cuenta permite gestionar datos de acceso,
            consultar pedidos asociados y recuperar entradas adquiridas. La
            persona usuaria debe facilitar datos reales y mantener segura su
            contrasena.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Usuarios invitados</h2>
          <p>
            Se podran realizar compras sin crear cuenta. En ese caso se
            solicitaran los datos necesarios para enviar la entrada, identificar
            la compra y prestar soporte si existe una incidencia con el correo o
            con la descarga del PDF.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Promotores</h2>
          <p>
            Los promotores podran crear eventos y sesiones, pero la publicacion
            dependera de la revision y aprobacion administrativa. La informacion
            enviada debe ser veraz, completa y respetar la normativa aplicable
            al evento.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Compra de entradas</h2>
          <p>
            Al completar el pago, el comprador recibira sus entradas en formato
            PDF en el correo indicado durante la compra. Tambien podra
            descargarlas desde las vistas habilitadas cuando corresponda.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Precio y gastos de gestion</h2>
          <p>
            El precio final podra incluir el importe de la entrada definido para
            el evento y los gastos de gestion aplicables. El desglose se
            mostrara antes de continuar con el pago.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Validez de la entrada</h2>
          <p>
            Cada entrada contiene un codigo QR unico. La entrada solo sera
            valida para el evento, sesion, fecha, lugar y tipo de entrada
            indicados en el PDF.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Validacion de acceso</h2>
          <p>
            La entrada podra ser validada una sola vez, salvo configuracion
            especifica. Si el QR no corresponde a la sesion, ya fue usado, esta
            cancelado o no es valido, el sistema mostrara el motivo del rechazo
            al personal autorizado.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Datos introducidos durante la compra</h2>
          <p>
            El comprador es responsable de revisar el email, telefono y datos
            introducidos antes de pagar. Si detecta un error, debera contactar
            con soporte aportando informacion suficiente para verificar la
            compra.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Cambios, cancelaciones y devoluciones</h2>
          <p>
            Las condiciones especificas de cambios, cancelaciones o devoluciones
            podran depender del evento, del promotor correspondiente y de la
            normativa aplicable.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Conductas no permitidas</h2>
          <ul>
            <li>Intentar acceder a zonas de administracion sin autorizacion.</li>
            <li>Manipular entradas, codigos QR, sesiones o localizadores.</li>
            <li>Realizar compras fraudulentas o con datos falsos.</li>
            <li>Interferir en el funcionamiento de la plataforma.</li>
            <li>Crear eventos o solicitudes masivas con finalidad abusiva.</li>
          </ul>
        </div>

        <div className={styles.section}>
          <h2>Datos pendientes de completar</h2>
          <p>
            Estas condiciones deberan revisarse con los datos reales del titular,
            politica final de devoluciones, legislacion aplicable y canales de
            soporte:
            {" "}
            <span className={styles.placeholder}>[DATOS LEGALES DEFINITIVOS]</span>.
          </p>
        </div>
      </section>
    </PageContainer>
  );
}

