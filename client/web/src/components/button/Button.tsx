import React, { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonProps = {
  children: ReactNode;
  className?: string;
  disabled?: boolean;
  state?: "primary" | "secondary" | "dropdown" | "destructive";
  size?: "small" | "medium" | "large";
} & ButtonHTMLAttributes<HTMLButtonElement>;

export const Button: React.FC<ButtonProps> = ({
  children,
  className,
  disabled,
  state = "primary",
  size = "small",
  ...allProps
}) => {
  let buttonStyles;
  switch (state) {
    case "secondary":
      buttonStyles =
        "bg-transparent text-cerebras-control-text hover:text-cerebras-accent-text-active";
      break;

    case "dropdown":
      "bg-white rounded-full text-cerebras-accent-text hover:text-cerebras-accent-text-active";
      break;

    case "destructive":
      buttonStyles = "bg-[#FFD1CC] text-cerebras-action-text";
      break;

    default:
      buttonStyles =
        "bg-cerebras-button-bg hover:bg-cerebras-button-bg/80 text-cerebras-button-text hover:border-cerebras-action-text rounded-[20px] border-[1px] uppercase";
      break;
  }

  let sizeStyles;
  switch (size) {
    case "large":
      sizeStyles = "text-lg px-6 py-4 font-semibold tracking-wider";
      break;

    case "medium":
      sizeStyles = "text-sm px-2 py-2";
      break;

    default: //small
      sizeStyles = "text-xs px-2 py-[6px]";
      break;
  }

  return (
    <button
      className={`active:translate-y-[2px] active:scale-[0.99] hover:-translate-y-[2px] flex flex-row ${
        disabled ? "pointer-events-none" : ""
      } ${size} font-mono ${buttonStyles} ${sizeStyles} transition-all ease-out duration-250 ${className}`}
      {...allProps}
    >
      {children}
    </button>
  );
};
