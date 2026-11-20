"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Download, FileSpreadsheet, FileText, ShieldAlert } from "lucide-react";
import { apiDownloadFile, apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Department } from "@/types";
import {
  Badge,
  Button,
  Card,
  EthicalNoticeBanner,
  Input,
  Select,
  StatusBadge,
} from "@/components/ui/primitives";

interface ReportSummaryResponse {
  start_date: string;
  end_date: string;
  total_records: number;
  ethics_notice: string;
  department_summaries: Array<{
    department_id: number;
    department_name: string;
    department_code: string;
    employee_count: number;
    present_records: number;
    late_records: number;
    early_departures: number;
    leave_records: number;
    absent_records: number;
    avg_working_hours: number;
    attendance_rate: number;
  }>;
  records_preview: Array<{
    id: number;
    attendance_date: string;
    employee_code: string;
    employee_name: string;
    department_name: string;
    status: string;
    working_hours: number;
    verification_method: string;
  }>;
}

export default function ReportsPage() {
  const { user } = useAuth();
  const today = new Date();
  const twoWeeksAgo = new Date(today.getTime() - 13 * 86400000);

  const [startDate, setStartDate] = useState(twoWeeksAgo.toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState(today.toISOString().slice(0, 10));
  const [deptId, setDeptId] = useState("");
  const [departments, setDepartments] = useState<Department[]>([]);
  const [report, setReport] = useState<ReportSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<"excel" | "pdf" | null>(null);

  const loadReport = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
      if (deptId) params.set("department_id", deptId);
      const data = await apiFetch<ReportSummaryResponse>(
        `/api/reports/summary?${params.toString()}`
      );
      setReport(data);
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, deptId]);

  useEffect(() => {
    if (user && user.role !== "employee") {
      apiFetch<Department[]>("/api/departments").then(setDepartments).catch(() => {});
      loadReport();
    }
  }, [user, loadReport]);

  if (user?.role === "employee") {
    return (
      <Card className="max-w-lg mx-auto my-12 text-center space-y-3">
        <ShieldAlert className="w-8 h-8 text-[#9A3430] mx-auto" />
        <h2 className="font-serif text-xl">Restricted Reports</h2>
        <p className="text-xs text-[#5C655F]">
          Department and company-wide reports are accessible to HR, Managers, and Owners.
        </p>
      </Card>
    );
  }

  const handleExport = async (format: "excel" | "pdf") => {
    setDownloading(format);
    try {
      const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
      if (deptId) params.set("department_id", deptId);
      const ext = format === "excel" ? "xlsx" : "pdf";
      await apiDownloadFile(
        `/api/reports/export/${format}?${params.toString()}`,
        `worksight-attendance-${startDate}-to-${endDate}.${ext}`
      );
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[#4D7361] font-semibold">
            Compliance &amp; Executive Exports
          </p>
          <h1 className="font-serif text-3xl text-[#19201C] mt-1">Reports</h1>
          <p className="text-xs text-[#5C655F] mt-1">
            Generate audited department attendance summaries and export formatted Excel (.xlsx) or PDF (.pdf) reports.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            variant="secondary"
            disabled={downloading !== null}
            onClick={() => handleExport("excel")}
          >
            <FileSpreadsheet className="w-4 h-4" />
            {downloading === "excel" ? "Generating..." : "Export Excel (.xlsx)"}
          </Button>
          <Button disabled={downloading !== null} onClick={() => handleExport("pdf")}>
            <FileText className="w-4 h-4" />
            {downloading === "pdf" ? "Generating..." : "Export PDF (.pdf)"}
          </Button>
        </div>
      </div>

      <EthicalNoticeBanner compact />

      {/* Filter Bar */}
      <Card className="p-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-[11px] font-medium text-[#5C655F] mb-1">Start Date</label>
          <Input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-40"
          />
        </div>
        <div>
          <label className="block text-[11px] font-medium text-[#5C655F] mb-1">End Date</label>
          <Input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-40"
          />
        </div>
        {user?.role !== "dept_manager" && (
          <div>
            <label className="block text-[11px] font-medium text-[#5C655F] mb-1">Department</label>
            <Select
              value={deptId}
              onChange={(e) => setDeptId(e.target.value)}
              className="w-48"
            >
              <option value="">All Departments</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </Select>
          </div>
        )}
        <Button variant="outline" onClick={loadReport} disabled={loading}>
          <Download className="w-3.5 h-3.5" />
          Apply Filters
        </Button>
      </Card>

      {/* Department Summary Table */}
      <Card className="p-0 overflow-hidden">
        <div className="px-5 py-4 border-b border-[#E5E0D5] flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[#19201C]">
            Department Verified Attendance Breakdown
          </h2>
          {report && <Badge tone="green">{report.total_records} verified records</Badge>}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-[#FAF8F4] border-b border-[#E5E0D5] text-[#636C66] uppercase text-[10px] tracking-wider">
              <tr>
                <th className="py-3 px-5">Department</th>
                <th className="py-3 px-4">Employees</th>
                <th className="py-3 px-4">Present</th>
                <th className="py-3 px-4">Late</th>
                <th className="py-3 px-4">Early Out</th>
                <th className="py-3 px-4">On Leave</th>
                <th className="py-3 px-4">Avg Hours</th>
                <th className="py-3 px-5">Attendance Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EFECE4]">
              {loading || !report ? (
                <tr>
                  <td colSpan={8} className="py-10 text-center text-[#6B746E]">
                    Compiling report summary...
                  </td>
                </tr>
              ) : (
                report.department_summaries.map((d) => (
                  <tr key={d.department_id} className="hover:bg-[#FAF8F4]">
                    <td className="py-3 px-5 font-semibold text-[#19201C]">
                      {d.department_name}{" "}
                      <span className="font-mono text-[10px] text-[#7A837D]">
                        ({d.department_code})
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono">{d.employee_count}</td>
                    <td className="py-3 px-4 font-mono text-[#22513C]">{d.present_records}</td>
                    <td className="py-3 px-4 font-mono text-[#9A5229]">{d.late_records}</td>
                    <td className="py-3 px-4 font-mono text-[#9A5229]">{d.early_departures}</td>
                    <td className="py-3 px-4 font-mono text-[#2B5478]">{d.leave_records}</td>
                    <td className="py-3 px-4 font-mono">{d.avg_working_hours.toFixed(2)}h</td>
                    <td className="py-3 px-5">
                      <Badge tone="green">{d.attendance_rate.toFixed(1)}%</Badge>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Records Preview */}
      {report && (
        <Card className="p-0 overflow-hidden">
          <div className="px-5 py-4 border-b border-[#E5E0D5]">
            <h2 className="text-sm font-semibold text-[#19201C]">
              Verified Records Preview (Top 25)
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-[#FAF8F4] border-b border-[#E5E0D5] text-[#636C66] uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-2.5 px-5">Date</th>
                  <th className="py-2.5 px-4">Employee</th>
                  <th className="py-2.5 px-4">Department</th>
                  <th className="py-2.5 px-4">Hours</th>
                  <th className="py-2.5 px-4">Method</th>
                  <th className="py-2.5 px-5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFECE4]">
                {report.records_preview.slice(0, 25).map((r) => (
                  <tr key={r.id}>
                    <td className="py-2.5 px-5 font-mono">{r.attendance_date}</td>
                    <td className="py-2.5 px-4 font-medium text-[#19201C]">{r.employee_name}</td>
                    <td className="py-2.5 px-4 text-[#5C655F]">{r.department_name}</td>
                    <td className="py-2.5 px-4 font-mono">{r.working_hours.toFixed(2)}h</td>
                    <td className="py-2.5 px-4 capitalize text-[#5C655F]">
                      {r.verification_method.replace(/_/g, " ")}
                    </td>
                    <td className="py-2.5 px-5">
                      <StatusBadge status={r.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
