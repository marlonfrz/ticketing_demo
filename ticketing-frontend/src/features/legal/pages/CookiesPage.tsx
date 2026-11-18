import PageContainer from "../../../components/ui/PageContainer";

import styles from "./LegalPage.module.css";

export default function CookiesPage() {
  return (
    <PageContainer title="Politica de cookies">
      <section className={styles.content}>
        <p className={styles.intro}>
          Esta politica explica de forma general como puede usar cookies o
          tecnologias similares la plataforma.
        </p>

        <div className={styles.section}>
          <h2>Resumen de uso</h2>
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Tipo</th>
                  <th>Finalidad</th>
                  <th>Gestion</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Tecnicas necesarias</td>
                  <td>Sesion de usuario, seguridad, checkout y validacion.</td>
                  <td>Necesarias para prestar el servicio.</td>
                </tr>
                <tr>
                  <td>Proveedor de pagos</td>
                  <td>Procesar pagos y prevenir fraude.</td>
                  <td>Depende del proveedor configurado.</td>
                </tr>
                <tr>
                  <td>Analitica</td>
                  <td>Medicion de uso y mejora del producto.</td>
                  <td>
                    <span className={styles.placeholder}>
                      [PENDIENTE DE ACTIVAR]
                    </span>
                  </td>
                </tr>
                <tr>
                  <td>Marketing</td>
                  <td>Campanas, conversiones o anuncios.</td>
                  <td>
                    <span className={styles.placeholder}>
                      [PENDIENTE DE DEFINIR]
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div className={styles.section}>
          <h2>Cookies necesarias</h2>
          <p>
            Podemos utilizar cookies o almacenamiento local necesarios para
            mantener sesiones, recordar datos tecnicos de navegacion, procesar
            compras, activar puestos de validacion y proteger el funcionamiento
            basico de la plataforma.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Almacenamiento local</h2>
          <p>
            La aplicacion puede utilizar almacenamiento del navegador para
            recordar informacion tecnica, mantener contexto de navegacion o
            mejorar la experiencia durante formularios y procesos de compra.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Cookies de terceros</h2>
          <p>
            Algunos proveedores externos, como pasarelas de pago, pueden usar
            sus propias tecnologias para prestar sus servicios y prevenir
            fraude. Su uso dependera de la configuracion final de produccion.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Gestion</h2>
          <p>
            Puedes configurar o bloquear cookies desde el navegador. Algunas
            funciones, como iniciar sesion, completar compras o validar
            entradas, pueden dejar de funcionar correctamente si bloqueas
            almacenamiento tecnico necesario.
          </p>
        </div>

        <p className={styles.note}>
          Si se activan analitica, publicidad o herramientas de marketing, habra
          que incorporar banner de consentimiento y registrar las preferencias
          del usuario.
        </p>
      </section>
    </PageContainer>
  );
}
