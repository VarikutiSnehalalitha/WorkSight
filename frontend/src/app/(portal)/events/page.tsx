"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Activity,
  CheckCircle2,
  FlaskConical,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useRealtime } from "@/lib/ws-context";
import { formatDateTime, formatEventLabel } from "@/lib/utils";
import type { Camera, VisionEvent } from "@/types";
import {
  Badge,
  Button,
  Card,
  EthicalNoticeBanner,
  Select,
  StatusBadge,
} from "@/components/ui/primitives";

export default function AiEventsPage() {
  const { user } = useAuth();
  const { lastMessage } = useRealtime();
  const [events, setEvents] = useState<VisionEvent[]>([]);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [eventType, setEventType] = useState("");
  const [reviewFilter, setReviewFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);

  // Simulator controls for dev/demo
  const [simCamId, setSimCamId] = useState<string>("");
  const [simType, setSimType] = useState<string>("restricted_intrusion");
  const [simCount, setSimCount] = useState<number>(2);

  const canSimulate = user?.role === "super_admin" || user?.role === "hr_admin";

  const loadEvents = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (eventType) params.set("event_type", eventType);
      if (reviewFilter) params.set("review_status", reviewFilter);
      const list = await apiFetch<VisionEvent[]>(`/api/events?${params.toString()}`);
      setEvents(list);
    } finally {
      setLoading(false);
    }
  }, [eventType, reviewFilter]);

  useEffect(() => {
    if (user && user.role !== "employee") {
      loadEvents();
      if (user.can_view_cctv) {
        apiFetch<Camera[]>("/api/cameras")
          .then((cams) => {
            setCameras(cams);
            if (cams.length > 0 && !simCamId) setSimCamId(String(cams[0].id));
          })
          .catch(() => {});
      }
    }
  }, [user, loadEvents, lastMessage, simCamId]);

  if (user?.role === "employee") {
    return (
      <Card className="max-w-lg mx-auto my-12 text-center space-y-3">
        <ShieldAlert className="w-8 h-8 text-[#9A3430] mx-auto" />
        <h2 className="font-serif text-xl">Restricted Telemetry</h2>
        <p className="text-xs text-[#5C655F]">
          AI facility telemetry events are restricted to authorized operations and HR reviewers.
        </p>
      </Card>
    );
  }

  const handleReview = async (
    eventId: number,
    review_status: "confirmed" | "false_positive" | "resolved"
  ) => {
    try {
      await apiFetch(`/api/events/${eventId}/review`, {
        method: "POST",
        body: JSON.stringify({
          review_status,
          review_notes: `Marked ${review_status.replace("_", " ")} via human review queue.`,
        }),
      });
      setNotice(`Event #${eventId} updated to ${review_status.replace("_", " ")}.`);
      await loadEvents();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Failed to review event.");
    }
  };

  const handleSimulate = async () => {
    if (!simCamId) return;
    try {
      await apiFetch("/api/events/simulate", {
        method: "POST",
        body: JSON.stringify({
          camera_id: Number(simCamId),
          event_type: simType,
          person_count: simCount,
        }),
      });
      setNotice(
        `Dispatched clearly labeled SIMULATED '${formatEventLabel(simType)}' event & real-time WebSocket alert.`
      );
      await loadEvents();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Simulation failed.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[#4D7361] font-semibold">
            Anonymous Computer Vision Telemetry
          </p>
          <h1 className="font-serif text-3xl text-[#19201C] mt-1">AI Monitoring Events</h1>
          <p className="text-xs text-[#5C655F] mt-1">
            Short-lived anonymous person tracking for safety, entry/exit flow, crowding, and camera health. Every alert is reviewable and correctable.
          </p>
        </div>

        <div className="flex flex-wrap gap-2.5">
          <div className="w-48">
            <Select value={eventType} onChange={(e) => setEventType(e.target.value)}>
              <option value="">All Event Types</option>
              <option value="entry">Entry Crossing</option>
              <option value="exit">Exit Crossing</option>
              <option value="occupancy_change">Occupancy Change</option>
              <option value="restricted_intrusion">Restricted Intrusion</option>
              <option value="extended_vacancy">Extended Vacancy</option>
              <option value="crowd_detected">Crowd Detected</option>
              <option value="camera_obstructed">Camera Obstructed</option>
              <option value="camera_disconnected">Camera Disconnected</option>
            </Select>
          </div>
          <div className="w-40">
            <Select value={reviewFilter} onChange={(e) => setReviewFilter(e.target.value)}>
              <option value="">All Review States</option>
              <option value="unreviewed">Needs Review</option>
              <option value="confirmed">Confirmed</option>
              <option value="false_positive">False Positive</option>
              <option value="resolved">Resolved</option>
            </Select>
          </div>
        </div>
      </div>

      <EthicalNoticeBanner compact />

      {/* Developer / Demo Event Simulator Bar */}
      {canSimulate && cameras.length > 0 && (
        <Card className="bg-[#FAF8F4] border-dashed border-[#CBBFA8] p-4">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#7E4826]">
              <FlaskConical className="w-4 h-4" />
              <span>Dev AI Event Simulator (Tagged SIMULATED — Tests Real-Time Alerts)</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="w-52">
                <Select value={simCamId} onChange={(e) => setSimCamId(e.target.value)}>
                  {cameras.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="w-44">
                <Select value={simType} onChange={(e) => setSimType(e.target.value)}>
                  <option value="restricted_intrusion">Restricted Intrusion</option>
                  <option value="crowd_detected">Crowd Detected</option>
                  <option value="extended_vacancy">Extended Vacancy</option>
                  <option value="camera_obstructed">Camera Obstructed</option>
                  <option value="camera_disconnected">Camera Disconnected</option>
                  <option value="entry">Entry Passage</option>
                  <option value="exit">Exit Passage</option>
                </Select>
              </div>
              <Button size="sm" variant="secondary" onClick={handleSimulate}>
                Trigger Simulated Event
              </Button>
            </div>
          </div>
        </Card>
      )}

      {notice && (
        <div className="rounded-xl border border-[#CFE0D6] bg-[#EAF1ED] px-4 py-3 text-xs text-[#234536]">
          {notice}
        </div>
      )}

      {/* Event List */}
      <div className="space-y-3">
        {loading ? (
          <Card className="py-10 text-center text-xs text-[#6B746E]">
            Loading AI vision events...
          </Card>
        ) : events.length === 0 ? (
          <Card className="py-10 text-center text-xs text-[#6B746E]">
            No monitoring events match your filter.
          </Card>
        ) : (
          events.map((ev) => (
            <Card
              key={ev.id}
              className="flex flex-col lg:flex-row lg:items-center justify-between gap-4"
            >
              <div className="space-y-1.5 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Activity className="w-4 h-4 text-[#244738]" />
                  <span className="text-sm font-semibold text-[#19201C]">
                    {formatEventLabel(ev.event_type)}
                  </span>
                  <StatusBadge status={ev.severity} />
                  <StatusBadge status={ev.review_status} />
                  {ev.is_simulated && <Badge tone="amber">SIMULATED</Badge>}
                  <Badge tone="neutral">AI Presence Telemetry</Badge>
                </div>

                <p className="text-xs text-[#3C4640] leading-relaxed">{ev.description}</p>

                <div className="flex flex-wrap items-center gap-3 text-[11px] text-[#6B746E]">
                  <span>
                    Camera: <strong className="text-[#19201C]">{ev.camera_name}</strong>
                  </span>
                  {ev.zone_name && <span>Zone: {ev.zone_name}</span>}
                  <span className="font-mono">Persons: {ev.person_count}</span>
                  <span className="font-mono">
                    Confidence: {Math.round(ev.confidence * 100)}%
                  </span>
                  {ev.anonymous_track_ids.length > 0 && (
                    <span className="font-mono">
                      Ephemeral IDs: {ev.anonymous_track_ids.join(", ")}
                    </span>
                  )}
                  <span className="font-mono">{formatDateTime(ev.occurred_at)}</span>
                </div>

                {ev.reviewed_by_name && (
                  <p className="text-[11px] text-[#4D7361]">
                    Reviewed by {ev.reviewed_by_name}: {ev.review_notes}
                  </p>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2 shrink-0">
                {ev.review_status === "unreviewed" ? (
                  <>
                    <Button size="sm" onClick={() => handleReview(ev.id, "confirmed")}>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Confirm
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleReview(ev.id, "false_positive")}
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      False Positive
                    </Button>
                  </>
                ) : (
                  ev.review_status !== "resolved" && (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => handleReview(ev.id, "resolved")}
                    >
                      Mark Resolved
                    </Button>
                  )
                )}
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
