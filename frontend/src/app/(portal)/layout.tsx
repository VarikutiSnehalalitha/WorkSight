"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  Bell,
  Building2,
  CalendarClock,
  CalendarDays,
  Camera,
  Eye,
  FileBarChart2,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useRealtime } from "@/lib/ws-context";
import { apiFetch } from "@/lib/api";
import { cn, formatRoleLabel } from "@/lib/utils";
import type { NotificationItem, UserRole } from "@/types";

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  roles: UserRole[];
  requiresCctv?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  {
    label: "Overview",
    href: "/",
    icon: LayoutDashboard,
    roles: ["super_admin", "hr_admin", "dept_manager", "employee"],
  },
  {
    label: "Employees",
    href: "/employees",
    icon: Users,
    roles: ["super_admin", "hr_admin", "dept_manager"],
  },
  {
    label: "Attendance",
    href: "/attendance",
    icon: CalendarClock,
    roles: ["super_admin", "hr_admin", "dept_manager", "employee"],
  },
  {
    label: "CCTV Monitoring",
    href: "/cctv",
    icon: Camera,
    roles: ["super_admin", "hr_admin"],
    requiresCctv: true,
  },
  {
    label: "AI Events",
    href: "/events",
    icon: Activity,
    roles: ["super_admin", "hr_admin", "dept_manager"],
  },
  {
    label: "Departments",
    href: "/departments",
    icon: Building2,
    roles: ["super_admin", "hr_admin", "dept_manager"],
  },
  {
    label: "Leave Management",
    href: "/leaves",
    icon: CalendarDays,
    roles: ["super_admin", "hr_admin", "dept_manager", "employee"],
  },
  {
    label: "Reports",
    href: "/reports",
    icon: FileBarChart2,
    roles: ["super_admin", "hr_admin", "dept_manager"],
  },
  {
    label: "Notifications",
    href: "/notifications",
    icon: Bell,
    roles: ["super_admin", "hr_admin", "dept_manager", "employee"],
  },
  {
    label: "Settings",
    href: "/settings",
    icon: Settings,
    roles: ["super_admin", "hr_admin", "employee"],
  },
];

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();
  const { connected, lastMessage } = useRealtime();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;
    apiFetch<NotificationItem[]>("/api/notifications?unread_only=true")
      .then((list) => setUnreadCount(list.length))
      .catch(() => {});
  }, [user, pathname, lastMessage]);

  useEffect(() => {
    if (!lastMessage) return;
    if (lastMessage.type === "vision_event" || lastMessage.type === "notification") {
      const payload = lastMessage.payload as Record<string, string> | undefined;
      const msg = payload?.description || payload?.title || "New real-time workplace update received.";
      setToast(msg);
      const t = setTimeout(() => setToast(null), 5500);
      return () => clearTimeout(t);
    }
  }, [lastMessage]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F6F4EE]">
        <div className="text-center space-y-3">
          <div className="h-10 w-10 mx-auto rounded-xl bg-[#244738] flex items-center justify-center animate-pulse">
            <Eye className="w-5 h-5 text-[#FAF8F4]" />
          </div>
          <p className="text-xs uppercase tracking-[0.2em] text-[#5C655F]">
            Initializing WorkSight...
          </p>
        </div>
      </div>
    );
  }

  const visibleNav = NAV_ITEMS.filter((item) => {
    if (!item.roles.includes(user.role)) return false;
    if (item.requiresCctv && !user.can_view_cctv) return false;
    return true;
  });

  const SidebarContent = (
    <div className="flex flex-col h-full bg-[#FCFBF8] border-r border-[#E3DED2]">
      {/* Brand Wordmark */}
      <div className="px-5 py-5 border-b border-[#EAE5DA] flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-[#244738] flex items-center justify-center shadow-xs">
            <Eye className="w-4 h-4 text-[#FAF8F4]" />
          </div>
          <div>
            <div className="font-serif text-xl leading-none text-[#19201C] tracking-tight">
              WorkSight
            </div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-[#6A746E] mt-1">
              {user.role === "employee" ? "Employee Portal" : "Enterprise Suite"}
            </div>
          </div>
        </Link>
        <button
          onClick={() => setMobileOpen(false)}
          className="lg:hidden p-1.5 rounded-lg text-[#5C655F] hover:bg-[#EDE9DF]"
          aria-label="Close navigation"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {visibleNav.map((item) => {
          const Icon = item.icon;
          const active =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors",
                active
                  ? "bg-[#244738] text-[#FAF8F4] shadow-xs"
                  : "text-[#49534D] hover:bg-[#EFECE4] hover:text-[#19201C]"
              )}
            >
              <span className="flex items-center gap-3">
                <Icon
                  className={cn(
                    "w-4 h-4",
                    active ? "text-[#CFE0D6]" : "text-[#6E7872]"
                  )}
                />
                <span>{item.label}</span>
              </span>
              {item.href === "/notifications" && unreadCount > 0 && (
                <span
                  className={cn(
                    "text-[11px] font-mono px-2 py-0.5 rounded-full",
                    active
                      ? "bg-[#FAF8F4]/20 text-[#FAF8F4]"
                      : "bg-[#B5673B] text-white"
                  )}
                >
                  {unreadCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Privacy & User Footer */}
      <div className="p-3.5 border-t border-[#EAE5DA] space-y-3 bg-[#F7F4ED]/60">
        <div className="flex items-center gap-2 px-2.5 py-2 rounded-xl bg-[#EAF1ED] border border-[#D4E2DA] text-[11px] text-[#234536]">
          <ShieldCheck className="w-4 h-4 shrink-0 text-[#244738]" />
          <span className="leading-tight">
            Zero facial recognition. Presence ≠ productivity.
          </span>
        </div>

        <div className="flex items-center justify-between gap-2 px-1">
          <div className="min-w-0">
            <p className="text-xs font-semibold text-[#19201C] truncate">
              {user.full_name}
            </p>
            <p className="text-[11px] text-[#5C655F] truncate">
              {formatRoleLabel(user.role)}
            </p>
            {user.managed_department_name && (
              <p className="text-[10px] text-[#4D7361] font-medium truncate">
                Scope: {user.managed_department_name}
              </p>
            )}
          </div>
          <button
            onClick={() => {
              logout();
              router.replace("/login");
            }}
            title="Sign out"
            className="p-2 rounded-lg text-[#5C655F] hover:bg-[#EAE5DA] hover:text-[#A43E3A] transition cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex bg-[#F6F4EE]">
      {/* Desktop Fixed Sidebar */}
      <aside className="hidden lg:block w-64 shrink-0 sticky top-0 h-screen">
        {SidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div className="w-72 max-w-[85vw] h-full">{SidebarContent}</div>
          <div
            className="flex-1 bg-[#19201C]/40 backdrop-blur-[1px]"
            onClick={() => setMobileOpen(false)}
          />
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="sticky top-0 z-30 h-15 bg-[#FCFBF8]/90 backdrop-blur-md border-b border-[#E3DED2] px-4 sm:px-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="lg:hidden p-2 rounded-xl border border-[#E3DED2] bg-white text-[#19201C]"
              aria-label="Open menu"
            >
              <Menu className="w-4 h-4" />
            </button>
            <div className="hidden sm:flex items-center gap-2 text-xs text-[#5C655F]">
              <span className="font-medium text-[#19201C]">
                {NAV_ITEMS.find((n) =>
                  n.href === "/" ? pathname === "/" : pathname.startsWith(n.href)
                )?.label || "WorkSight"}
              </span>
              <span>/</span>
              <span>{formatRoleLabel(user.role)}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div
              className={cn(
                "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border",
                connected
                  ? "bg-[#EAF1ED] text-[#244738] border-[#CFE0D6]"
                  : "bg-[#EFECE4] text-[#6B746E] border-[#E0DBD0]"
              )}
            >
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  connected ? "bg-[#2C7A56] animate-pulse" : "bg-[#9BA39D]"
                )}
              />
              {connected ? "Live Sync" : "Reconnecting"}
            </div>

            <Link
              href="/notifications"
              className="relative p-2 rounded-xl border border-[#E3DED2] bg-white hover:bg-[#FAF8F4] text-[#3A443E] transition"
              aria-label="Notifications"
            >
              <Bell className="w-4 h-4" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 h-4 min-w-4 px-1 rounded-full bg-[#B5673B] text-white text-[10px] font-mono flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </Link>
          </div>
        </header>

        {toast && (
          <div className="fixed bottom-5 right-5 z-50 max-w-sm rounded-2xl bg-[#1F3D30] text-[#FAF8F4] px-4 py-3 shadow-xl border border-[#3B6251] flex items-start gap-3">
            <Activity className="w-4 h-4 text-[#9CD3B8] shrink-0 mt-0.5" />
            <div className="text-xs leading-relaxed flex-1">
              <div className="font-semibold text-[#D6EAE0]">Real-Time Alert</div>
              <div className="mt-0.5 text-[#EAF2EE]">{toast}</div>
            </div>
            <button
              onClick={() => setToast(null)}
              className="text-[#A9C2B5] hover:text-white cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        <main className="flex-1 p-4 sm:p-8 max-w-[1440px] w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
