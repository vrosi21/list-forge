import { row, toCsv, type CatalogueRow } from "@/lib/catalogue";

export interface ReadyTest {
  readonly id: string;
  readonly title: string;
  readonly brandId: string;
  readonly summary: string;
  readonly expectation: string;
  readonly rows: readonly CatalogueRow[];
}

export const READY_TESTS: readonly ReadyTest[] = [
  {
    id: "complete-rows",
    title: "Complete rows",
    brandId: "mindful-souls",
    summary:
      "Five products with every fact filled in: size, weight, count, origin and price. The model has nothing to guess.",
    expectation: "Usually all approved.",
    rows: [
      row({
        sku: "MS-AMT-201",
        name: "Amethyst Chevron Crystal Tower",
        product_type: "tower",
        stones: "amethyst",
        colours: "purple; white",
        size_mm: "90",
        weight_g: "120",
        pieces: "1",
        origin: "Brazil",
        price_eur: "24.90",
      }),
      row({
        sku: "MS-RQZ-202",
        name: "Rose Quartz Sphere 35 mm",
        product_type: "sphere",
        stones: "rose quartz",
        colours: "pink",
        size_mm: "35",
        weight_g: "60",
        pieces: "1",
        origin: "Madagascar",
        price_eur: "18.50",
      }),
      row({
        sku: "MS-SMQ-203",
        name: "Smoky Quartz Palm Stone",
        product_type: "palm stone",
        stones: "smoky quartz",
        colours: "brown; grey",
        size_mm: "50",
        weight_g: "70",
        pieces: "1",
        origin: "Brazil",
        price_eur: "14.90",
      }),
      row({
        sku: "MS-CIT-204",
        name: "Citrine Cluster on Wooden Stand",
        product_type: "cluster",
        stones: "citrine",
        colours: "yellow; orange",
        materials: "wooden stand",
        size_mm: "80",
        weight_g: "210",
        pieces: "1",
        origin: "Brazil",
        price_eur: "32.00",
      }),
      row({
        sku: "MS-LAB-205",
        name: "Labradorite Worry Stone",
        product_type: "worry stone",
        stones: "labradorite",
        colours: "grey; blue",
        size_mm: "40",
        weight_g: "30",
        pieces: "1",
        origin: "Madagascar",
        price_eur: "9.90",
      }),
    ],
  },
  {
    id: "tempting-rows",
    title: "Rows that invite mistakes",
    brandId: "beads-and-stones",
    summary:
      "Five products whose names use words this brand bans, such as healing, chakra and aura, and rows that leave out counts and strand lengths.",
    expectation: "Usually several need review. Open one to see the flagged words in place.",
    rows: [
      row({
        sku: "BS-SEL-301",
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
        sku: "BS-CHK-302",
        name: "7 Chakra Tumbled Stone Set",
        product_type: "set",
        stones: "amethyst; lapis lazuli; carnelian; red jasper; green aventurine; sodalite; clear quartz",
        colours: "purple; blue; orange; red; green; clear",
        materials: "velvet pouch",
        size_mm: "25",
        pieces: "7",
        origin: "India",
      }),
      row({
        sku: "BS-MNS-303",
        name: "Rainbow Moonstone Aura Pendant",
        product_type: "pendant",
        stones: "moonstone",
        colours: "white",
        materials: "sterling silver",
      }),
      row({
        sku: "BS-LAP-304",
        name: "Lapis Lazuli Round Beads 6 mm",
        product_type: "beads",
        stones: "lapis lazuli",
        colours: "blue",
        size_mm: "6",
      }),
      row({
        sku: "BS-BTM-305",
        name: "Black Tourmaline Protection Bracelet",
        product_type: "bracelet",
        stones: "black tourmaline",
        colours: "black",
        materials: "elastic cord",
        size_mm: "8",
      }),
    ],
  },
];

export function readyTestFile(test: ReadyTest): File {
  return new File([toCsv(test.rows)], `${test.id}.csv`, { type: "text/csv" });
}
