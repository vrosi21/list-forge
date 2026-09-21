import type { components } from "@/lib/api-types";

export type AccessStatus = components["schemas"]["AccessStatus"];
export type Brand = components["schemas"]["BrandSummary"];
export type Batch = components["schemas"]["Batch"];
export type BatchResponse = components["schemas"]["BatchResponse"];
export type BatchTotals = components["schemas"]["BatchTotals"];
export type Item = components["schemas"]["Item"];
export type Finding = components["schemas"]["Finding"];
export type GeneratedCopy = components["schemas"]["GeneratedCopy"];
export type Health = components["schemas"]["HealthResponse"];
export type ProductFacts = components["schemas"]["ProductFacts"];
export type Provenance = components["schemas"]["Provenance"];
export type Severity = components["schemas"]["Severity"];
export type Status = components["schemas"]["Status"];

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const ACCESS_HEADER = "X-Demo-Code";

export const UNAUTHORIZED = 401;

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number, options?: ErrorOptions) {
    super(message, options);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function listBrands(signal?: AbortSignal): Promise<Brand[]> {
  return request<Brand[]>("/brands", { signal });
}

export async function createBatch(
  file: File,
  brandId: string,
  accessCode: string | null,
): Promise<string> {
  const body = new FormData();
  body.append("file", file);
  body.append("brand_id", brandId);
  const created = await request<{ batch_id: string }>("/batches", {
    method: "POST",
    body,
    headers: accessHeaders(accessCode),
  });
  return created.batch_id;
}

export async function readBatch(batchId: string, signal?: AbortSignal): Promise<BatchResponse> {
  return request<BatchResponse>(`/batches/${encodeURIComponent(batchId)}`, { signal });
}

export async function regenerateItem(itemId: string, accessCode: string | null): Promise<Item> {
  return request<Item>(`/items/${encodeURIComponent(itemId)}/regenerate`, {
    method: "POST",
    headers: accessHeaders(accessCode),
  });
}

function accessHeaders(accessCode: string | null): HeadersInit | undefined {
  return accessCode ? { [ACCESS_HEADER]: accessCode } : undefined;
}

export async function checkAccess(
  accessCode: string | null,
  signal?: AbortSignal,
): Promise<AccessStatus> {
  return request<AccessStatus>("/access", { headers: accessHeaders(accessCode), signal });
}

export async function readHealth(signal?: AbortSignal): Promise<Health> {
  return request<Health>("/health", { signal });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, init);
  } catch (cause) {
    throw new ApiError(`the API at ${BASE_URL} could not be reached`, 0, { cause });
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(describe(payload, response.status), response.status);
  }
  return payload as T;
}

function describe(payload: unknown, status: number): string {
  const detail = isRecord(payload) ? payload.detail : null;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map(describeValidationError).join("; ");
  }
  return `the API answered ${status}`;
}

function describeValidationError(error: unknown): string {
  if (!isRecord(error)) {
    return "invalid request";
  }
  const location = Array.isArray(error.loc) ? error.loc.join(".") : "request";
  return `${location}: ${String(error.msg ?? "invalid")}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
