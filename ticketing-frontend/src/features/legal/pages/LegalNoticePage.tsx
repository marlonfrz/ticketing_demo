import PageContainer from "../../../components/ui/PageContainer";

import styles from "./LegalPage.module.css";

export default function LegalNoticePage() {
  return (
    <PageContainer title="Aviso legal">
      <section className={styles.content}>
        <p className={styles.intro}>
          Este aviso recoge informacion general sobre el titular de la
          plataforma y las condiciones basicas de acceso al sitio.
        </p>

        <div className={styles.section}>
          <h2>Titularidad</h2>
          <dl className={styles.dataList}>
            <div>
              <dt>Titular del sitio</dt>
              <dd>
                <span className={styles.placeholder}>[NOMBRE FISCAL]</span>
              </dd>
            </div>
            <div>
              <dt>NIF/CIF</dt>
              <dd>
                <span className={styles.placeholder}>[NIF O CIF]</span>
              </dd>
            </div>
            <div>
              <dt>Domicilio social</dt>
              <dd>
                <span className={styles.placeholder}>[DIRECCION FISCAL]</span>
              </dd>
            </div>
            <div>
              <dt>Email de contacto legal</dt>
              <dd>
                <span className={styles.placeholder}>[legal@dominio.com]</span>
              </dd>
            </div>
            <div>
              <dt>Dominio</dt>
              <dd>
                <span className={styles.placeholder}>[www.dominio.com]</span>
              </dd>
            </div>
          </dl>
        </div>

        <div className={styles.section}>
          <h2>Uso del sitio</h2>
          <p>
            La persona usuaria se compromete a utilizar la plataforma de forma
            licita, sin realizar acciones que puedan danar el servicio, alterar
            su funcionamiento o afectar a otros usuarios, promotores,
            validadores o administradores.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Responsabilidad</h2>
          <p>
            La plataforma facilita herramientas de publicacion, venta y
            validacion de entradas. La informacion concreta de cada evento,
            sesion, lugar, horario y condiciones particulares debera ser
            revisada por el promotor y por el administrador antes de su
            publicacion.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Propiedad intelectual</h2>
          <p>
            Los contenidos, marcas, textos, imagenes y elementos de la
            plataforma pertenecen a sus titulares correspondientes. No se
            permite su uso no autorizado fuera de los casos permitidos por la
            ley.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Enlaces externos</h2>
          <p>
            Algunas zonas pueden enlazar a servicios externos, como pasarelas de
            pago, mapas, proveedores de email o herramientas tecnicas. La
            plataforma no controla necesariamente el contenido ni las politicas
            de dichos servicios.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Legislacion y jurisdiccion</h2>
          <p>
            La legislacion aplicable y los tribunales competentes deberan
            completarse con el asesoramiento correspondiente:
            {" "}
            <span className={styles.placeholder}>[JURISDICCION]</span>.
          </p>
        </div>

        <p className={styles.note}>
          Este texto es una base tecnica para desarrollo. Debe revisarse con la
          informacion real del titular antes de salir a mercado.
        </p>
      </section>
    </PageContainer>
  );
}
