"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  Database,
  FileLock2,
  History,
  Save,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatDateTime, formatRoleLabel } from "@/lib/utils";
import type { AuditLog, RetentionPolicy } from "@/types";
import { Badge, Button, Card, Input, Textarea } from "@/components/ui/primitives";

interface UserAccessRow {
  id: number;
  full_name: string;
  email: string;
  role: string;
  can_view_cctv: boolean;
  is_active: boolean;
  last_login_at: string | null;
}

interface MonitoringPolicyPublic {
  version: string;
  notice_text: string;
  video_retention_days: number;
  event_metadata_retention_days: number;
  raw_video_storage_enabled: boolean;
  prohibited_practices: string[];
}

export default function SettingsPage() {
  const { user, refreshProfile } = useAuth();
  const [policy, setPolicy] = useState<RetentionPolicy | null>(null);
  const [publicPolicy, setPublicPolicy] = useState<MonitoringPolicyPublic | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [accessUsers, setAccessUsers] = useState<UserAccessRow[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const isAdminOrHr = user?.role === "super_admin" || user?.role === "hr_admin";
  const isOwner = user?.role === "super_admin";

  const loadSettings = useCallback(async () => {
    try {
      const pub = await apiFetch<MonitoringPolicyPublic>("/api/auth/monitoring-policy");
      setPublicPolicy(pub);

      if (isAdminOrHr) {
        const [ret, logs] = await Promise.all([
          apiFetch<RetentionPolicy>("/api/settings/retention"),
          apiFetch<AuditLog[]>("/api/settings/audit-logs?limit=60"),
        ]);
        setPolicy(ret);
        setAuditLogs(logs);
      }
      if (isOwner) {
        const users = await apiFetch<UserAccessRow[]>("/api/settings/user-access");
        setAccessUsers(users);
      }
    } catch {
      // handled cleanly by role views
    }
  }, [isAdminOrHr, isOwner]);

  useEffect(() => {
    if (user) loadSettings();
  }, [user, loadSettings]);

  const handleSavePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!policy) return;
    setSaving(true);
    setNotice(null);
    try {
      const updated = await apiFetch<RetentionPolicy>("/api/settings/retention", {
        method: "PUT",
        body: JSON.stringify({
          video_retention_days: policy.video_retention_days,
          event_metadata_retention_days: policy.event_metadata_retention_days,
          enable_raw_video_storage: policy.enable_raw_video_storage,
          auto_purge_enabled: policy.auto_purge_enabled,
          monitoring_notice_text: policy.monitoring_notice_text,
        }),
      });
      setPolicy(updated);
      setNotice("Privacy & retention settings saved and recorded in Access Audit Trail.");
      await loadSettings();
    } finally {
      setSaving(false);
    }
  };

  const handleRunPurge = async () => {
    setNotice(null);
    const res = await apiFetch<{ deleted_events: number; deleted_files: number }>(
      "/api/settings/run-retention",
      { method: "POST" }
    );
    setNotice(
      `Retention purge completed: ${res.deleted_events} expired event(s) and ${res.deleted_files} expired footage file(s) deleted.`
    );
    await loadSettings();
  };

  const handleToggleCctvAccess = async (row: UserAccessRow) => {
    try {
      await apiFetch(`/api/settings/user-access/${row.id}`, {
        method: "PATCH",
        body: JSON.stringify({ can_view_cctv: !row.can_view_cctv }),
      });
      setNotice(`Updated CCTV access permission for ${row.full_name}.`);
      await loadSettings();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Permission update blocked.");
    }
  };

  const handleUpdateConsent = async (accepted: boolean) => {
    await apiFetch("/api/auth/consent", {
      method: "POST",
      body: JSON.stringify({ accepted }),
    });
    await refreshProfile();
    setNotice("Your workplace monitoring notice acknowledgment has been updated.");
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.16em] text-[#4D7361] font-semibold">
          Privacy, Security &amp; Ethical AI Governance
        </p>
        <h1 className="font-serif text-3xl text-[#19201C] mt-1">
          {user?.role === "employee" ? "Privacy & Monitoring Policy" : "Settings & Audit Trail"}
        </h1>
      </div>

      {notice && (
        <div className="rounded-xl border border-[#CFE0D6] bg-[#EAF1ED] px-4 py-3 text-xs text-[#234536]">
          {notice}
        </div>
      )}

      {/* Employee-Visible Transparent Monitoring Policy & Consent */}
      {publicPolicy && (
        <Card className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-[#244738]" />
              <h2 className="text-base font-semibold text-[#19201C]">
                Transparent Workplace Monitoring Policy (v{publicPolicy.version})
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <Badge tone="green">
                Raw Video Storage: {publicPolicy.raw_video_storage_enabled ? "Enabled" : "Disabled"}
              </Badge>
              <Badge tone="neutral">
                Metadata Retention: {publicPolicy.event_metadata_retention_days} days
              </Badge>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#FAF8F4] border border-[#E5E0D5] whitespace-pre-line text-xs text-[#343E38] leading-relaxed">
            {publicPolicy.notice_text}
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {publicPolicy.prohibited_practices.map((item) => (
              <div
                key={item}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#EAF1ED] border border-[#D4E2DA] text-xs text-[#22513C]"
              >
                <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                <span>{item}</span>
              </div>
            ))}
          </div>

          {user?.employee_id && (
            <div className="pt-3 border-t border-[#ECE8DE] flex flex-wrap items-center justify-between gap-3">
              <div className="text-xs text-[#5C655F]">
                Consent Acknowledgment Status:{" "}
                <strong className="text-[#19201C]">
                  {user.privacy_consent_accepted ? "Acknowledged" : "Pending"}
                </strong>
                {user.privacy_consent_at && (
                  <span className="ml-2 font-mono text-[11px]">
                    ({formatDateTime(user.privacy_consent_at)})
                  </span>
                )}
              </div>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => handleUpdateConsent(true)}
              >
                Re-confirm Acknowledgment
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* Admin / HR Retention Configuration */}
      {isAdminOrHr && policy && (
        <Card>
          <form onSubmit={handleSavePolicy} className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Database className="w-4 h-4 text-[#244738]" />
                <h2 className="text-sm font-semibold text-[#19201C]">
                  Data Retention &amp; Automatic Footage Deletion
                </h2>
              </div>
              <Button type="button" size="sm" variant="outline" onClick={handleRunPurge}>
                <Trash2 className="w-3.5 h-3.5" />
                Run Retention Purge Now
              </Button>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium mb-1">
                  Video Clip Retention Period (Days)
                </label>
                <Input
                  type="number"
                  min={1}
                  max={90}
                  value={policy.video_retention_days}
                  onChange={(e) =>
                    setPolicy({ ...policy, video_retention_days: Number(e.target.value) })
                  }
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1">
                  AI Event Metadata Retention (Days)
                </label>
                <Input
                  type="number"
                  min={7}
                  max={365}
                  value={policy.event_metadata_retention_days}
                  onChange={(e) =>
                    setPolicy({
                      ...policy,
                      event_metadata_retention_days: Number(e.target.value),
                    })
                  }
                />
              </div>
            </div>

            <div className="flex flex-wrap gap-6 pt-1 text-xs">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={policy.enable_raw_video_storage}
                  onChange={(e) =>
                    setPolicy({ ...policy, enable_raw_video_storage: e.target.checked })
                  }
                  className="accent-[#244738]"
                />
                <span>
                  Enable Raw Video Storage (Recommended: <strong>Off</strong> — prefer aggregate metadata)
                </span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={policy.auto_purge_enabled}
                  onChange={(e) =>
                    setPolicy({ ...policy, auto_purge_enabled: e.target.checked })
                  }
                  className="accent-[#244738]"
                />
                <span>Automatic Scheduled Deletion of Expired Footage &amp; Events</span>
              </label>
            </div>

            <div>
              <label className="block text-xs font-medium mb-1">
                Employee Monitoring Notice Text
              </label>
              <Textarea
                rows={5}
                value={policy.monitoring_notice_text}
                onChange={(e) =>
                  setPolicy({ ...policy, monitoring_notice_text: e.target.value })
                }
              />
            </div>

            <div className="flex items-center justify-between pt-2">
              <span className="text-[11px] text-[#6B746E]">
                Last automated purge: {formatDateTime(policy.last_purge_at)} (
                {policy.last_purge_deleted_count} items removed)
              </span>
              <Button type="submit" disabled={saving}>
                <Save className="w-3.5 h-3.5" />
                {saving ? "Saving..." : "Save Governance Policy"}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Super Admin: Role-Based CCTV Access Permissions */}
      {isOwner && accessUsers.length > 0 && (
        <Card className="p-0 overflow-hidden">
          <div className="px-5 py-4 border-b border-[#E5E0D5] flex items-center gap-2">
            <FileLock2 className="w-4 h-4 text-[#244738]" />
            <h2 className="text-sm font-semibold text-[#19201C]">
              Role-Based CCTV Access Governance (Owner Only)
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-[#FAF8F4] border-b border-[#E5E0D5] text-[#636C66] uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-3 px-5">Account</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Live CCTV Privilege</th>
                  <th className="py-3 px-5 text-right">Control</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFECE4]">
                {accessUsers.map((u) => {
                  const eligible = u.role === "super_admin" || u.role === "hr_admin";
                  return (
                    <tr key={u.id}>
                      <td className="py-3 px-5">
                        <div className="font-semibold text-[#19201C]">{u.full_name}</div>
                        <div className="text-[11px] text-[#6B746E]">{u.email}</div>
                      </td>
                      <td className="py-3 px-4">{formatRoleLabel(u.role)}</td>
                      <td className="py-3 px-4">
                        <Badge tone={u.can_view_cctv ? "green" : "neutral"}>
                          {u.can_view_cctv ? "Authorized" : "Blocked"}
                        </Badge>
                      </td>
                      <td className="py-3 px-5 text-right">
                        {eligible ? (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleToggleCctvAccess(u)}
                          >
                            {u.can_view_cctv ? "Revoke CCTV" : "Grant CCTV"}
                          </Button>
                        ) : (
                          <span className="text-[11px] text-[#838C86]">
                            Permanently prohibited for role
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Immutable Access Audit Trail */}
      {isAdminOrHr && (
        <Card className="p-0 overflow-hidden">
          <div className="px-5 py-4 border-b border-[#E5E0D5] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-[#244738]" />
              <h2 className="text-sm font-semibold text-[#19201C]">
                Immutable Access &amp; Security Audit Trail
              </h2>
            </div>
            <Badge tone="neutral">{auditLogs.length} recent events</Badge>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-[#FAF8F4] border-b border-[#E5E0D5] text-[#636C66] uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-2.5 px-5">Timestamp</th>
                  <th className="py-2.5 px-4">Actor</th>
                  <th className="py-2.5 px-4">Action</th>
                  <th className="py-2.5 px-5">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFECE4]">
                {auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-[#FAF8F4]">
                    <td className="py-2.5 px-5 font-mono text-[11px] text-[#68716B] whitespace-nowrap">
                      {formatDateTime(log.created_at)}
                    </td>
                    <td className="py-2.5 px-4">
                      <div className="font-medium text-[#19201C]">{log.user_email}</div>
                      <div className="text-[10px] text-[#7A837D]">{log.user_role}</div>
                    </td>
                    <td className="py-2.5 px-4 font-mono text-[11px] text-[#244738]">
                      {log.action}
                    </td>
                    <td className="py-2.5 px-5 text-[#4C554F]">{log.details}</td>
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
