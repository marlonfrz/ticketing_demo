import type { ButtonHTMLAttributes } from "react";

import styles from "./Button.module.css";

export type ButtonVariant =
  | "primary"
  | "primarySoft"
  | "secondary"
  | "danger"
  | "warning"
  | "ghost";
export type ButtonSize = "small" | "medium";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
};

export function getButtonClassName({
  className,
  variant = "secondary",
  size = "medium",
}: {
  className?: string | undefined;
  variant?: ButtonVariant | undefined;
  size?: ButtonSize | undefined;
}) {
  return [styles.button, styles[variant], styles[size], className]
    .filter(Boolean)
    .join(" ");
}

export default function Button({
  className,
  variant = "secondary",
  size = "medium",
  type = "button",
  ...props
}: ButtonProps) {
  const classes = getButtonClassName({ className, variant, size });

  return <button className={classes} type={type} {...props} />;
}
