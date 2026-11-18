import styles from "./PasswordRequirements.module.css";
import { getPasswordChecks, type PasswordChecks } from "../utils/passwordValidation";

const requirements: Array<[keyof PasswordChecks, string]> = [
  ["length", "12 caracteres como minimo"],
  ["lowercase", "Una letra minúscula"],
  ["uppercase", "Una letra mayúscula"],
  ["number", "Un número"],
  ["special", "Un carácter especial"],
];

export default function PasswordRequirements({ password }: { password: string }) {
  const checks = getPasswordChecks(password);

  return (
    <div className={styles.box}>
      <strong>La contraseña necesita:</strong>
      <ul className={styles.list}>
        {requirements.map(([key, label]) => (
          <li className={checks[key] ? styles.valid : styles.pending} key={key}>
            {label}
          </li>
        ))}
      </ul>
    </div>
  );
}
