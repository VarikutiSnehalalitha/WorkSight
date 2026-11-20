"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Building2, Plus, ShieldAlert, Users } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Department } from "@/types";
import { Badge, Button, Card, Input, Modal, Textarea } from "@/components/ui/primitives";

export default function DepartmentsPage() {
  const { user } = useAuth();
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    code: "",
    floor_location: "Floor 2",
    description: "",
    target_capacity: 15,
  });

  const canManage = user?.role === "super_admin" || user?.role === "hr_admin";

  const loadDepts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch<Department[]>("/api/departments");
      setDepartments(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load departments.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user && user.role !== "employee") {
      loadDepts();
    }
  }, [user, loadDepts]);

  if (user?.role === "employee") {
    return (
      <Card className="max-w-lg mx-auto my-12 text-center space-y-3">
        <ShieldAlert className="w-8 h-8 text-[#9A3430] mx-auto" />
        <h2 className="font-serif text-xl">Restricted Section</h2>
        <p className="text-xs text-[#5C655F]">
          Department-wide analytics are available to Department Managers, HR, and Company Owners.
        </p>
      </Card>
    );
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await apiFetch("/api/departments", {
        method: "POST",
        body: JSON.stringify(form),
      });
      setModalOpen(false);
      setForm({ name: "", code: "", floor_location: "Floor 2", description: "", target_capacity: 15 });
      await loadDepts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create department.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[#4D7361] font-semibold">
            Organization Structure
          </p>
          <h1 className="font-serif text-3xl text-[#19201C] mt-1">Departments</h1>
          <p className="text-xs text-[#5C655F] mt-1">
            Department-wise verified attendance paired with anonymous workspace occupancy telemetry.
          </p>
        </div>
        {canManage && (
          <Button onClick={() => setModalOpen(true)}>
            <Plus className="w-4 h-4" />
            Add Department
          </Button>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-[#EDC8C6] bg-[#FBECEB] px-4 py-3 text-xs text-[#9A3430]">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-[#6B746E] py-8">Loading departments...</p>
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
          {departments.map((dept) => {
            const occPct = Math.min(
              100,
              Math.round((dept.ai_observed_occupancy / Math.max(1, dept.target_capacity)) * 100)
            );
            return (
              <Card key={dept.id} className="flex flex-col justify-between space-y-4">
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-semibold text-[#19201C]">{dept.name}</h3>
                        <Badge tone="neutral">{dept.code}</Badge>
                      </div>
                      <p className="text-xs text-[#68716B] mt-0.5 flex items-center gap-1">
                        <Building2 className="w-3.5 h-3.5" />
                        {dept.floor_location}
                      </p>
                    </div>
                    <Badge tone="green">{dept.attendance_rate}% Present</Badge>
                  </div>
                  {dept.description && (
                    <p className="text-xs text-[#5C655F] mt-3 leading-relaxed">
                      {dept.description}
                    </p>
                  )}
                </div>

                <div className="space-y-3 pt-3 border-t border-[#ECE8DE]">
                  <div className="grid grid-cols-4 gap-2 text-center">
                    <div className="p-2 rounded-lg bg-[#FAF8F4] border border-[#EAE5DA]">
                      <div className="font-mono text-sm font-semibold text-[#19201C]">
                        {dept.employee_count}
                      </div>
                      <div className="text-[10px] text-[#68716B]">Total</div>
                    </div>
                    <div className="p-2 rounded-lg bg-[#EAF1ED] border border-[#CFE0D6]">
                      <div className="font-mono text-sm font-semibold text-[#22513C]">
                        {dept.present_today}
                      </div>
                      <div className="text-[10px] text-[#22513C]">Present</div>
                    </div>
                    <div className="p-2 rounded-lg bg-[#EBF2F8] border border-[#C8DCEB]">
                      <div className="font-mono text-sm font-semibold text-[#2B5478]">
                        {dept.on_leave_today}
                      </div>
                      <div className="text-[10px] text-[#2B5478]">Leave</div>
                    </div>
                    <div className="p-2 rounded-lg bg-[#FBF1E6] border border-[#EED3BA]">
                      <div className="font-mono text-sm font-semibold text-[#9A5229]">
                        {dept.late_today}
                      </div>
                      <div className="text-[10px] text-[#9A5229]">Late</div>
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between text-[11px] mb-1">
                      <span className="text-[#5C655F] flex items-center gap-1">
                        <Users className="w-3 h-3" />
                        AI-Observed Workspace Occupancy
                      </span>
                      <span className="font-mono font-medium text-[#244738]">
                        {dept.ai_observed_occupancy} / {dept.target_capacity} ({occPct}%)
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-[#EAE5DA] overflow-hidden">
                      <div
                        className="h-full rounded-full bg-[#244738] transition-all"
                        style={{ width: `${occPct}%` }}
                      />
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Add Department"
        subtitle="Create a new organizational department and spatial capacity target."
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Department Name</label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Research & Development"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Short Code</label>
              <Input
                value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                placeholder="RND"
                maxLength={12}
                required
              />
            </div>
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Floor / Location</label>
              <Input
                value={form.floor_location}
                onChange={(e) => setForm({ ...form, floor_location: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Target Seat Capacity</label>
              <Input
                type="number"
                min={1}
                value={form.target_capacity}
                onChange={(e) => setForm({ ...form, target_capacity: Number(e.target.value) })}
                required
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Description</label>
            <Textarea
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">Create Department</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
