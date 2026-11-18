import type { ReactNode } from "react";

import Button, { type ButtonProps } from "./Button";
import styles from "./IconButton.module.css";

type IconButtonProps = Omit<ButtonProps, "children"> & {
  appearance?: "default" | "overlay";
  children: ReactNode;
  label: string;
};

export default function IconButton({
  appearance = "default",
  children,
  className,
  label,
  size = "medium",
  title,
  ...props
}: IconButtonProps) {
  return (
    <Button
      className={[styles.iconButton, styles[size], styles[appearance], className]
        .filter(Boolean)
        .join(" ")}
      aria-label={label}
      size={size}
      title={title ?? label}
      {...props}
    >
      {children}
    </Button>
  );
}
