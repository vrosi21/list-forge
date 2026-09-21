export const COLUMNS = [
  { key: "sku", label: "SKU", hint: "Unique id", width: "w-28" },
  { key: "name", label: "Name", hint: "Product name", width: "w-64" },
  { key: "product_type", label: "Type", hint: "tower, bracelet", width: "w-28" },
  { key: "stones", label: "Stones", hint: "a; b", width: "w-48" },
  { key: "colours", label: "Colours", hint: "a; b", width: "w-40" },
  { key: "materials", label: "Materials", hint: "a; b", width: "w-36" },
  { key: "size_mm", label: "Size mm", hint: "35", width: "w-20" },
  { key: "weight_g", label: "Weight g", hint: "150", width: "w-20" },
  { key: "pieces", label: "Pieces", hint: "1", width: "w-16" },
  { key: "origin", label: "Origin", hint: "Brazil", width: "w-28" },
  { key: "price_eur", label: "Price EUR", hint: "24.90", width: "w-20" },
] as const;

export type ColumnKey = (typeof COLUMNS)[number]["key"];

export type CatalogueRow = Readonly<Record<ColumnKey, string>>;

export const DEFAULT_MAX_ROWS = 5;

export const SAMPLE_ROWS: readonly CatalogueRow[] = [
  row({
    sku: "MS-AMT-101",
    name: "Amethyst Chevron Crystal Tower",
    product_type: "tower",
    stones: "amethyst",
    colours: "purple; white",
    pieces: "1",
  }),
  row({
    sku: "MS-RQZ-102",
    name: "Rose Quartz Crystal Sphere 35 mm",
    product_type: "sphere",
    stones: "rose quartz",
    colours: "pink",
    size_mm: "35",
    pieces: "1",
  }),
  row({
    sku: "BS-TGE-103",
    name: "Tiger's Eye Stretch Bracelet 8 mm",
    product_type: "bracelet",
    stones: "tiger's eye",
    colours: "brown; gold",
    materials: "elastic cord",
    size_mm: "8",
  }),
  row({
    sku: "MS-SEL-104",
    name: "Selenite Crystal Wand Cleansing Healing Tool",
    product_type: "wand",
    stones: "selenite",
    colours: "white",
    size_mm: "200",
    weight_g: "150",
    pieces: "1",
    origin: "Morocco",
  }),
  row({
    sku: "MS-CHK-105",
    name: "7 Chakra Tumbled Stone Set",
    product_type: "set",
    stones: "amethyst; lapis lazuli; carnelian; red jasper; green aventurine; sodalite; clear quartz",
    colours: "purple; blue; orange; red; green; clear",
    materials: "velvet pouch",
    size_mm: "25",
    pieces: "7",
    origin: "India",
  }),
];

export function row(values: Partial<Record<ColumnKey, string>> = {}): CatalogueRow {
  const empty = Object.fromEntries(COLUMNS.map((column) => [column.key, ""])) as Record<
    ColumnKey,
    string
  >;
  return { ...empty, ...values };
}

export function withCell(
  rows: readonly CatalogueRow[],
  index: number,
  key: ColumnKey,
  value: string,
): CatalogueRow[] {
  return rows.map((current, position) => (position === index ? { ...current, [key]: value } : current));
}

export function withoutRow(rows: readonly CatalogueRow[], index: number): CatalogueRow[] {
  return rows.filter((_, position) => position !== index);
}

export function withEmptyRow(rows: readonly CatalogueRow[], maxRows: number): CatalogueRow[] {
  return rows.length >= maxRows ? [...rows] : [...rows, row()];
}

export function filledRows(rows: readonly CatalogueRow[]): CatalogueRow[] {
  return rows.filter((current) => COLUMNS.some((column) => current[column.key].trim() !== ""));
}

export function toCsv(rows: readonly CatalogueRow[]): string {
  const header = COLUMNS.map((column) => column.key).join(",");
  const lines = rows.map((current) =>
    COLUMNS.map((column) => csvField(current[column.key].trim())).join(","),
  );
  return [header, ...lines].join("\n") + "\n";
}

export function missingRequired(rows: readonly CatalogueRow[]): number[] {
  return rows.flatMap((current, index) =>
    current.sku.trim() === "" || current.name.trim() === "" ? [index] : [],
  );
}

function csvField(value: string): string {
  return /[",\n\r]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}
