export const SITE_NAME = "ListForge";

export const REPOSITORY_URL = "https://github.com/vrosi21/list-forge";

export const LEGAL_UPDATED = "21 September 2026";

export const THEME_STORAGE_KEY = "listforge.theme";

export interface Operator {
  readonly name: string;
  readonly email: string | null;
  readonly country: string | null;
}

export const OPERATOR: Operator = {
  name: process.env.NEXT_PUBLIC_OPERATOR_NAME ?? "the operator of this site",
  email: process.env.NEXT_PUBLIC_OPERATOR_EMAIL ?? null,
  country: process.env.NEXT_PUBLIC_OPERATOR_COUNTRY ?? null,
};
