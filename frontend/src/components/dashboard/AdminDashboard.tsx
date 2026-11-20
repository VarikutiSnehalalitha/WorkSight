"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  Building2,
  Camera,
  Clock,
  RefreshCw,
  UserCheck,
  UserMinus,
  UserX,
  Users,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiFetch } from "@/lib/api";
import { useRealtime } from "@/lib/ws-context";
import { useAuth } from "@/lib/auth-context";
import { formatDateTime, formatEventLabel } from "@/lib/utils";
import type { DashboardOverview, Department } from "@/types";
import {
  Badge,
  Button,
  Card,
  EthicalNoticeBanner,
  Input,
  Select,
  StatusBadge,
} from "@/components/ui/primitives";

export function AdminDashboard() {
  const { user } = useAuth();
  const { lastMessage } = useRealtime();
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().slice(0, 10)
  );
  const [selectedDept, setSelectedDept] = useState<string>("");
  const [trendDays, setTrendDays] = useState<number>(10);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        target_date: selectedDate,
        trend_days: String(trendDays),
      });
      if (selectedDept) params.set("department_id", selectedDept);
      const res = await apiFetch<DashboardOverview>(
        `/api/dashboard/overview?${params.toString()}`
      );
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard.");
    } finally {
      setLoading(false);
    }
  }, [selectedDate, selectedDept, trendDays]);

  useEffect(() => {
    apiFetch<Department[]>("/api/departments")
      .then(setDepartments)
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadOverview();
  }, [loadOverview, lastMessage]);

  const kpis = data
    ? [
        {
          label: "Total Employees",
          value: data.total_employees,
          sub: "Active roster",
          icon: Users,
          accent: "text-[#244738] bg-[#EAF1ED]",
        },
        {
          label: "Currently Present",
          value: data.currently_present,
          sub: "Verified check-ins",
          icon: UserCheck,
          accent: "text-[#22513C] bg-[#E8F2EC]",
        },
        {
          label: "Absent Today",
          value: data.absent_today,
          sub: "Unrecorded / absent",
          icon: UserX,
          accent: "text-[#9A3430] bg-[#FBECEB]",
        },
        {
          label: "On Leave",
          value: data.on_leave_today,
          sub: `${data.pending_leaves} pending approval`,
          icon: UserMinus,
          accent: "text-[#2B5478] bg-[#EBF2F8]",
        },
        {
          label: "Late Arrivals",
          value: data.late_arrivals,
          sub: "Past shift grace",
          icon: Clock,
          accent: "text-[#9A5229] bg-[#FBF1E6]",
        },
        {
          label: "Early Departures",
          value: data.early_departures,
          sub: "Before shift close",
          icon: AlertTriangle,
          accent: "text-[#9A5229] bg-[#FBF1E6]",
        },
        {
          label: "Office Occupancy",
          value: `${data.office_occupancy_percent}%`,
          sub: `${data.office_occupancy_count} / ${data.office_capacity} AI-observed`,
          icon: Building2,
          accent: "text-[#244738] bg-[#EAF1ED]",
        },
        {
          label: "Camera Health",
          value: `${data.cameras_online}/${data.cameras_total}`,
          sub: `${data.unreviewed_alerts} alerts to review`,
          icon: Camera,
          accent: "text-[#244738] bg-[#EAF1ED]",
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      {/* Header & Interactive Filters */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[#4D7361] font-semibold">
            {user?.role === "dept_manager"
              ? `${user.managed_department_name || "Department"} Operations`
              : "Executive Workplace Overview"}
          </p>
          <h1 className="font-serif text-3xl text-[#19201C] mt-1 tracking-tight">
            Workplace Attendance &amp; Spatial Intelligence
          </h1>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="w-40">
            <Input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              aria-label="Select Date"
            />
          </div>
          {user?.role !== "dept_manager" && (
            <div className="w-48">
              <Select
                value={selectedDept}
                onChange={(e) => setSelectedDept(e.target.value)}
                aria-label="Filter Department"
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
          <div className="w-32">
            <Select
              value={String(trendDays)}
              onChange={(e) => setTrendDays(Number(e.target.value))}
              aria-label="Trend Range"
            >
              <option value="7">7 Days</option>
              <option value="10">10 Days</option>
              <option value="14">14 Days</option>
            </Select>
          </div>
          <Button variant="outline" onClick={loadOverview} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      <EthicalNoticeBanner compact />

      {error && (
        <div className="rounded-xl border border-[#EDC8C6] bg-[#FBECEB] px-4 py-3 text-sm text-[#9A3430]">
          {error}
        </div>
      )}

      {/* 8 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <Card key={kpi.label} className="p-5 flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-[#5C655F]">{kpi.label}</p>
                <p className="mt-2 text-2xl font-semibold text-[#19201C] tabular-nums font-mono">
                  {kpi.value}
                </p>
                <p className="mt-1 text-[11px] text-[#727B75]">{kpi.sub}</p>
              </div>
              <div className={`p-2.5 rounded-xl ${kpi.accent}`}>
                <Icon className="w-4 h-4" />
              </div>
            </Card>
          );
        })}
      </div>

      {/* Charts Row */}
      {data && (
        <div className="grid lg:grid-cols-12 gap-5">
          {/* Attendance Trends Area Chart */}
          <Card className="lg:col-span-7">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-[#19201C]">
                  Attendance &amp; Spatial Occupancy Trends
                </h2>
                <p className="text-xs text-[#5C655F]">
                  Verified daily check-ins compared with anonymous AI peak occupancy
                </p>
              </div>
              <Badge tone="green">Verified vs AI Telemetry</Badge>
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.attendance_trends}>
                  <defs>
                    <linearGradient id="wsPresent" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#244738" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#244738" stopOpacity={0.02} />
                    </linearGradient>
                    <linearGradient id="wsOcc" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6D9481" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#6D9481" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E9E4D9" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(v: string) => v.slice(5)}
                    tick={{ fontSize: 11, fill: "#69736D" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "#69736D" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#FCFBF8",
                      borderColor: "#E3DED2",
                      borderRadius: "12px",
                      fontSize: "12px",
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "12px" }} />
                  <Area
                    type="monotone"
                    dataKey="present"
                    name="Verified Present"
                    stroke="#244738"
                    strokeWidth={2}
                    fill="url(#wsPresent)"
                  />
                  <Area
                    type="monotone"
                    dataKey="ai_peak_occupancy"
                    name="AI Peak Occupancy"
                    stroke="#6D9481"
                    strokeWidth={2}
                    strokeDasharray="4 3"
                    fill="url(#wsOcc)"
                  />
                  <Area
                    type="monotone"
                    dataKey="late"
                    name="Late Arrivals"
                    stroke="#B5673B"
                    strokeWidth={1.8}
                    fill="none"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Department-Wise Attendance Bar Chart */}
          <Card className="lg:col-span-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-[#19201C]">
                  Department-Wise Attendance
                </h2>
                <p className="text-xs text-[#5C655F]">
                  Present, leave &amp; absent distribution for {data.target_date}
                </p>
              </div>
              <Link
                href="/departments"
                className="text-xs font-medium text-[#244738] hover:underline"
              >
                View all
              </Link>
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.department_attendance} layout="vertical" barSize={14}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E9E4D9" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: "#69736D" }} axisLine={false} />
                  <YAxis
                    type="category"
                    dataKey="code"
                    width={42}
                    tick={{ fontSize: 11, fill: "#19201C", fontWeight: 600 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#FCFBF8",
                      borderColor: "#E3DED2",
                      borderRadius: "12px",
                      fontSize: "12px",
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "12px" }} />
                  <Bar dataKey="present_today" name="Present" stackId="a" fill="#244738" radius={[0, 0, 0, 0]} />
                  <Bar dataKey="on_leave_today" name="On Leave" stackId="a" fill="#7D9FB5" />
                  <Bar dataKey="absent_today" name="Absent" stackId="a" fill="#C97B63" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      )}

      {/* Bottom Row: Recent AI Monitoring Events + Camera Fleet Health */}
      {data && (
        <div className="grid lg:grid-cols-12 gap-5">
          <Card className="lg:col-span-7">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-[#19201C]">
                  Recent AI Monitoring Events
                </h2>
                <p className="text-xs text-[#5C655F]">
                  Anonymous presence telemetry &amp; safety alerts (human review required)
                </p>
              </div>
              <Link
                href="/events"
                className="text-xs font-medium text-[#244738] hover:underline"
              >
                Review Queue →
              </Link>
            </div>

            <div className="divide-y divide-[#ECE8DE]">
              {data.recent_events.length === 0 ? (
                <p className="py-8 text-center text-xs text-[#6B746E]">
                  No recent vision events recorded.
                </p>
              ) : (
                data.recent_events.slice(0, 6).map((ev) => (
                  <div
                    key={ev.id}
                    className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <Activity className="w-3.5 h-3.5 text-[#4D7361]" />
                        <span className="text-xs font-semibold text-[#19201C]">
                          {formatEventLabel(ev.event_type)}
                        </span>
                        <span className="text-[11px] text-[#6B746E]">• {ev.camera_name}</span>
                        {ev.is_simulated && <Badge tone="amber">SIMULATED</Badge>}
                      </div>
                      <p className="text-xs text-[#5C655F] mt-1 line-clamp-1">
                        {ev.description}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <StatusBadge status={ev.review_status} />
                      <span className="text-[11px] font-mono text-[#76807A]">
                        {formatDateTime(ev.occurred_at)}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Card className="lg:col-span-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-[#19201C]">Camera Fleet Status</h2>
                <p className="text-xs text-[#5C655F]">
                  Live connectivity, occupancy &amp; simulator disclosure
                </p>
              </div>
              {user?.can_view_cctv && (
                <Link
                  href="/cctv"
                  className="text-xs font-medium text-[#244738] hover:underline"
                >
                  Open CCTV Console →
                </Link>
              )}
            </div>

            <div className="space-y-2.5">
              {data.cameras.map((cam) => (
                <div
                  key={cam.id}
                  className="p-3 rounded-xl bg-[#FAF8F4] border border-[#E7E2D7] flex items-center justify-between gap-3"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-[#19201C] truncate">
                        {cam.name}
                      </span>
                      {cam.is_simulated && <Badge tone="amber">SIMULATED</Badge>}
                    </div>
                    <p className="text-[11px] text-[#68716B] truncate mt-0.5">{cam.location}</p>
                  </div>
                  <div className="flex items-center gap-2.5 shrink-0">
                    <span className="text-xs font-mono text-[#244738] bg-[#EAF1ED] px-2 py-0.5 rounded-md">
                      {cam.current_occupancy}/{cam.max_occupancy_threshold}
                    </span>
                    <StatusBadge status={cam.status} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
