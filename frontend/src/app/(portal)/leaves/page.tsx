"use client";

import React, { useCallback, useEffect, useState } from "react";
import { CalendarDays, Check, Plus, X } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { LeaveRequest } from "@/types";
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

export default function LeavesPage() {
  const { user } = useAuth();
  const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const todayStr = new Date().toISOString().slice(0, 10);
  const [form, setForm] = useState({
    leave_type: "annual",
    start_date: todayStr,
    end_date: todayStr,
    reason: "",
  });

  const canReview =
    user?.role === "super_admin" ||
    user?.role === "hr_admin" ||
    user?.role === "dept_manager";

  const loadLeaves = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status_filter", statusFilter);
      const res = await apiFetch<LeaveRequest[]>(`/api/leaves?${params.toString()}`);
      setLeaves(res);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadLeaves();
  }, [loadLeaves]);

  const handleApply = async (e: React.FormEvent) => {
    e.preventDefault();
    setNotice(null);
    try {
      await apiFetch("/api/leaves", {
        method: "POST",
        body: JSON.stringify(form),
      });
      setModalOpen(false);
      setForm({ leave_type: "annual", start_date: todayStr, end_date: todayStr, reason: "" });
      setNotice("Leave application submitted for approval.");
      await loadLeaves();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Failed to submit leave application.");
    }
  };

  const handleReview = async (id: number, status: "approved" | "rejected") => {
    try {
      await apiFetch(`/api/leaves/${id}/review`, {
        method: "POST",
        body: JSON.stringify({
          status,
          review_notes:
            status === "approved" ? "Approved by HR/Management." : "Unable to approve at this time.",
        }),
      });
      setNotice(`Leave request #${id} ${status}.`);
      await loadLeaves();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Review failed.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[#4D7361] font-semibold">
            Time Off &amp; Absence Governance
          </p>
          <h1 className="font-serif text-3xl text-[#19201C] mt-1">Leave Management</h1>
          <p className="text-xs text-[#5C655F] mt-1">
            {user?.role === "employee"
              ? "Submit personal leave applications and track approval status."
              : "Review employee leave requests and synchronize approved leave with verified attendance."}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="w-40">
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </Select>
          </div>
          <Button onClick={() => setModalOpen(true)}>
            <Plus className="w-4 h-4" />
            Apply Leave
          </Button>
        </div>
      </div>

      {notice && (
        <div className="rounded-xl border border-[#CFE0D6] bg-[#EAF1ED] px-4 py-3 text-xs text-[#234536]">
          {notice}
        </div>
      )}

      <div className="space-y-3">
        {loading ? (
          <Card className="py-10 text-center text-xs text-[#6B746E]">
            Loading leave requests...
          </Card>
        ) : leaves.length === 0 ? (
          <Card className="py-10 text-center text-xs text-[#6B746E]">
            No leave requests found.
          </Card>
        ) : (
          leaves.map((lr) => (
            <Card
              key={lr.id}
              className="flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1.5">
                <div className="flex flex-wrap items-center gap-2">
                  <CalendarDays className="w-4 h-4 text-[#4D7361]" />
                  <span className="text-sm font-semibold text-[#19201C]">
                    {lr.employee_name}
                  </span>
                  <span className="text-xs text-[#68716B]">({lr.department_name})</span>
                  <Badge tone="blue" className="capitalize">
                    {lr.leave_type} • {lr.days_count}d
                  </Badge>
                  <StatusBadge status={lr.status} />
                </div>
                <p className="text-xs font-mono text-[#244738]">
                  {lr.start_date} → {lr.end_date}
                </p>
                <p className="text-xs text-[#5C655F]">{lr.reason}</p>
                {lr.review_notes && (
                  <p className="text-[11px] text-[#4D7361]">
                    Reviewed by {lr.reviewed_by_name}: {lr.review_notes}
                  </p>
                )}
              </div>

              {canReview && lr.status === "pending" && (
                <div className="flex items-center gap-2 shrink-0">
                  <Button size="sm" onClick={() => handleReview(lr.id, "approved")}>
                    <Check className="w-3.5 h-3.5" />
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleReview(lr.id, "rejected")}
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

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Apply for Leave"
        subtitle="Approved leaves automatically reflect on your verified attendance calendar."
      >
        <form onSubmit={handleApply} className="space-y-4">
          <div>
            <label className="block text-xs font-medium mb-1">Leave Type</label>
            <Select
              value={form.leave_type}
              onChange={(e) => setForm({ ...form, leave_type: e.target.value })}
            >
              <option value="annual">Annual Leave</option>
              <option value="sick">Sick Leave</option>
              <option value="personal">Personal Leave</option>
              <option value="parental">Parental Leave</option>
              <option value="unpaid">Unpaid Leave</option>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Start Date</label>
              <Input
                type="date"
                value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">End Date</label>
              <Input
                type="date"
                value={form.end_date}
                onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                required
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Reason</label>
            <Textarea
              rows={3}
              value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })}
              placeholder="Briefly describe your leave request..."
              required
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">Submit Application</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
