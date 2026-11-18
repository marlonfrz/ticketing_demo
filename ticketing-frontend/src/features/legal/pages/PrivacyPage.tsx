import PageContainer from "../../../components/ui/PageContainer";

import styles from "./LegalPage.module.css";

export default function PrivacyPage() {
  return (
    <PageContainer title="Politica de privacidad">
      <section className={styles.content}>
        <p className={styles.intro}>
          Esta politica explica que datos se tratan en la plataforma y con que
          finalidad general.
        </p>

        <div className={styles.section}>
          <h2>Responsable del tratamiento</h2>
          <dl className={styles.dataList}>
            <div>
              <dt>Responsable</dt>
              <dd>
                <span className={styles.placeholder}>[NOMBRE FISCAL]</span>
              </dd>
            </div>
            <div>
              <dt>Contacto de privacidad</dt>
              <dd>
                <span className={styles.placeholder}>[privacidad@dominio.com]</span>
              </dd>
            </div>
            <div>
              <dt>Domicilio</dt>
              <dd>
                <span className={styles.placeholder}>[DIRECCION FISCAL]</span>
              </dd>
            </div>
          </dl>
        </div>

        <div className={styles.section}>
          <h2>Datos tratados</h2>
          <ul>
            <li>Datos de cuenta: nombre, email, telefono, contrasena cifrada y rol.</li>
            <li>Datos de compra: comprador, telefono, email, pedido, entradas y localizadores.</li>
            <li>Datos de eventos: promotor, sesiones, ubicaciones, tickets, aforos e imagenes.</li>
            <li>Datos de validacion: puesto, sesion, resultado, hora y usuario responsable.</li>
            <li>Datos de RRPP: nombre, telefono, email opcional y ventas atribuidas.</li>
            <li>Comunicaciones de soporte y solicitudes administrativas.</li>
          </ul>
        </div>

        <div className={styles.section}>
          <h2>Finalidades</h2>
          <p>
            Los datos se utilizan para gestionar pedidos, enviar entradas,
            validar accesos, atender incidencias, permitir recuperacion de
            entradas, administrar eventos y cumplir obligaciones legales
            aplicables.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Base juridica</h2>
          <p>
            El tratamiento puede basarse en la ejecucion de la compra, el
            cumplimiento de obligaciones legales, el interes legitimo para
            seguridad y prevencion de fraude, y el consentimiento cuando se
            trate de comunicaciones comerciales o preferencias opcionales.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Compras sin cuenta</h2>
          <p>
            Para compras como invitado se solicitan nombre, email y telefono. El
            telefono se usa como dato adicional de verificacion si el comprador
            necesita soporte, corregir un correo o recuperar sus entradas.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Pagos y proveedores</h2>
          <p>
            Los datos de pago son tratados por el proveedor de pagos. La
            plataforma conserva las referencias necesarias para relacionar el
            pago con el pedido, sin almacenar datos completos de tarjeta.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Conservacion</h2>
          <p>
            Los datos se conservaran durante el tiempo necesario para prestar el
            servicio, atender incidencias, justificar operaciones y cumplir las
            obligaciones legales aplicables. Los plazos concretos quedan
            pendientes de definir:
            {" "}
            <span className={styles.placeholder}>[PLAZOS DE CONSERVACION]</span>.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Derechos</h2>
          <p>
            La persona interesada podra solicitar acceso, rectificacion,
            supresion, oposicion, limitacion y portabilidad cuando corresponda,
            escribiendo a:
            {" "}
            <span className={styles.placeholder}>[privacidad@dominio.com]</span>.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Seguridad</h2>
          <p>
            La plataforma debera aplicar medidas tecnicas y organizativas para
            proteger cuentas, pedidos, tokens, entradas, validadores y datos de
            contacto. Estas medidas se completaran con la configuracion final de
            produccion.
          </p>
        </div>

        <div className={styles.section}>
          <h2>Comunicaciones comerciales</h2>
          <p>
            Solo se enviaran comunicaciones promocionales cuando la persona haya
            otorgado su consentimiento o exista otra base legitimadora aplicable.
            Este consentimiento podra retirarse cuando se habilite el mecanismo
            correspondiente.
          </p>
        </div>

        <p className={styles.note}>
          Antes de produccion se deberan completar responsable del tratamiento,
          datos de contacto, plazos de conservacion, encargados de tratamiento y
          canales para ejercer derechos.
        </p>
      </section>
    </PageContainer>
  );
}

