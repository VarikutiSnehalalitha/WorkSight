"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Bell, CheckCheck, CheckCircle2, XCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useRealtime } from "@/lib/ws-context";
import { formatDateTime } from "@/lib/utils";
import type { NotificationItem } from "@/types";
import { Badge, Button, Card, Select, StatusBadge } from "@/components/ui/primitives";

export default function NotificationsPage() {
  const { lastMessage } = useRealtime();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(true);

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (category) params.set("category", category);
      const data = await apiFetch<NotificationItem[]>(
        `/api/notifications?${params.toString()}`
      );
      setItems(data);
    } finally {
      setLoading(false);
    }
  }, [category]);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications, lastMessage]);

  const handleMarkAllRead = async () => {
    await apiFetch("/api/notifications/mark-all-read", { method: "POST" });
    await loadNotifications();
  };

  const handleUpdate = async (
    id: number,
    review_status: "acknowledged" | "resolved" | "dismissed"
  ) => {
    await apiFetch(`/api/notifications/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_read: true, review_status }),
    });
    await loadNotifications();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[#4D7361] font-semibold">
            Real-Time Alert Center
          </p>
          <h1 className="font-serif text-3xl text-[#19201C] mt-1">Notifications</h1>
          <p className="text-xs text-[#5C655F] mt-1">
            All camera, occupancy, restricted-area, vacancy, and attendance alerts are reviewable and correctable by authorized personnel.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <div className="w-44">
            <Select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">All Categories</option>
              <option value="camera">Camera Health</option>
              <option value="restricted_area">Restricted Area</option>
              <option value="occupancy">Occupancy</option>
              <option value="vacancy">Extended Vacancy</option>
              <option value="attendance">Attendance</option>
              <option value="leave">Leave</option>
            </Select>
          </div>
          <Button variant="outline" size="sm" onClick={handleMarkAllRead}>
            <CheckCheck className="w-3.5 h-3.5" />
            Mark All Read
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        {loading ? (
          <Card className="py-10 text-center text-xs text-[#6B746E]">
            Loading notifications...
          </Card>
        ) : items.length === 0 ? (
          <Card className="py-10 text-center text-xs text-[#6B746E]">
            You have no notifications in this category.
          </Card>
        ) : (
          items.map((n) => (
            <Card
              key={n.id}
              className={`flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                !n.is_read ? "border-l-4 border-l-[#244738]" : ""
              }`}
            >
              <div className="space-y-1.5 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Bell className="w-4 h-4 text-[#4D7361]" />
                  <span className="text-sm font-semibold text-[#19201C]">{n.title}</span>
                  <StatusBadge status={n.severity} />
                  <StatusBadge status={n.review_status} />
                  <Badge tone="neutral" className="capitalize">
                    {n.category.replace("_", " ")}
                  </Badge>
                </div>
                <p className="text-xs text-[#4C554F] leading-relaxed">{n.message}</p>
                <p className="text-[11px] font-mono text-[#7A837D]">
                  {formatDateTime(n.created_at)}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2 shrink-0">
                {n.review_status === "pending" && (
                  <>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleUpdate(n.id, "acknowledged")}
                    >
                      Acknowledge
                    </Button>
                    <Button size="sm" onClick={() => handleUpdate(n.id, "resolved")}>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Resolve
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleUpdate(n.id, "dismissed")}
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      Dismiss
                    </Button>
                  </>
                )}
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
