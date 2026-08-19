import { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  small?: boolean;
}

export function Button({ variant = "primary", small, className = "", ...rest }: Props) {
  const classes = ["btn", `btn--${variant}`, small ? "btn--sm" : "", className].filter(Boolean).join(" ");
  return <button className={classes} {...rest} />;
}
