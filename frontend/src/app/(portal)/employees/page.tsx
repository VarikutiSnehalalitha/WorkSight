"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Plus, Search, UserPlus, Edit3, ShieldAlert } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatTime } from "@/lib/utils";
import type { Department, Employee, Shift } from "@/types";
import {
  Badge,
  Button,
  Card,
  Input,
  Modal,
  Select,
  StatusBadge,
} from "@/components/ui/primitives";

export default function EmployeesPage() {
  const { user } = useAuth();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Employee | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    employee_code: "",
    full_name: "",
    email: "",
    phone: "",
    job_title: "",
    department_id: "",
    shift_id: "",
    workspace_desk_label: "",
  });

  const canManage = user?.role === "super_admin" || user?.role === "hr_admin";

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search.trim()) params.set("search", search.trim());
      if (deptFilter) params.set("department_id", deptFilter);
      const [emps, depts, sh] = await Promise.all([
        apiFetch<Employee[]>(`/api/employees?${params.toString()}`),
        apiFetch<Department[]>("/api/departments"),
        apiFetch<Shift[]>("/api/attendance/shifts"),
      ]);
      setEmployees(emps);
      setDepartments(depts);
      setShifts(sh);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load employees.");
    } finally {
      setLoading(false);
    }
  }, [search, deptFilter]);

  useEffect(() => {
    if (user && user.role !== "employee") {
      loadData();
    }
  }, [user, loadData]);

  if (user?.role === "employee") {
    return (
      <Card className="max-w-lg mx-auto my-12 text-center space-y-3">
        <ShieldAlert className="w-8 h-8 text-[#9A3430] mx-auto" />
        <h2 className="font-serif text-xl">Restricted Directory</h2>
        <p className="text-xs text-[#5C655F]">
          Employee accounts cannot browse the company employee directory. Access your personal records from Overview or Attendance.
        </p>
      </Card>
    );
  }

  const openCreate = () => {
    setEditing(null);
    setForm({
      employee_code: `WS-${1030 + employees.length}`,
      full_name: "",
      email: "",
      phone: "",
      job_title: "",
      department_id: departments[0] ? String(departments[0].id) : "",
      shift_id: shifts[0] ? String(shifts[0].id) : "",
      workspace_desk_label: "",
    });
    setModalOpen(true);
  };

  const openEdit = (emp: Employee) => {
    setEditing(emp);
    setForm({
      employee_code: emp.employee_code,
      full_name: emp.full_name,
      email: emp.email,
      phone: emp.phone || "",
      job_title: emp.job_title,
      department_id: String(emp.department_id),
      shift_id: emp.shift_id ? String(emp.shift_id) : "",
      workspace_desk_label: emp.workspace_desk_label || "",
    });
    setModalOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (editing) {
        await apiFetch(`/api/employees/${editing.id}`, {
          method: "PUT",
          body: JSON.stringify({
            full_name: form.full_name,
            phone: form.phone || null,
            job_title: form.job_title,
            department_id: Number(form.department_id),
            shift_id: form.shift_id ? Number(form.shift_id) : null,
            workspace_desk_label: form.workspace_desk_label || null,
          }),
        });
      } else {
        await apiFetch("/api/employees", {
          method: "POST",
          body: JSON.stringify({
            employee_code: form.employee_code,
            full_name: form.full_name,
            email: form.email,
            phone: form.phone || null,
            job_title: form.job_title || "Associate",
            department_id: Number(form.department_id),
            shift_id: form.shift_id ? Number(form.shift_id) : null,
            workspace_desk_label: form.workspace_desk_label || null,
          }),
        });
      }
      setModalOpen(false);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save employee.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[#4D7361] font-semibold">
            People Directory
          </p>
          <h1 className="font-serif text-3xl text-[#19201C] mt-1">Employees</h1>
          <p className="text-xs text-[#5C655F] mt-1">
            Verified employee roster, access-card credentials, shift assignments, and privacy acknowledgment status.
          </p>
        </div>
        {canManage && (
          <Button onClick={openCreate}>
            <UserPlus className="w-4 h-4" />
            Add Employee
          </Button>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-[#EDC8C6] bg-[#FBECEB] px-4 py-3 text-xs text-[#9A3430]">
          {error}
        </div>
      )}

      {/* Search & Filters */}
      <Card className="p-4 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-[#7A837D] absolute left-3.5 top-2.5" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, email, code, or role..."
            className="pl-10"
          />
        </div>
        {user?.role !== "dept_manager" && (
          <div className="sm:w-56">
            <Select value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)}>
              <option value="">All Departments</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </Select>
          </div>
        )}
      </Card>

      {/* Directory Table */}
      <Card className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-[#FAF8F4] border-b border-[#E5E0D5] text-[#636C66] uppercase text-[10px] tracking-wider">
              <tr>
                <th className="py-3.5 px-5">Employee</th>
                <th className="py-3.5 px-4">Department</th>
                <th className="py-3.5 px-4">Shift &amp; Desk</th>
                <th className="py-3.5 px-4">Access Badge</th>
                <th className="py-3.5 px-4">Today</th>
                <th className="py-3.5 px-4">Privacy Notice</th>
                {canManage && <th className="py-3.5 px-5 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EFECE4]">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-[#6B746E]">
                    Loading employees...
                  </td>
                </tr>
              ) : employees.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-[#6B746E]">
                    No employees matched your filter.
                  </td>
                </tr>
              ) : (
                employees.map((emp) => (
                  <tr key={emp.id} className="hover:bg-[#FAF8F4]/80">
                    <td className="py-3.5 px-5">
                      <div className="font-semibold text-[#19201C]">{emp.full_name}</div>
                      <div className="text-[11px] text-[#68716B]">
                        {emp.job_title} • <span className="font-mono">{emp.employee_code}</span>
                      </div>
                      <div className="text-[11px] text-[#838C86]">{emp.email}</div>
                    </td>
                    <td className="py-3.5 px-4 font-medium text-[#2F3933]">
                      {emp.department_name}
                    </td>
                    <td className="py-3.5 px-4">
                      <div>{emp.shift_name || "Default"}</div>
                      <div className="text-[11px] text-[#7A837D]">
                        {emp.workspace_desk_label || "Unassigned desk"}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px] text-[#244738]">
                      {emp.badge_id}
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={emp.today_status} />
                      {emp.today_check_in && (
                        <div className="text-[10px] font-mono text-[#76807A] mt-1">
                          In {formatTime(emp.today_check_in)}
                        </div>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <Badge tone={emp.privacy_consent_accepted ? "green" : "amber"}>
                        {emp.privacy_consent_accepted ? "Acknowledged" : "Pending"}
                      </Badge>
                    </td>
                    {canManage && (
                      <td className="py-3.5 px-5 text-right">
                        <Button variant="ghost" size="sm" onClick={() => openEdit(emp)}>
                          <Edit3 className="w-3.5 h-3.5" />
                          Edit
                        </Button>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Add / Edit Employee Modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editing ? `Edit ${editing.full_name}` : "Add New Employee"}
        subtitle="Creates a verified employee record with an access-card badge ID."
      >
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Employee Code</label>
              <Input
                value={form.employee_code}
                disabled={Boolean(editing)}
                onChange={(e) => setForm({ ...form, employee_code: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Full Name</label>
              <Input
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Corporate Email</label>
              <Input
                type="email"
                value={form.email}
                disabled={Boolean(editing)}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Job Title</label>
              <Input
                value={form.job_title}
                onChange={(e) => setForm({ ...form, job_title: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Department</label>
              <Select
                value={form.department_id}
                onChange={(e) => setForm({ ...form, department_id: e.target.value })}
                required
              >
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Assigned Shift</label>
              <Select
                value={form.shift_id}
                onChange={(e) => setForm({ ...form, shift_id: e.target.value })}
              >
                {shifts.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.start_time}–{s.end_time})
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Phone</label>
              <Input
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="+1 (415) 555-0199"
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Workspace Desk</label>
              <Input
                value={form.workspace_desk_label}
                onChange={(e) => setForm({ ...form, workspace_desk_label: e.target.value })}
                placeholder="Desk 3N-12"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">
              <Plus className="w-4 h-4" />
              {editing ? "Save Changes" : "Create Employee"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
