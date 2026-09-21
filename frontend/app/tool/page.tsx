import type { Metadata } from "next";
import { ToolScreen } from "@/components/ToolScreen";

export const metadata: Metadata = {
  title: "Tool",
};

export default function ToolPage() {
  return <ToolScreen />;
}
