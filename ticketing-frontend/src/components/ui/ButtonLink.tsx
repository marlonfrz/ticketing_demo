import Link from "next/link";
import type { ComponentProps } from "react";

import {
  getButtonClassName,
  type ButtonSize,
  type ButtonVariant,
} from "./Button";

type ButtonLinkProps = Omit<ComponentProps<typeof Link>, "className"> & {
  className?: string | undefined;
  variant?: ButtonVariant;
  size?: ButtonSize;
};

export default function ButtonLink({
  className,
  variant = "secondary",
  size = "medium",
  ...props
}: ButtonLinkProps) {
  return (
    <Link
      className={getButtonClassName({ className, variant, size })}
      {...props}
    />
  );
}
