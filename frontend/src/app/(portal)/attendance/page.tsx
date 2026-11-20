"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Check,
  Clock,
  FileEdit,
  LogIn,
  LogOut,
  Plus,
  X,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatTime } from "@/lib/utils";
import type { AttendanceCorrection, AttendanceRecord, Shift } from "@/types";
import {
  Badge,
  Button,
  Card,
  Input,
  Modal,
  Select,
  StatusBadge,
  Textarea,
} from "@/components/ui/primitives";

export default function AttendancePage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<"history" | "corrections" | "shifts">("history");
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [corrections, setCorrections] = useState<AttendanceCorrection[]>([]);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);

  const [corrModal, setCorrModal] = useState(false);
  const [corrForm, setCorrForm] = useState({
    attendance_date: new Date().toISOString().slice(0, 10),
    requested_check_in: "09:00",
    requested_check_out: "17:30",
    reason: "",
  });

  const [shiftModal, setShiftModal] = useState(false);
  const [shiftForm, setShiftForm] = useState({
    name: "",
    start_time: "09:00",
    end_time: "17:30",
    grace_period_minutes: 15,
    early_departure_threshold_minutes: 15,
    is_default: false,
  });

  const canReview =
    user?.role === "super_admin" ||
    user?.role === "hr_admin" ||
    user?.role === "dept_manager";
  const canCreateShift = user?.role === "super_admin" || user?.role === "hr_admin";

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status_filter", statusFilter);
      const [recs, corrs, sh] = await Promise.all([
        apiFetch<AttendanceRecord[]>(`/api/attendance?${params.toString()}`),
        apiFetch<AttendanceCorrection[]>("/api/attendance/corrections"),
        apiFetch<Shift[]>("/api/attendance/shifts"),
      ]);
      setRecords(recs);
      setCorrections(corrs);
      setShifts(sh);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleClock = async (type: "check-in" | "check-out") => {
    setMessage(null);
    try {
      await apiFetch(`/api/attendance/${type}`, {
        method: "POST",
        body: JSON.stringify({ verification_method: "qr_code" }),
      });
      setMessage(
        type === "check-in"
          ? "Verified QR check-in recorded."
          : "Verified check-out recorded."
      );
      await loadAll();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Action failed.");
    }
  };

  const handleSubmitCorrection = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    try {
      await apiFetch("/api/attendance/corrections", {
        method: "POST",
        body: JSON.stringify(corrForm),
      });
      setCorrModal(false);
      setCorrForm({
        attendance_date: new Date().toISOString().slice(0, 10),
        requested_check_in: "09:00",
        requested_check_out: "17:30",
        reason: "",
      });
      setMessage("Attendance correction request submitted for HR review.");
      await loadAll();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to submit correction.");
    }
  };

  const handleReviewCorrection = async (id: number, status: "approved" | "rejected") => {
    try {
      await apiFetch(`/api/attendance/corrections/${id}/review`, {
        method: "POST",
        body: JSON.stringify({
          status,
          review_notes:
            status === "approved"
              ? "Verified and approved by HR/Management."
              : "Insufficient verification details provided.",
        }),
      });
      setMessage(`Correction #${id} ${status}.`);
      await loadAll();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Review failed.");
    }
  };

  const handleCreateShift = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await apiFetch("/api/attendance/shifts", {
        method: "POST",
        body: JSON.stringify(shiftForm),
      });
      setShiftModal(false);
      setMessage("Shift schedule created.");
      await loadAll();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Shift creation failed.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[#4D7361] font-semibold">
            Verified Access-Control Attendance
          </p>
          <h1 className="font-serif text-3xl text-[#19201C] mt-1">
            Attendance &amp; Shift Management
          </h1>
          <p className="text-xs text-[#5C655F] mt-1">
            Individual attendance is verified strictly through access cards, QR check-ins, or HR-approved adjustments—never inferred from CCTV.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" onClick={() => handleClock("check-in")}>
            <LogIn className="w-3.5 h-3.5" />
            Check-In (QR)
          </Button>
          <Button size="sm" variant="outline" onClick={() => handleClock("check-out")}>
            <LogOut className="w-3.5 h-3.5" />
            Check-Out
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setCorrModal(true)}>
            <FileEdit className="w-3.5 h-3.5" />
            Request Correction
          </Button>
        </div>
      </div>

      {message && (
        <div className="rounded-xl border border-[#CFE0D6] bg-[#EAF1ED] px-4 py-3 text-xs text-[#234536]">
          {message}
        </div>
      )}

      {/* Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E3DED2] pb-2">
        <div className="flex gap-2">
          {(
            [
              ["history", "Verified Attendance Log"],
              [
                "corrections",
                `Correction Requests (${corrections.filter((c) => c.status === "pending").length})`,
              ],
              ["shifts", "Shifts & Grace Rules"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition cursor-pointer ${
                tab === id
                  ? "bg-[#244738] text-[#FAF8F4]"
                  : "text-[#5C655F] hover:bg-[#EDE9DF]"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === "history" && (
          <div className="w-48">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Filter by status"
            >
              <option value="">All Statuses</option>
              <option value="present">Present</option>
              <option value="late">Late Arrival</option>
              <option value="early_departure">Early Departure</option>
              <option value="on_leave">On Leave</option>
              <option value="absent">Absent</option>
            </Select>
          </div>
        )}

        {tab === "shifts" && canCreateShift && (
          <Button size="sm" onClick={() => setShiftModal(true)}>
            <Plus className="w-3.5 h-3.5" />
            New Shift
          </Button>
        )}
      </div>

      {/* Tab 1: Attendance Log */}
      {tab === "history" && (
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-[#FAF8F4] border-b border-[#E5E0D5] text-[#636C66] uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-3.5 px-5">Date</th>
                  <th className="py-3.5 px-4">Employee</th>
                  <th className="py-3.5 px-4">Check-In</th>
                  <th className="py-3.5 px-4">Check-Out</th>
                  <th className="py-3.5 px-4">Working Hours</th>
                  <th className="py-3.5 px-4">Verification</th>
                  <th className="py-3.5 px-5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFECE4]">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-[#6B746E]">
                      Loading verified attendance records...
                    </td>
                  </tr>
                ) : (
                  records.map((rec) => (
                    <tr key={rec.id} className="hover:bg-[#FAF8F4]">
                      <td className="py-3 px-5 font-mono text-[#19201C]">{rec.attendance_date}</td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-[#19201C]">{rec.employee_name}</div>
                        <div className="text-[11px] text-[#6B746E]">
                          {rec.department_name} • {rec.employee_code}
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono">
                        {formatTime(rec.check_in_time)}
                        {rec.late_minutes > 0 && (
                          <span className="ml-1.5 text-[10px] text-[#9A5229]">
                            (+{rec.late_minutes}m)
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono">
                        {formatTime(rec.check_out_time)}
                        {rec.early_departure_minutes > 0 && (
                          <span className="ml-1.5 text-[10px] text-[#9A5229]">
                            (-{rec.early_departure_minutes}m)
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono font-medium">
                        {rec.working_hours.toFixed(2)}h
                      </td>
                      <td className="py-3 px-4">
                        <Badge tone="green">
                          {rec.verification_method.replace(/_/g, " ")}
                        </Badge>
                        {rec.is_corrected && (
                          <Badge tone="blue" className="ml-1">
                            HR Corrected
                          </Badge>
                        )}
                      </td>
                      <td className="py-3 px-5">
                        <StatusBadge status={rec.status} />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Tab 2: Correction Requests */}
      {tab === "corrections" && (
        <div className="space-y-3">
          {corrections.length === 0 ? (
            <Card className="text-center py-10 text-xs text-[#6B746E]">
              No attendance correction requests found.
            </Card>
          ) : (
            corrections.map((c) => (
              <Card
                key={c.id}
                className="flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-[#19201C]">
                      {c.employee_name}
                    </span>
                    <span className="text-xs text-[#68716B]">
                      ({c.department_name}) • Date:{" "}
                      <span className="font-mono text-[#19201C]">{c.attendance_date}</span>
                    </span>
                    <StatusBadge status={c.status} />
                  </div>
                  <p className="text-xs text-[#4C554F]">
                    Requested timings:{" "}
                    <span className="font-mono font-medium">
                      {c.requested_check_in || "—"} – {c.requested_check_out || "—"}
                    </span>
                  </p>
                  <p className="text-xs text-[#5C655F]">{c.reason}</p>
                  {c.review_notes && (
                    <p className="text-[11px] text-[#244738]">
                      Reviewer ({c.reviewed_by_name}): {c.review_notes}
                    </p>
                  )}
                </div>

                {canReview && c.status === "pending" && (
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      size="sm"
                      onClick={() => handleReviewCorrection(c.id, "approved")}
                    >
                      <Check className="w-3.5 h-3.5" />
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleReviewCorrection(c.id, "rejected")}
                    >
                      <X className="w-3.5 h-3.5" />
                      Reject
                    </Button>
                  </div>
                )}
              </Card>
            ))
          )}
        </div>
      )}

      {/* Tab 3: Shifts */}
      {tab === "shifts" && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {shifts.map((s) => (
            <Card key={s.id} className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-[#19201C] flex items-center gap-2">
                  <Clock className="w-4 h-4 text-[#4D7361]" />
                  {s.name}
                </h3>
                {s.is_default && <Badge tone="green">Default</Badge>}
              </div>
              <p className="font-mono text-2xl font-semibold text-[#244738]">
                {s.start_time} – {s.end_time}
              </p>
              <div className="text-xs text-[#5C655F] space-y-1 pt-2 border-t border-[#ECE8DE]">
                <div>Late arrival grace period: {s.grace_period_minutes} minutes</div>
                <div>Early departure threshold: {s.early_departure_threshold_minutes} minutes</div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Correction Modal */}
      <Modal
        open={corrModal}
        onClose={() => setCorrModal(false)}
        title="Request Attendance Correction"
        subtitle="Submit a verified correction request for HR review."
      >
        <form onSubmit={handleSubmitCorrection} className="space-y-4">
          <div>
            <label className="block text-xs font-medium mb-1">Attendance Date</label>
            <Input
              type="date"
              value={corrForm.attendance_date}
              onChange={(e) => setCorrForm({ ...corrForm, attendance_date: e.target.value })}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Check-In (HH:MM)</label>
              <Input
                type="time"
                value={corrForm.requested_check_in}
                onChange={(e) => setCorrForm({ ...corrForm, requested_check_in: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Check-Out (HH:MM)</label>
              <Input
                type="time"
                value={corrForm.requested_check_out}
                onChange={(e) => setCorrForm({ ...corrForm, requested_check_out: e.target.value })}
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Explanation</label>
            <Textarea
              rows={3}
              value={corrForm.reason}
              onChange={(e) => setCorrForm({ ...corrForm, reason: e.target.value })}
              placeholder="Explain why the verified check-in/out record needs adjustment..."
              required
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setCorrModal(false)}>
              Cancel
            </Button>
            <Button type="submit">Submit Request</Button>
          </div>
        </form>
      </Modal>

      {/* Create Shift Modal */}
      <Modal
        open={shiftModal}
        onClose={() => setShiftModal(false)}
        title="Create Shift Schedule"
      >
        <form onSubmit={handleCreateShift} className="space-y-4">
          <div>
            <label className="block text-xs font-medium mb-1">Shift Name</label>
            <Input
              value={shiftForm.name}
              onChange={(e) => setShiftForm({ ...shiftForm, name: e.target.value })}
              placeholder="Evening Support Shift"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Start Time</label>
              <Input
                type="time"
                value={shiftForm.start_time}
                onChange={(e) => setShiftForm({ ...shiftForm, start_time: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">End Time</label>
              <Input
                type="time"
                value={shiftForm.end_time}
                onChange={(e) => setShiftForm({ ...shiftForm, end_time: e.target.value })}
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Late Grace (min)</label>
              <Input
                type="number"
                min={0}
                value={shiftForm.grace_period_minutes}
                onChange={(e) =>
                  setShiftForm({ ...shiftForm, grace_period_minutes: Number(e.target.value) })
                }
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Early Out Threshold (min)</label>
              <Input
                type="number"
                min={0}
                value={shiftForm.early_departure_threshold_minutes}
                onChange={(e) =>
                  setShiftForm({
                    ...shiftForm,
                    early_departure_threshold_minutes: Number(e.target.value),
                  })
                }
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setShiftModal(false)}>
              Cancel
            </Button>
            <Button type="submit">Create Shift</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
