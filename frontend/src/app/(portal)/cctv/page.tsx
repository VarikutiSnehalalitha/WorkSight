"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Camera as CameraIcon,
  CheckCircle2,
  Layers,
  Lock,
  Plus,
  Radar,
  RefreshCw,
  ShieldAlert,
  Trash2,
  Wifi,
} from "lucide-react";
import { apiFetch, buildMediaUrl } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { formatDateTime } from "@/lib/utils";
import type { Camera, Department, OnvifDevice } from "@/types";
import {
  Badge,
  Button,
  Card,
  EthicalNoticeBanner,
  Input,
  Modal,
  Select,
  StatusBadge,
} from "@/components/ui/primitives";

export default function CctvPage() {
  const { user } = useAuth();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [streamUrls, setStreamUrls] = useState<Record<number, string>>({});
  const [liveActive, setLiveActive] = useState<Record<number, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [banner, setBanner] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Add Camera Modal
  const [addModal, setAddModal] = useState(false);
  const [testResult, setTestResult] = useState<{
    reachable: boolean;
    message: string;
    latency_ms: number;
  } | null>(null);
  const [camForm, setCamForm] = useState({
    name: "",
    location: "",
    department_id: "",
    camera_type: "rtsp" as "rtsp" | "onvif" | "simulated",
    is_simulated: false,
    rtsp_url: "",
    username: "",
    password: "",
    max_occupancy_threshold: 12,
    ai_enabled: true,
    recording_enabled: false,
  });

  // ONVIF Discovery Modal
  const [onvifModal, setOnvifModal] = useState(false);
  const [onvifDevices, setOnvifDevices] = useState<OnvifDevice[]>([]);
  const [scanning, setScanning] = useState(false);

  // Zone Configuration Modal
  const [zoneCamera, setZoneCamera] = useState<Camera | null>(null);
  const [zoneForm, setZoneForm] = useState({
    name: "",
    zone_type: "workspace" as "workspace" | "entry_exit" | "restricted" | "common_area",
    max_occupancy: 10,
    vacancy_alert_minutes: 45,
  });

  const authorized =
    user &&
    (user.role === "super_admin" || user.role === "hr_admin") &&
    user.can_view_cctv;

  const loadCameras = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cams, depts] = await Promise.all([
        apiFetch<Camera[]>("/api/cameras"),
        apiFetch<Department[]>("/api/departments"),
      ]);
      setCameras(cams);
      setDepartments(depts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load CCTV cameras.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authorized) {
      loadCameras();
    }
  }, [authorized, loadCameras]);

  if (!authorized) {
    return (
      <Card className="max-w-lg mx-auto my-12 text-center space-y-3">
        <ShieldAlert className="w-9 h-9 text-[#9A3430] mx-auto" />
        <h2 className="font-serif text-2xl text-[#19201C]">CCTV Access Restricted</h2>
        <p className="text-xs text-[#5C655F] leading-relaxed">
          Live video feeds and camera credentials are restricted strictly to explicitly authorized
          Super Admin and HR Administrator accounts. Every viewing session is immutably audit-logged.
        </p>
      </Card>
    );
  }

  const startStream = async (cam: Camera) => {
    try {
      const res = await apiFetch<{ stream_url: string; snapshot_url: string }>(
        `/api/cameras/${cam.id}/stream-token`,
        { method: "POST" }
      );
      setStreamUrls((prev) => ({ ...prev, [cam.id]: buildMediaUrl(res.stream_url) }));
      setLiveActive((prev) => ({ ...prev, [cam.id]: true }));
      setBanner(
        `Authorized stream session opened for ${cam.name} (logged to Access Audit Trail).`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to open stream.");
    }
  };

  const stopStream = (camId: number) => {
    setLiveActive((prev) => ({ ...prev, [camId]: false }));
  };

  const handleTestSavedCamera = async (camId: number) => {
    setBanner(null);
    try {
      const res = await apiFetch<{ reachable: boolean; message: string; latency_ms: number }>(
        `/api/cameras/${camId}/test`,
        { method: "POST" }
      );
      setBanner(
        `${res.reachable ? "Connected" : "Unreachable"} (${res.latency_ms}ms): ${res.message}`
      );
      await loadCameras();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection test failed.");
    }
  };

  const handleTestNewCamera = async () => {
    setTestResult(null);
    try {
      const res = await apiFetch<{ reachable: boolean; message: string; latency_ms: number }>(
        "/api/cameras/test-connection",
        {
          method: "POST",
          body: JSON.stringify({
            rtsp_url: camForm.rtsp_url || null,
            username: camForm.username || null,
            password: camForm.password || null,
            is_simulated: camForm.camera_type === "simulated",
          }),
        }
      );
      setTestResult(res);
    } catch (err) {
      setTestResult({
        reachable: false,
        message: err instanceof Error ? err.message : "Test failed.",
        latency_ms: 0,
      });
    }
  };

  const handleCreateCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await apiFetch("/api/cameras", {
        method: "POST",
        body: JSON.stringify({
          ...camForm,
          is_simulated: camForm.camera_type === "simulated",
          department_id: camForm.department_id ? Number(camForm.department_id) : null,
        }),
      });
      setAddModal(false);
      setTestResult(null);
      setCamForm({
        name: "",
        location: "",
        department_id: "",
        camera_type: "rtsp",
        is_simulated: false,
        rtsp_url: "",
        username: "",
        password: "",
        max_occupancy_threshold: 12,
        ai_enabled: true,
        recording_enabled: false,
      });
      setBanner("Camera registered with Fernet-encrypted credentials.");
      await loadCameras();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to register camera.");
    }
  };

  const handleDeleteCamera = async (camId: number, name: string) => {
    if (!window.confirm(`Remove camera "${name}" and its monitoring zones?`)) return;
    try {
      await apiFetch(`/api/cameras/${camId}`, { method: "DELETE" });
      setBanner(`Removed camera "${name}".`);
      await loadCameras();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete camera.");
    }
  };

  const handleOnvifDiscover = async () => {
    setOnvifModal(true);
    setScanning(true);
    try {
      const devices = await apiFetch<OnvifDevice[]>("/api/cameras/discover/onvif");
      setOnvifDevices(devices);
    } catch (err) {
      setError(err instanceof Error ? err.message : "ONVIF discovery failed.");
    } finally {
      setScanning(false);
    }
  };

  const adoptOnvifDevice = (dev: OnvifDevice) => {
    setOnvifModal(false);
    setCamForm({
      name: dev.name,
      location: "Discovered via ONVIF LAN Scan",
      department_id: departments[0] ? String(departments[0].id) : "",
      camera_type: dev.is_simulated_discovery ? "simulated" : "onvif",
      is_simulated: dev.is_simulated_discovery,
      rtsp_url: dev.is_simulated_discovery ? "" : `rtsp://${dev.ip_address}:${dev.port}/stream1`,
      username: "",
      password: "",
      max_occupancy_threshold: 10,
      ai_enabled: true,
      recording_enabled: false,
    });
    setAddModal(true);
  };

  const handleAddZone = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!zoneCamera) return;
    const presetCoords: Record<string, number[][]> = {
      workspace: [[0.1, 0.15], [0.9, 0.15], [0.9, 0.85], [0.1, 0.85]],
      entry_exit: [[0.1, 0.28], [0.9, 0.28], [0.9, 0.68], [0.1, 0.68]],
      restricted: [[0.18, 0.2], [0.82, 0.2], [0.82, 0.8], [0.18, 0.8]],
      common_area: [[0.12, 0.55], [0.88, 0.55], [0.88, 0.92], [0.12, 0.92]],
    };
    try {
      await apiFetch(`/api/cameras/${zoneCamera.id}/zones`, {
        method: "POST",
        body: JSON.stringify({
          ...zoneForm,
          coordinates: presetCoords[zoneForm.zone_type],
        }),
      });
      setZoneForm({
        name: "",
        zone_type: "workspace",
        max_occupancy: 10,
        vacancy_alert_minutes: 45,
      });
      await loadCameras();
      const updated = await apiFetch<Camera[]>("/api/cameras");
      setZoneCamera(updated.find((c) => c.id === zoneCamera.id) || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add zone.");
    }
  };

  const handleDeleteZone = async (camId: number, zoneId: number) => {
    try {
      await apiFetch(`/api/cameras/${camId}/zones/${zoneId}`, { method: "DELETE" });
      const updated = await apiFetch<Camera[]>("/api/cameras");
      setCameras(updated);
      setZoneCamera(updated.find((c) => c.id === camId) || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove zone.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-[#4D7361] font-semibold">
            Authorized CCTV &amp; On-Premise AI Vision
          </p>
          <h1 className="font-serif text-3xl text-[#19201C] mt-1">CCTV Monitoring</h1>
          <p className="text-xs text-[#5C655F] mt-1">
            Manage RTSP &amp; ONVIF cameras with encrypted credentials, configurable monitoring zones, and audited live viewing.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Button variant="outline" onClick={handleOnvifDiscover}>
            <Radar className="w-4 h-4" />
            ONVIF Discover
          </Button>
          <Button onClick={() => setAddModal(true)}>
            <Plus className="w-4 h-4" />
            Add Camera
          </Button>
        </div>
      </div>

      <EthicalNoticeBanner compact />

      {banner && (
        <div className="rounded-xl border border-[#CFE0D6] bg-[#EAF1ED] px-4 py-3 text-xs text-[#234536]">
          {banner}
        </div>
      )}
      {error && (
        <div className="rounded-xl border border-[#EDC8C6] bg-[#FBECEB] px-4 py-3 text-xs text-[#9A3430]">
          {error}
        </div>
      )}

      {/* Camera Grid */}
      {loading ? (
        <p className="text-sm text-[#6B746E] py-8">Loading camera fleet...</p>
      ) : (
        <div className="grid lg:grid-cols-2 gap-5">
          {cameras.map((cam) => {
            const isStreaming = liveActive[cam.id] && streamUrls[cam.id];
            return (
              <Card key={cam.id} className="p-0 overflow-hidden flex flex-col">
                {/* Video Viewport */}
                <div className="relative aspect-video bg-[#191F1C] flex items-center justify-center overflow-hidden">
                  {isStreaming ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={streamUrls[cam.id]}
                      alt={`${cam.name} stream`}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="text-center px-6 space-y-3">
                      <CameraIcon className="w-9 h-9 text-[#6F867A] mx-auto" />
                      <div>
                        <p className="text-xs font-medium text-[#E8EFEA]">
                          {cam.is_simulated
                            ? "Simulated Development Feed Ready"
                            : "Live RTSP Stream Standby"}
                        </p>
                        <p className="text-[11px] text-[#98ACA1] mt-0.5">
                          Viewing generates an immutable Access Audit Trail entry.
                        </p>
                      </div>
                      <Button size="sm" onClick={() => startStream(cam)}>
                        {cam.is_simulated ? "Open Simulated Feed" : "Open Live RTSP View"}
                      </Button>
                    </div>
                  )}

                  {/* Explicit Simulation vs Live Badge Overlay */}
                  <div className="absolute top-3 left-3 flex items-center gap-2">
                    {cam.is_simulated ? (
                      <span className="px-2.5 py-1 rounded-md bg-[#B5673B] text-white text-[10px] font-semibold tracking-wider uppercase shadow">
                        SIMULATED DEV FEED — NOT LIVE CCTV
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 rounded-md bg-[#244738] text-white text-[10px] font-semibold tracking-wider uppercase shadow">
                        HARDWARE RTSP
                      </span>
                    )}
                  </div>

                  {isStreaming && (
                    <button
                      onClick={() => stopStream(cam.id)}
                      className="absolute top-3 right-3 px-2.5 py-1 rounded-md bg-black/65 hover:bg-black/85 text-white text-[11px] cursor-pointer"
                    >
                      Stop View
                    </button>
                  )}
                </div>

                {/* Camera Metadata & Controls */}
                <div className="p-5 space-y-4 flex-1 flex flex-col justify-between">
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h3 className="text-sm font-semibold text-[#19201C]">{cam.name}</h3>
                        <p className="text-xs text-[#5C655F] mt-0.5">{cam.location}</p>
                      </div>
                      <StatusBadge status={cam.status} />
                    </div>

                    <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                      <div className="p-2 rounded-lg bg-[#FAF8F4] border border-[#EAE5DA]">
                        <span className="text-[10px] text-[#68716B] block">AI Occupancy</span>
                        <span className="font-mono font-semibold text-[#244738]">
                          {cam.current_occupancy} / {cam.max_occupancy_threshold}
                        </span>
                      </div>
                      <div className="p-2 rounded-lg bg-[#FAF8F4] border border-[#EAE5DA]">
                        <span className="text-[10px] text-[#68716B] block">Stream Spec</span>
                        <span className="font-mono text-[#19201C]">
                          {cam.resolution} · {cam.fps}fps
                        </span>
                      </div>
                      <div className="p-2 rounded-lg bg-[#FAF8F4] border border-[#EAE5DA]">
                        <span className="text-[10px] text-[#68716B] block">Zones</span>
                        <span className="font-mono text-[#19201C]">{cam.zones.length} active</span>
                      </div>
                    </div>

                    <div className="mt-3 flex items-center gap-1.5 text-[11px] font-mono text-[#6B746E] bg-[#F7F4ED] px-2.5 py-1.5 rounded-lg border border-[#E7E2D7] truncate">
                      <Lock className="w-3 h-3 shrink-0 text-[#4D7361]" />
                      <span className="truncate">{cam.masked_endpoint}</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-[#ECE8DE]">
                    <span className="text-[11px] text-[#7A837D]">
                      Heartbeat: {formatDateTime(cam.last_heartbeat_at)}
                    </span>
                    <div className="flex items-center gap-1.5">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleTestSavedCamera(cam.id)}
                      >
                        <Wifi className="w-3.5 h-3.5" />
                        Test
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => setZoneCamera(cam)}
                      >
                        <Layers className="w-3.5 h-3.5" />
                        Zones ({cam.zones.length})
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteCamera(cam.id, cam.name)}
                        title="Remove camera"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-[#A43E3A]" />
                      </Button>
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Add Camera Modal */}
      <Modal
        open={addModal}
        onClose={() => setAddModal(false)}
        title="Register CCTV Camera"
        subtitle="RTSP URLs and credentials are encrypted at rest via Fernet and never returned to browsers."
      >
        <form onSubmit={handleCreateCamera} className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Camera Name</label>
              <Input
                value={camForm.name}
                onChange={(e) => setCamForm({ ...camForm, name: e.target.value })}
                placeholder="CAM-07 West Entrance"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Source Protocol</label>
              <Select
                value={camForm.camera_type}
                onChange={(e) =>
                  setCamForm({
                    ...camForm,
                    camera_type: e.target.value as "rtsp" | "onvif" | "simulated",
                  })
                }
              >
                <option value="rtsp">Physical RTSP Stream</option>
                <option value="onvif">ONVIF Profile S Camera</option>
                <option value="simulated">Simulated Dev Feed (Watermarked)</option>
              </Select>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium mb-1">Physical Location</label>
              <Input
                value={camForm.location}
                onChange={(e) => setCamForm({ ...camForm, location: e.target.value })}
                placeholder="Floor 1 — West Corridor"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1">Department</label>
              <Select
                value={camForm.department_id}
                onChange={(e) => setCamForm({ ...camForm, department_id: e.target.value })}
              >
                <option value="">Shared Facility Area</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          {camForm.camera_type !== "simulated" && (
            <>
              <div>
                <label className="block text-xs font-medium mb-1">
                  RTSP Stream URI (Encrypted on Save)
                </label>
                <Input
                  value={camForm.rtsp_url}
                  onChange={(e) => setCamForm({ ...camForm, rtsp_url: e.target.value })}
                  placeholder="rtsp://192.168.1.40:554/stream1"
                  required
                />
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium mb-1">Camera Username</label>
                  <Input
                    value={camForm.username}
                    onChange={(e) => setCamForm({ ...camForm, username: e.target.value })}
                    placeholder="Optional"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium mb-1">Camera Password</label>
                  <Input
                    type="password"
                    value={camForm.password}
                    onChange={(e) => setCamForm({ ...camForm, password: e.target.value })}
                    placeholder="Encrypted with Fernet"
                  />
                </div>
              </div>
            </>
          )}

          <div>
            <label className="block text-xs font-medium mb-1">
              Crowd Alert Occupancy Threshold
            </label>
            <Input
              type="number"
              min={1}
              value={camForm.max_occupancy_threshold}
              onChange={(e) =>
                setCamForm({ ...camForm, max_occupancy_threshold: Number(e.target.value) })
              }
            />
          </div>

          {testResult && (
            <div
              className={`rounded-xl px-3.5 py-2.5 text-xs border ${
                testResult.reachable
                  ? "bg-[#EAF1ED] border-[#CFE0D6] text-[#22513C]"
                  : "bg-[#FBECEB] border-[#EDC8C6] text-[#9A3430]"
              }`}
            >
              <strong>{testResult.reachable ? "Reachable" : "Failed"}</strong> (
              {testResult.latency_ms}ms): {testResult.message}
            </div>
          )}

          <div className="flex items-center justify-between pt-2">
            <Button type="button" variant="secondary" onClick={handleTestNewCamera}>
              <Wifi className="w-3.5 h-3.5" />
              Test Connection
            </Button>
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={() => setAddModal(false)}>
                Cancel
              </Button>
              <Button type="submit">Save Camera</Button>
            </div>
          </div>
        </form>
      </Modal>

      {/* ONVIF Discovery Modal */}
      <Modal
        open={onvifModal}
        onClose={() => setOnvifModal(false)}
        title="ONVIF LAN Camera Discovery"
        subtitle="WS-Discovery multicast probe (239.255.255.250:3702) for ONVIF Profile S cameras."
      >
        {scanning ? (
          <div className="py-10 text-center space-y-2">
            <RefreshCw className="w-6 h-6 text-[#244738] animate-spin mx-auto" />
            <p className="text-xs text-[#5C655F]">Scanning local network for ONVIF cameras...</p>
          </div>
        ) : onvifDevices.length === 0 ? (
          <p className="py-8 text-center text-xs text-[#6B746E]">
            No ONVIF devices responded on this subnet.
          </p>
        ) : (
          <div className="space-y-3">
            {onvifDevices.map((dev) => (
              <div
                key={dev.ip_address}
                className="p-3.5 rounded-xl bg-white border border-[#E3DED2] flex items-center justify-between gap-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-[#19201C]">{dev.name}</span>
                    {dev.is_simulated_discovery && <Badge tone="amber">SIMULATED</Badge>}
                  </div>
                  <p className="text-[11px] font-mono text-[#5C655F] mt-0.5">
                    {dev.ip_address}:{dev.port} • {dev.manufacturer} {dev.model}
                  </p>
                </div>
                <Button size="sm" onClick={() => adoptOnvifDevice(dev)}>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Configure
                </Button>
              </div>
            ))}
          </div>
        )}
      </Modal>

      {/* Monitoring Zones Modal */}
      <Modal
        open={Boolean(zoneCamera)}
        onClose={() => setZoneCamera(null)}
        title={`Monitoring Zones — ${zoneCamera?.name || ""}`}
        subtitle="Define anonymous spatial zones for occupancy counting, entry/exit, restricted intrusion, and vacancy alerts."
      >
        {zoneCamera && (
          <div className="space-y-5">
            <div className="space-y-2">
              {zoneCamera.zones.length === 0 ? (
                <p className="text-xs text-[#6B746E]">No monitoring zones configured yet.</p>
              ) : (
                zoneCamera.zones.map((z) => (
                  <div
                    key={z.id}
                    className="p-3 rounded-xl bg-white border border-[#E3DED2] flex items-center justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-[#19201C]">{z.name}</span>
                        <Badge tone={z.zone_type === "restricted" ? "red" : "green"}>
                          {z.zone_type}
                        </Badge>
                      </div>
                      <p className="text-[11px] text-[#68716B] mt-0.5">
                        Max occupancy: {z.max_occupancy} • Vacancy alert: {z.vacancy_alert_minutes}m
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteZone(zoneCamera.id, z.id)}
                    >
                      <Trash2 className="w-3.5 h-3.5 text-[#A43E3A]" />
                    </Button>
                  </div>
                ))
              )}
            </div>

            <form
              onSubmit={handleAddZone}
              className="pt-4 border-t border-[#E5E0D5] space-y-3"
            >
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[#4D7361]">
                Add Monitoring Zone
              </h4>
              <div className="grid sm:grid-cols-2 gap-3">
                <Input
                  value={zoneForm.name}
                  onChange={(e) => setZoneForm({ ...zoneForm, name: e.target.value })}
                  placeholder="Zone Name (e.g. Server Rack Door)"
                  required
                />
                <Select
                  value={zoneForm.zone_type}
                  onChange={(e) =>
                    setZoneForm({
                      ...zoneForm,
                      zone_type: e.target.value as
                        | "workspace"
                        | "entry_exit"
                        | "restricted"
                        | "common_area",
                    })
                  }
                >
                  <option value="workspace">Workspace Occupancy</option>
                  <option value="entry_exit">Entry / Exit Line</option>
                  <option value="restricted">Restricted Area</option>
                  <option value="common_area">Common Area</option>
                </Select>
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] text-[#5C655F] mb-1">Max Occupancy</label>
                  <Input
                    type="number"
                    min={0}
                    value={zoneForm.max_occupancy}
                    onChange={(e) =>
                      setZoneForm({ ...zoneForm, max_occupancy: Number(e.target.value) })
                    }
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-[#5C655F] mb-1">
                    Extended Vacancy Alert (min)
                  </label>
                  <Input
                    type="number"
                    min={5}
                    value={zoneForm.vacancy_alert_minutes}
                    onChange={(e) =>
                      setZoneForm({
                        ...zoneForm,
                        vacancy_alert_minutes: Number(e.target.value),
                      })
                    }
                  />
                </div>
              </div>
              <div className="flex justify-end">
                <Button type="submit" size="sm">
                  <Plus className="w-3.5 h-3.5" />
                  Add Zone
                </Button>
              </div>
            </form>
          </div>
        )}
      </Modal>
    </div>
  );
}
