import PageContainer from "../../../components/ui/PageContainer";

import styles from "./FaqPage.module.css";

const faqItems = [
  {
    question: "He comprado entradas, pero no he recibido el email. ¿Qué hago?",
    answer: (
      <>
        Revisa las carpetas de spam, promociones y correo no deseado. Si iniciaste
        sesión, también puedes consultar y descargar tus entradas desde “Mis
        entradas”. Si siguen sin aparecer, contacta con soporte indicando el email
        utilizado y el evento para que podamos localizar la compra.
      </>
    ),
  },
  {
    question: "¿Necesito imprimir las entradas?",
    answer: (
      <>
        No es necesario. Puedes mostrar el PDF o el código QR desde el móvil. Te
        recomendamos llevarlo descargado, subir el brillo de la pantalla y evitar
        capturas recortadas para facilitar la lectura en el acceso.
      </>
    ),
  },
  {
    question: "El pago con tarjeta ha sido rechazado. ¿Qué puede haber ocurrido?",
    answer: (
      <>
        La autorización final depende de la entidad bancaria y del proveedor de
        pago. Comprueba los datos de la tarjeta, el saldo disponible y cualquier
        confirmación de seguridad solicitada por tu banco. Si el problema continúa,
        guarda el mensaje o código de error y consúltalo con tu entidad o con soporte.
      </>
    ),
  },
  {
    question: "El pago falló y las entradas aparecen ocupadas. ¿Las he comprado?",
    answer: (
      <>
        Un pago fallido no confirma la compra ni genera el cobro. Durante el checkout,
        las entradas se reservan temporalmente para evitar ventas simultáneas. Si la
        operación no termina, volverán a estar disponibles cuando finalice el periodo
        de reserva mostrado durante la compra.
      </>
    ),
  },
  {
    question: "No puedo asistir. ¿Puedo devolver o cambiar mis entradas?",
    answer: (
      <>
        Como norma general, las entradas confirmadas no se cambian ni se reembolsan
        por motivos personales. Las excepciones dependen de la cancelación del evento,
        de las condiciones anunciadas por el organizador y de la normativa aplicable.
        Consulta siempre las condiciones concretas de tu compra.
      </>
    ),
  },
  {
    question: "¿Qué sucede si el evento se cancela o se aplaza?",
    answer: (
      <>
        Te informaremos por los datos de contacto asociados a la compra. En caso de
        cancelación, se comunicarán los plazos y el procedimiento de devolución. Cuando
        corresponda un reembolso, se tramitará normalmente al mismo método de pago usado
        en la compra.
      </>
    ),
  },
  {
    question: "Las entradas son para otra persona. ¿Puede utilizarlas?",
    answer: (
      <>
        Sí, salvo que el evento indique expresamente que las entradas son nominativas
        o exija identificar a cada asistente. Los datos del comprador se solicitan para
        gestionar la operación y poder comunicar cualquier incidencia.
      </>
    ),
  },
  {
    question: "¿Es seguro pagar en la plataforma?",
    answer: (
      <>
        El pago se procesa mediante un proveedor especializado y la plataforma no
        almacena los datos completos de tu tarjeta. Comprueba siempre que estás en la
        dirección correcta antes de introducir información de pago y no compartas los
        códigos de verificación de tu banco.
      </>
    ),
  },
  {
    question: "¿Puedo compartir una entrada o su código QR?",
    answer: (
      <>
        No compartas el QR públicamente. Cada entrada permite un único acceso válido y
        una copia podría ser utilizada antes que la entrada original. Si vas a regalarla,
        envíala únicamente a la persona que asistirá.
      </>
    ),
  },
  {
    question: "¿Dónde consulto las condiciones de acceso de un evento?",
    answer: (
      <>
        Revisa la descripción y la información publicada en la ficha del evento. Las
        normas sobre edad mínima, accesibilidad, horarios o documentación pueden variar
        según el recinto y el organizador.
      </>
    ),
  },
];

export default function FaqPage() {
  return (
    <PageContainer title="Preguntas frecuentes">
      <div className={styles.content}>
        <p className={styles.intro}>
          Estas son las consultas más habituales durante la compra y el uso de las
          entradas. Abre una pregunta para consultar la respuesta.
        </p>

        <div className={styles.list}>
          {faqItems.map((item) => (
            <details className={styles.item} key={item.question}>
              <summary>{item.question}</summary>
              <div className={styles.answer}>{item.answer}</div>
            </details>
          ))}
        </div>
      </div>
    </PageContainer>
  );
}
