"use client";

import React from "react";
import { useAuth } from "@/lib/auth-context";
import { AdminDashboard } from "@/components/dashboard/AdminDashboard";
import { EmployeeDashboard } from "@/components/employee/EmployeeDashboard";

export default function OverviewPage() {
  const { user } = useAuth();
  if (!user) return null;
  if (user.role === "employee") {
    return <EmployeeDashboard />;
  }
  return <AdminDashboard />;
}
