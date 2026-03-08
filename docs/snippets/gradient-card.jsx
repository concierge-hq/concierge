import { useMemo } from "react";

export const GradientCard = ({
  className,
  title,
  description,
  icon,
  href,
  color = 270,
}) => {
  const hue = typeof color === "number" ? color : 270;

  return (
    <a
      href={href}
      className={`group relative overflow-hidden rounded-2xl no-underline block transition-all duration-500 hover:-translate-y-0.5 ${className || ""}`}
      style={{ minHeight: "220px" }}
    >
      {/* Base: very soft, light gradient */}
      <div
        className="absolute inset-0 w-full h-full transition-all duration-700 group-hover:scale-[1.02]"
        style={{
          background: `linear-gradient(145deg,
            oklch(0.96 0.02 ${hue}) 0%,
            oklch(0.92 0.04 ${hue + 10}) 40%,
            oklch(0.88 0.05 ${hue + 15}) 100%)`,
        }}
      />

      {/* Subtle top-left glow */}
      <div
        className="absolute inset-0 w-full h-full"
        style={{
          background: `radial-gradient(ellipse at 20% 0%, oklch(0.98 0.01 ${hue}) 0%, transparent 50%)`,
        }}
      />

      {/* Very faint bottom-right warmth */}
      <div
        className="absolute inset-0 w-full h-full"
        style={{
          background: `radial-gradient(ellipse at 90% 90%, oklch(0.90 0.04 ${hue + 20}) 0%, transparent 45%)`,
        }}
      />

      {/* Subtle border — light inner stroke effect */}
      <div
        className="absolute inset-0 w-full h-full rounded-2xl"
        style={{
          boxShadow: `inset 0 0 0 1px rgba(255,255,255,0.5), inset 0 1px 0 0 rgba(255,255,255,0.6)`,
        }}
      />

      {/* Outer shadow */}
      <div
        className="absolute inset-0 w-full h-full rounded-2xl transition-shadow duration-500 group-hover:shadow-lg"
        style={{
          boxShadow: `0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)`,
        }}
      />

      {/* Content */}
      <div className="relative z-10 p-7 flex flex-col justify-between h-full">
        <div
          className="text-2xl w-10 h-10 flex items-center justify-center rounded-xl"
          style={{
            background: `linear-gradient(135deg, oklch(0.94 0.03 ${hue}), oklch(0.88 0.05 ${hue + 10}))`,
            boxShadow: `0 1px 3px rgba(0,0,0,0.06)`,
          }}
        >
          {icon}
        </div>
        <div className="mt-auto pt-8">
          <h3
            className="font-semibold text-lg tracking-tight"
            style={{ color: `oklch(0.25 0.02 ${hue})` }}
          >
            {title}
          </h3>
          <p
            className="text-sm mt-1.5 leading-relaxed"
            style={{ color: `oklch(0.45 0.02 ${hue})` }}
          >
            {description}
          </p>
        </div>
      </div>
    </a>
  );
};

/* Dark mode variant */
export const GradientCardDark = ({
  className,
  title,
  description,
  icon,
  href,
  color = 270,
}) => {
  const hue = typeof color === "number" ? color : 270;

  return (
    <a
      href={href}
      className={`group relative overflow-hidden rounded-2xl no-underline block transition-all duration-500 hover:-translate-y-0.5 ${className || ""}`}
      style={{ minHeight: "220px" }}
    >
      {/* Base: very dark, barely tinted */}
      <div
        className="absolute inset-0 w-full h-full transition-all duration-700 group-hover:scale-[1.02]"
        style={{
          background: `linear-gradient(145deg,
            oklch(0.18 0.015 ${hue}) 0%,
            oklch(0.15 0.02 ${hue + 10}) 40%,
            oklch(0.13 0.025 ${hue + 15}) 100%)`,
        }}
      />

      {/* Subtle top-left highlight */}
      <div
        className="absolute inset-0 w-full h-full"
        style={{
          background: `radial-gradient(ellipse at 20% 0%, oklch(0.22 0.02 ${hue}) 0%, transparent 50%)`,
        }}
      />

      {/* Border */}
      <div
        className="absolute inset-0 w-full h-full rounded-2xl"
        style={{
          boxShadow: `inset 0 0 0 1px rgba(255,255,255,0.06), inset 0 1px 0 0 rgba(255,255,255,0.08)`,
        }}
      />

      {/* Content */}
      <div className="relative z-10 p-7 flex flex-col justify-between h-full">
        <div
          className="text-2xl w-10 h-10 flex items-center justify-center rounded-xl"
          style={{
            background: `linear-gradient(135deg, oklch(0.22 0.02 ${hue}), oklch(0.18 0.03 ${hue + 10}))`,
            boxShadow: `inset 0 0 0 1px rgba(255,255,255,0.08)`,
          }}
        >
          {icon}
        </div>
        <div className="mt-auto pt-8">
          <h3
            className="font-semibold text-lg tracking-tight"
            style={{ color: `oklch(0.92 0.02 ${hue})` }}
          >
            {title}
          </h3>
          <p
            className="text-sm mt-1.5 leading-relaxed"
            style={{ color: `oklch(0.65 0.02 ${hue})` }}
          >
            {description}
          </p>
        </div>
      </div>
    </a>
  );
};
