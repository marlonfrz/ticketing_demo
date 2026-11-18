import PageContainer from "../../../components/ui/PageContainer";

import styles from "./LegalPage.module.css";

export default function AboutPage() {
  return (
    <PageContainer title="Sobre nosotros">
      <section className={styles.content}>
        <p className={styles.intro}>
          Ticketing Demo es una plataforma para crear eventos, organizar sesiones,
          vender entradas, generar invitaciones y validar accesos mediante
          codigos QR.
        </p>

        <div className={styles.grid}>
          <article className={styles.panel}>
            <h3>Para compradores</h3>
            <p>
              Compra de entradas con o sin cuenta, descarga del PDF, recepcion
              por email y recuperacion desde el perfil cuando proceda.
            </p>
          </article>
          <article className={styles.panel}>
            <h3>Para promotores</h3>
            <p>
              Gestion de eventos, sesiones, aforos, tipos de entrada,
              invitaciones, RRPP y resumenes de ventas.
            </p>
          </article>
          <article className={styles.panel}>
            <h3>Para administradores</h3>
            <p>
              Revision de eventos, control de publicaciones, tarifas de gestion,
              usuarios, validadores y actividad operativa.
            </p>
          </article>
        </div>

        <div className={styles.section}>
          <h2>Nuestro enfoque</h2>
          <p>
            La herramienta esta pensada para que el comprador pueda adquirir una
            entrada con pocos pasos y para que el equipo operativo mantenga el
            control de revision, publicacion, venta y validacion de cada sesion.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Flujo de trabajo</h2>
          <ul>
            <li>El promotor prepara el evento, sus sesiones y entradas.</li>
            <li>El contenido se envia a revision antes de poder publicarse.</li>
            <li>El administrador aprueba, cancela o devuelve a revision.</li>
            <li>Las sesiones publicadas quedan disponibles para la venta.</li>
            <li>Las entradas se validan en puerta con puestos temporales.</li>
          </ul>
        </div>

        <div className={styles.section}>
          <h2>Datos pendientes de completar</h2>
          <dl className={styles.dataList}>
            <div>
              <dt>Marca comercial definitiva</dt>
              <dd>
                <span className={styles.placeholder}>[NOMBRE DE MARCA]</span>
              </dd>
            </div>
            <div>
              <dt>Empresa o titular responsable</dt>
              <dd>
                <span className={styles.placeholder}>[TITULARIDAD]</span>
              </dd>
            </div>
            <div>
              <dt>Dominio publico</dt>
              <dd>
                <span className={styles.placeholder}>[DOMINIO]</span>
              </dd>
            </div>
          </dl>
        </div>

        <div className={styles.section}>
          <h2>Compromiso de servicio</h2>
          <p>
            Buscamos que cada entrada tenga trazabilidad suficiente para
            localizar su pedido, su sesion, su comprador, su estado de
            validacion y el canal por el que se genero la venta.
          </p>
        </div>

        <p className={styles.note}>
          Esta pagina es una simulacion para desarrollo. Antes de produccion se
          debera adaptar con la identidad real de la empresa y el tono final de
          comunicacion de la marca.
        </p>
      </section>
    </PageContainer>
  );
}
