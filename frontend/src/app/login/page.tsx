"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, Lock, ShieldCheck, ArrowRight, Building2, Users, UserCheck, Briefcase } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Button, Input } from "@/components/ui/primitives";

const DEMO_ACCOUNTS = [
  {
    label: "Super Admin / Owner",
    name: "Eleanor Vance",
    email: "owner@worksight.io",
    scope: "Full platform, CCTV & audit governance",
    icon: Building2,
  },
  {
    label: "HR Administrator",
    name: "Nadia Al-Mansoor",
    email: "hr@worksight.io",
    scope: "Directory, attendance, leaves, reports & alerts",
    icon: Users,
  },
  {
    label: "Department Manager",
    name: "Marcus Sterling",
    email: "manager@worksight.io",
    scope: "Engineering department scope only",
    icon: Briefcase,
  },
  {
    label: "Employee Portal",
    name: "Maya Lin",
    email: "employee@worksight.io",
    scope: "Self-service attendance, leaves & privacy",
    icon: UserCheck,
  },
];

export default function LoginPage() {
  const router = useRouter();
  const { user, login } = useAuth();
  const [email, setEmail] = useState("owner@worksight.io");
  const [password, setPassword] = useState("WorkSight2026!");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      router.replace("/");
    }
  }, [user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email, password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const quickLogin = async (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword("WorkSight2026!");
    setSubmitting(true);
    setError(null);
    try {
      await login(demoEmail, "WorkSight2026!");
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in. Ensure backend API is running.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-12 bg-[#F6F4EE]">
      {/* Left Architectural Editorial Column */}
      <div className="lg:col-span-6 xl:col-span-7 bg-[#1F3D30] text-[#F6F4EE] p-8 sm:p-14 flex flex-col justify-between relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-[0.06] pointer-events-none"
          style={{
            backgroundImage:
              "linear-gradient(to right, #ffffff 1px, transparent 1px), linear-gradient(to bottom, #ffffff 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />
        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-[#F6F4EE]/12 border border-[#F6F4EE]/20 flex items-center justify-center">
              <Eye className="w-5 h-5 text-[#CFE0D6]" />
            </div>
            <div>
              <span className="font-serif text-2xl tracking-tight text-[#FAF8F4]">WorkSight</span>
              <p className="text-[11px] uppercase tracking-[0.2em] text-[#A8C1B4]">
                Workplace Intelligence
              </p>
            </div>
          </div>

          <div className="mt-14 max-w-xl">
            <p className="text-xs uppercase tracking-[0.18em] text-[#A8C1B4] font-medium">
              Enterprise Attendance & Spatial Telemetry
            </p>
            <h1 className="mt-4 font-serif text-4xl sm:text-5xl leading-[1.12] tracking-tight text-[#FAF8F4]">
              Clarity across your workplace, built on employee trust.
            </h1>
            <p className="mt-5 text-sm sm:text-base text-[#CAD9D1] leading-relaxed">
              Unify verified badge &amp; QR attendance with anonymous on-premise CCTV occupancy
              sensing. Designed from the ground up with strict role-based access, encrypted camera
              credentials, and human-reviewed alerts.
            </p>
          </div>
        </div>

        <div className="relative z-10 mt-12 grid sm:grid-cols-3 gap-4 pt-8 border-t border-[#F6F4EE]/15">
          <div>
            <div className="flex items-center gap-2 text-[#CFE0D6] text-xs font-semibold uppercase tracking-wider">
              <ShieldCheck className="w-4 h-4" /> Zero Biometrics
            </div>
            <p className="mt-1.5 text-xs text-[#B8CCC1] leading-relaxed">
              No facial recognition, no emotion analysis, and no identity inference from camera feeds.
            </p>
          </div>
          <div>
            <div className="flex items-center gap-2 text-[#CFE0D6] text-xs font-semibold uppercase tracking-wider">
              <Lock className="w-4 h-4" /> Strict RBAC
            </div>
            <p className="mt-1.5 text-xs text-[#B8CCC1] leading-relaxed">
              Four isolated portals with audited CCTV viewing and Fernet-encrypted RTSP secrets.
            </p>
          </div>
          <div>
            <div className="flex items-center gap-2 text-[#CFE0D6] text-xs font-semibold uppercase tracking-wider">
              <Eye className="w-4 h-4" /> Presence ≠ Productivity
            </div>
            <p className="mt-1.5 text-xs text-[#B8CCC1] leading-relaxed">
              Physical occupancy informs safety and space planning—never automated employee scoring.
            </p>
          </div>
        </div>
      </div>

      {/* Right Sign-In & Role Portal Selector */}
      <div className="lg:col-span-6 xl:col-span-5 flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md space-y-7">
          <div>
            <h2 className="font-serif text-3xl text-[#19201C] tracking-tight">Sign in to WorkSight</h2>
            <p className="mt-1.5 text-sm text-[#5C655F]">
              Authenticate with your corporate credentials or explore any of the four role-isolated portals below.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="ws-card p-6 space-y-4">
            {error && (
              <div className="rounded-xl border border-[#EDC8C6] bg-[#FBECEB] px-3.5 py-2.5 text-xs text-[#9A3430]">
                {error}
              </div>
            )}
            <div>
              <label className="block text-xs font-medium text-[#434D47] mb-1.5">
                Corporate Email
              </label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="name@company.com"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#434D47] mb-1.5">Password</label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••••••"
              />
            </div>
            <Button type="submit" className="w-full py-2.5" disabled={submitting}>
              {submitting ? "Signing in..." : "Sign in to Portal"}
              <ArrowRight className="w-4 h-4" />
            </Button>
          </form>

          {/* Four Role Demo Portals */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#5C655F]">
                Instant Role Portal Access (Demo)
              </span>
              <span className="text-[11px] font-mono text-[#76807A]">PW: WorkSight2026!</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {DEMO_ACCOUNTS.map((acct) => {
                const Icon = acct.icon;
                return (
                  <button
                    key={acct.email}
                    type="button"
                    disabled={submitting}
                    onClick={() => quickLogin(acct.email)}
                    className="text-left p-3 rounded-xl bg-white border border-[#E3ded2] hover:border-[#244738] hover:bg-[#FAF8F4] transition cursor-pointer group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-[#19201C] group-hover:text-[#244738]">
                        {acct.label}
                      </span>
                      <Icon className="w-3.5 h-3.5 text-[#5D7B6B]" />
                    </div>
                    <p className="text-[11px] text-[#5C655F] mt-0.5">{acct.name}</p>
                    <p className="text-[10px] text-[#7A837D] mt-1 leading-snug">{acct.scope}</p>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
