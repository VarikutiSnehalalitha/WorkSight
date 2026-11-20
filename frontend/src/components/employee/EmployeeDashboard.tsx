"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  Clock,
  CreditCard,
  FileCheck2,
  LogIn,
  LogOut,
  QrCode,
  ShieldCheck,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { formatTime } from "@/lib/utils";
import type { EmployeeSelfSummary } from "@/types";
import { Badge, Button, Card, StatusBadge } from "@/components/ui/primitives";

export function EmployeeDashboard() {
  const [summary, setSummary] = useState<EmployeeSelfSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [method, setMethod] = useState<"qr_code" | "access_card" | "web_portal">("qr_code");
  const [feedback, setFeedback] = useState<string | null>(null);

  const loadSelf = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<EmployeeSelfSummary>("/api/dashboard/employee-self");
      setSummary(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSelf();
  }, [loadSelf]);

  const handleClock = async (action: "check-in" | "check-out") => {
    setBusy(true);
    setFeedback(null);
    try {
      await apiFetch(`/api/attendance/${action}`, {
        method: "POST",
        body: JSON.stringify({ verification_method: method }),
      });
      setFeedback(
        action === "check-in"
          ? `Verified check-in recorded via ${method.replace("_", " ")}.`
          : "Verified check-out recorded and working hours updated."
      );
      await loadSelf();
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setBusy(false);
    }
  };

  if (loading || !summary) {
    return <p className="text-sm text-[#5C655F] py-12 text-center">Loading your portal...</p>;
  }

  const todayRec = summary.today_record;
  const checkedIn = Boolean(todayRec?.check_in_time);
  const checkedOut = Boolean(todayRec?.check_out_time);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[#4D7361] font-semibold">
            Employee Self-Service Portal
          </p>
          <h1 className="font-serif text-3xl text-[#19201C] mt-1">
            Welcome back, {summary.employee.full_name}
          </h1>
          <p className="text-xs text-[#5C655F] mt-1">
            {summary.employee.job_title} • {summary.employee.department_name} • Shift:{" "}
            <span className="font-mono">{summary.employee.shift_hours}</span> • Badge{" "}
            <span className="font-mono">{summary.employee.badge_id}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/leaves">
            <Button variant="secondary" size="sm">
              Apply for Leave
            </Button>
          </Link>
          <Link href="/attendance">
            <Button variant="outline" size="sm">
              Request Correction
            </Button>
          </Link>
        </div>
      </div>

      {feedback && (
        <div className="rounded-xl border border-[#CFE0D6] bg-[#EAF1ED] px-4 py-3 text-xs text-[#234536]">
          {feedback}
        </div>
      )}

      {/* Verified Check-In / Check-Out Card + 30-Day Metrics */}
      <div className="grid lg:grid-cols-12 gap-5">
        <Card className="lg:col-span-5 flex flex-col justify-between bg-[#FCFBF8]">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#4D7361]">
                Verified Attendance Today
              </span>
              <StatusBadge status={todayRec?.status || "unrecorded"} />
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="p-3 rounded-xl bg-white border border-[#E6E1D6]">
                <span className="text-[11px] text-[#68716B]">Check-In</span>
                <p className="font-mono text-lg font-semibold text-[#19201C] mt-0.5">
                  {formatTime(todayRec?.check_in_time)}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-white border border-[#E6E1D6]">
                <span className="text-[11px] text-[#68716B]">Check-Out</span>
                <p className="font-mono text-lg font-semibold text-[#19201C] mt-0.5">
                  {formatTime(todayRec?.check_out_time)}
                </p>
              </div>
            </div>

            <div className="mt-4">
              <span className="text-[11px] text-[#5C655F] font-medium block mb-1.5">
                Verification Method (Never Inferred from CCTV)
              </span>
              <div className="grid grid-cols-3 gap-2">
                {(
                  [
                    ["qr_code", "QR Check-In", QrCode],
                    ["access_card", "Access Card", CreditCard],
                    ["web_portal", "Web Portal", CheckCircle2],
                  ] as const
                ).map(([key, label, Icon]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setMethod(key)}
                    className={`p-2 rounded-xl border text-[11px] font-medium flex flex-col items-center gap-1 cursor-pointer transition ${
                      method === key
                        ? "bg-[#244738] text-[#FAF8F4] border-[#244738]"
                        : "bg-white text-[#4A544E] border-[#E3DED2] hover:bg-[#F3EFE6]"
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-5 flex gap-2.5">
            <Button
              className="flex-1"
              disabled={busy || checkedIn}
              onClick={() => handleClock("check-in")}
            >
              <LogIn className="w-4 h-4" />
              {checkedIn ? "Checked In" : "Verified Check-In"}
            </Button>
            <Button
              variant="outline"
              className="flex-1"
              disabled={busy || !checkedIn || checkedOut}
              onClick={() => handleClock("check-out")}
            >
              <LogOut className="w-4 h-4" />
              {checkedOut ? "Checked Out" : "Check-Out"}
            </Button>
          </div>
        </Card>

        <div className="lg:col-span-7 grid sm:grid-cols-2 gap-4">
          <Card>
            <p className="text-xs text-[#5C655F]">30-Day Working Hours</p>
            <p className="font-mono text-3xl font-semibold text-[#19201C] mt-2">
              {summary.metrics_30d.total_working_hours}h
            </p>
            <p className="text-xs text-[#6B746E] mt-1">
              Avg {summary.metrics_30d.avg_daily_hours}h / day across{" "}
              {summary.metrics_30d.days_present} days
            </p>
          </Card>
          <Card>
            <p className="text-xs text-[#5C655F]">Pending Requests</p>
            <p className="font-mono text-3xl font-semibold text-[#19201C] mt-2">
              {summary.metrics_30d.pending_leaves + summary.metrics_30d.pending_corrections}
            </p>
            <p className="text-xs text-[#6B746E] mt-1">
              {summary.metrics_30d.pending_leaves} leave(s) •{" "}
              {summary.metrics_30d.pending_corrections} correction(s)
            </p>
          </Card>
          <Card className="sm:col-span-2 bg-[#EFF5F1] border-[#CFE0D6]">
            <div className="flex items-start gap-3">
              <ShieldCheck className="w-5 h-5 text-[#244738] shrink-0 mt-0.5" />
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-[#1B382C]">
                    Your Workplace Privacy &amp; Monitoring Notice (v{summary.monitoring_policy.version})
                  </h3>
                  <Badge tone="green">
                    {summary.employee.privacy_consent_accepted ? "Acknowledged" : "Review Needed"}
                  </Badge>
                </div>
                <p className="text-xs text-[#2E5443] mt-1.5 leading-relaxed">
                  WorkSight uses anonymous person-counting for facility occupancy and safety only.
                  Facial recognition, emotion analysis, and automated productivity scoring are never
                  used. Raw video storage is{" "}
                  <strong>
                    {summary.monitoring_policy.raw_video_storage_enabled ? "enabled" : "disabled"}
                  </strong>
                  .
                </p>
                <Link
                  href="/settings"
                  className="inline-flex items-center gap-1 text-xs font-semibold text-[#244738] underline mt-2"
                >
                  <FileCheck2 className="w-3.5 h-3.5" />
                  Read Full Policy &amp; Privacy Rights
                </Link>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Recent Personal Attendance Table */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-[#19201C] flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#4D7361]" />
            Recent Personal Attendance History
          </h2>
          <Link href="/attendance" className="text-xs font-medium text-[#244738] hover:underline">
            Full History &amp; Corrections →
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-[#E5E0D5] text-[#636C66] uppercase text-[10px] tracking-wider">
                <th className="py-2.5 pr-4">Date</th>
                <th className="py-2.5 px-4">Check-In</th>
                <th className="py-2.5 px-4">Check-Out</th>
                <th className="py-2.5 px-4">Hours</th>
                <th className="py-2.5 px-4">Method</th>
                <th className="py-2.5 pl-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EFECE4]">
              {summary.recent_attendance.map((rec) => (
                <tr key={rec.id} className="hover:bg-[#FAF8F4]">
                  <td className="py-3 pr-4 font-mono text-[#19201C]">{rec.attendance_date}</td>
                  <td className="py-3 px-4 font-mono">{formatTime(rec.check_in_time)}</td>
                  <td className="py-3 px-4 font-mono">{formatTime(rec.check_out_time)}</td>
                  <td className="py-3 px-4 font-mono">{rec.working_hours.toFixed(2)}h</td>
                  <td className="py-3 px-4 capitalize text-[#5C655F]">
                    {rec.verification_method.replace(/_/g, " ")}
                  </td>
                  <td className="py-3 pl-4">
                    <StatusBadge status={rec.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
