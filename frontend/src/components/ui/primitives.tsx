"use client";

import React from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

/* ---------- Button ---------- */
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
}

export function Button({
  className,
  variant = "primary",
  size = "md",
  ...props
}: ButtonProps) {
  const variants: Record<string, string> = {
    primary:
      "bg-[#244738] text-[#FAF8F4] hover:bg-[#1B362A] shadow-xs border border-[#244738]",
    secondary:
      "bg-[#EAF1ED] text-[#244738] hover:bg-[#DCE8E1] border border-[#CFE0D6]",
    outline:
      "bg-white text-[#19201C] hover:bg-[#FAF8F4] border border-[#DCD6C8]",
    ghost: "bg-transparent text-[#5C655F] hover:bg-[#EDE9DF] hover:text-[#19201C]",
    danger:
      "bg-[#A43E3A] text-white hover:bg-[#8A322F] border border-[#A43E3A]",
  };
  const sizes: Record<string, string> = {
    sm: "px-3 py-1.5 text-xs rounded-lg gap-1.5",
    md: "px-4 py-2 text-sm rounded-xl gap-2",
    lg: "px-5 py-2.5 text-sm rounded-xl gap-2",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center font-medium transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  );
}

/* ---------- Badge ---------- */
export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: React.ReactNode;
  tone?: "neutral" | "green" | "amber" | "red" | "blue" | "forest";
  className?: string;
}) {
  const tones: Record<string, string> = {
    neutral: "bg-[#EFECE4] text-[#4C554F] border-[#E0DBD0]",
    green: "bg-[#E8F2EC] text-[#22513C] border-[#C9DFD2]",
    forest: "bg-[#244738] text-[#FAF8F4] border-[#244738]",
    amber: "bg-[#FBF1E6] text-[#9A5229] border-[#EED3BA]",
    red: "bg-[#FBECEB] text-[#9A3430] border-[#EDC8C6]",
    blue: "bg-[#EBF2F8] text-[#2B5478] border-[#C8DCEB]",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2.5 py-0.5 text-[11px] font-medium rounded-full border whitespace-nowrap",
        tones[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

export function StatusBadge({ status }: { status?: string | null }) {
  if (!status) return <Badge tone="neutral">Unrecorded</Badge>;
  const map: Record<string, { label: string; tone: "green" | "amber" | "red" | "blue" | "neutral" }> = {
    present: { label: "Present", tone: "green" },
    online: { label: "Online", tone: "green" },
    approved: { label: "Approved", tone: "green" },
    confirmed: { label: "Confirmed", tone: "green" },
    resolved: { label: "Resolved", tone: "green" },
    active: { label: "Active", tone: "green" },
    late: { label: "Late Arrival", tone: "amber" },
    early_departure: { label: "Early Departure", tone: "amber" },
    late_and_early: { label: "Late & Early", tone: "amber" },
    pending: { label: "Pending Review", tone: "amber" },
    unreviewed: { label: "Needs Review", tone: "amber" },
    degraded: { label: "Degraded", tone: "amber" },
    reconnecting: { label: "Reconnecting", tone: "amber" },
    warning: { label: "Warning", tone: "amber" },
    on_leave: { label: "On Leave", tone: "blue" },
    acknowledged: { label: "Acknowledged", tone: "blue" },
    info: { label: "Info", tone: "blue" },
    absent: { label: "Absent", tone: "red" },
    offline: { label: "Offline", tone: "red" },
    obstructed: { label: "Obstructed", tone: "red" },
    rejected: { label: "Rejected", tone: "red" },
    critical: { label: "Critical", tone: "red" },
    false_positive: { label: "False Positive", tone: "neutral" },
    dismissed: { label: "Dismissed", tone: "neutral" },
    inactive: { label: "Inactive", tone: "neutral" },
  };
  const cfg = map[status] || { label: status.replace(/_/g, " "), tone: "neutral" as const };
  return <Badge tone={cfg.tone}>{cfg.label}</Badge>;
}

/* ---------- Card ---------- */
export function Card({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={cn("ws-card p-5", className)}>{children}</div>;
}

/* ---------- Inputs ---------- */
export function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-xl border border-[#DCD6C8] bg-[#FCFBF8] px-3.5 py-2 text-sm text-[#19201C] placeholder:text-[#8E9690] focus:border-[#244738] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#244738]/12 transition",
        className
      )}
      {...props}
    />
  );
}

export function Select({
  className,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "w-full rounded-xl border border-[#DCD6C8] bg-[#FCFBF8] px-3.5 py-2 text-sm text-[#19201C] focus:border-[#244738] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#244738]/12 transition",
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Textarea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "w-full rounded-xl border border-[#DCD6C8] bg-[#FCFBF8] px-3.5 py-2.5 text-sm text-[#19201C] placeholder:text-[#8E9690] focus:border-[#244738] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#244738]/12 transition",
        className
      )}
      {...props}
    />
  );
}

/* ---------- Modal ---------- */
export function Modal({
  open,
  onClose,
  title,
  subtitle,
  children,
  maxWidth = "max-w-lg",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  maxWidth?: string;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#19201C]/45 backdrop-blur-[2px] p-4">
      <div
        className={cn(
          "w-full bg-[#FCFBF8] border border-[#DFD9CC] rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col",
          maxWidth
        )}
      >
        <div className="flex items-start justify-between px-6 py-4 border-b border-[#E7E2D7] bg-white">
          <div>
            <h3 className="text-base font-semibold text-[#19201C]">{title}</h3>
            {subtitle && <p className="text-xs text-[#5C655F] mt-0.5">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#6C756F] hover:bg-[#EFECE4] hover:text-[#19201C] cursor-pointer"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-6 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}

/* ---------- Ethical Governance Banner ---------- */
export function EthicalNoticeBanner({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-xl border border-[#CFE0D6] bg-[#EFF5F1] text-[#234536] flex items-start gap-3",
        compact ? "px-3.5 py-2.5 text-xs" : "px-4 py-3 text-xs sm:text-sm"
      )}
    >
      <span className="mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full bg-[#244738]" />
      <p className="leading-relaxed">
        <strong className="font-semibold">Privacy-First Workplace Governance:</strong>{" "}
        Verified attendance (access cards, QR check-in, portal) is strictly separated from anonymous AI
        spatial occupancy sensing. Physical presence never establishes employee productivity. Facial
        recognition, emotion inference, and automated disciplinary decisions are permanently disabled.
      </p>
    </div>
  );
}
