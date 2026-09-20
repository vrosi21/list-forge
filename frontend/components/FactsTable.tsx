import type { ProductFacts } from "@/lib/api";
import { formatFact } from "@/lib/format";

const ROWS: ReadonlyArray<readonly [string, (facts: ProductFacts) => string]> = [
  ["SKU", (facts) => formatFact(facts.sku)],
  ["Name", (facts) => formatFact(facts.name)],
  ["Type", (facts) => formatFact(facts.product_type)],
  ["Stones", (facts) => formatFact(facts.stones)],
  ["Colours", (facts) => formatFact(facts.colours)],
  ["Materials", (facts) => formatFact(facts.materials)],
  ["Size (mm)", (facts) => formatFact(facts.size_mm)],
  ["Weight (g)", (facts) => formatFact(facts.weight_g)],
  ["Pieces", (facts) => formatFact(facts.pieces)],
  ["Origin", (facts) => formatFact(facts.origin)],
  ["Price (EUR)", (facts) => formatFact(facts.price_eur)],
];

export function FactsTable({ facts }: { facts: ProductFacts }) {
  return (
    <table className="w-full text-sm">
      <tbody className="divide-y divide-rule">
        {ROWS.map(([label, read]) => (
          <tr key={label}>
            <th scope="row" className="w-32 py-1.5 pr-3 text-left font-medium text-muted">
              {label}
            </th>
            <td className="py-1.5 font-mono text-xs text-ink">{read(facts)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
