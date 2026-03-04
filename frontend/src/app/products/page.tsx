"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { api } from "@/lib/api";

interface Product {
  id: string;
  asin: string;
  title: string;
  brand: string;
  category: string;
  marketplace: string;
  price: number;
  currency: string;
  bsr: number | null;
  monthly_sales: number | null;
  review_count: number | null;
  rating: number | null;
  seller_count: number | null;
  image_url: string | null;
  source: string;
  status: string;
  niche: string | null;
  sub_niche: string | null;
  amazon_is_seller: boolean | null;
  buybox_seller: string | null;
  price_stability: string | null;
}

type SortField = "price" | "bsr" | "monthly_sales" | "review_count";
type SortDir = "asc" | "desc";

const NICHES = [
  { value: "piscine", label: "Piscine" },
  { value: "chauffage", label: "Chauffage" },
  { value: "electromenager", label: "Électroménager" },
  { value: "automobile", label: "Automobile" },
  { value: "plomberie", label: "Plomberie" },
  { value: "jardinage", label: "Jardinage" },
  { value: "electricite", label: "Électricité" },
  { value: "outillage", label: "Outillage" },
];

const PAGE_SIZE = 50;

const fmtPrice = (n: number) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(n);

const fmtNum = (n: number | null | undefined) =>
  n != null ? n.toLocaleString("fr-FR") : "—";

const STABILITY_CLASSES: Record<string, string> = {
  stable: "bg-green-50 text-green-700 border border-green-200",
  fluctuant: "bg-amber-50 text-amber-700 border border-amber-200",
  volatile: "bg-red-50 text-red-700 border border-red-200",
};

const SOURCE_CLASSES: Record<string, string> = {
  helium10: "bg-purple-50 text-purple-700",
  keepa: "bg-sky-50 text-sky-700",
  spapi: "bg-orange-50 text-orange-700",
  csv_import: "bg-gray-100 text-gray-600",
  manual: "bg-gray-100 text-gray-600",
};

function RatingStars({ value }: { value: number | null }) {
  if (value == null) return <span className="text-gray-300 text-xs">—</span>;
  const rounded = Math.round(value);
  return (
    <span className="inline-flex items-center gap-px text-xs whitespace-nowrap">
      {[0, 1, 2, 3, 4].map((i) => (
        <span key={i} className={i < rounded ? "text-amber-400" : "text-gray-200"}>
          ★
        </span>
      ))}
      <span className="ml-1 text-gray-500">{value.toFixed(1)}</span>
    </span>
  );
}

function Badge({ children, className }: { children: React.ReactNode; className: string }) {
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${className}`}>
      {children}
    </span>
  );
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(false);

  const [search, setSearch] = useState("");
  const [niche, setNiche] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [page, setPage] = useState(0);
  const [sortField, setSortField] = useState<SortField | "">("");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("limit", String(PAGE_SIZE));
      params.set("offset", String(page * PAGE_SIZE));
      if (niche) params.set("niche", niche);
      if (minPrice) params.set("min_price", minPrice);
      if (maxPrice) params.set("max_price", maxPrice);
      if (sortField)
        params.set("sort_by", sortDir === "desc" ? `-${sortField}` : sortField);

      const data = await api.get<Product[]>(`/api/v1/products/?${params}`);
      setProducts(data);
      setHasMore(data.length === PAGE_SIZE);
    } catch {
      setProducts([]);
    } finally {
      setLoading(false);
    }
  }, [page, niche, minPrice, maxPrice, sortField, sortDir]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const displayed = useMemo(() => {
    if (!search.trim()) return products;
    const q = search.toLowerCase();
    return products.filter(
      (p) =>
        p.asin.toLowerCase().includes(q) || p.title.toLowerCase().includes(q)
    );
  }, [products, search]);

  const stats = useMemo(() => {
    if (!displayed.length)
      return { count: 0, avgPrice: 0, nicheMap: {} as Record<string, number> };
    const avgPrice =
      displayed.reduce((s, p) => s + (p.price || 0), 0) / displayed.length;
    const nicheMap: Record<string, number> = {};
    for (const p of displayed) {
      const k = p.niche || "autre";
      nicheMap[k] = (nicheMap[k] || 0) + 1;
    }
    return { count: displayed.length, avgPrice, nicheMap };
  }, [displayed]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("desc");
    }
    setPage(0);
  };

  const SortArrow = ({ field }: { field: SortField }) =>
    sortField === field ? (
      <span className="ml-1 text-blue-600">
        {sortDir === "asc" ? "↑" : "↓"}
      </span>
    ) : (
      <span className="ml-1 text-gray-300">↕</span>
    );

  const offset = page * PAGE_SIZE;

  return (
    <div className="space-y-5">
      {/* ── Header ── */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Produits</h1>
        <p className="text-sm text-gray-500 mt-1">
          Catalogue de produits Amazon analysés
        </p>
      </div>

      {/* ── Stats ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Produits affichés
          </p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{stats.count}</p>
          {displayed.length > 0 && (
            <p className="text-xs text-gray-400 mt-1">
              {offset + 1}–{offset + displayed.length} sur cette page
            </p>
          )}
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Prix moyen
          </p>
          <p className="text-3xl font-bold text-blue-600 mt-2">
            {stats.count > 0 ? fmtPrice(stats.avgPrice) : "—"}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Répartition par niche
          </p>
          <div className="flex flex-wrap gap-1.5 mt-3">
            {Object.entries(stats.nicheMap)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 6)
              .map(([n, c]) => (
                <Badge key={n} className="bg-blue-50 text-blue-700">
                  {n} ({c})
                </Badge>
              ))}
            {stats.count === 0 && (
              <span className="text-xs text-gray-300">—</span>
            )}
          </div>
        </div>
      </div>

      {/* ── Filters ── */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Recherche ASIN / Titre
            </label>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="B08XYZ… ou mot-clé"
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Niche
            </label>
            <select
              value={niche}
              onChange={(e) => {
                setNiche(e.target.value);
                setPage(0);
              }}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
            >
              <option value="">Toutes les niches</option>
              {NICHES.map((n) => (
                <option key={n.value} value={n.value}>
                  {n.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Prix min (€)
            </label>
            <input
              type="number"
              value={minPrice}
              onChange={(e) => {
                setMinPrice(e.target.value);
                setPage(0);
              }}
              placeholder="0"
              min={0}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Prix max (€)
            </label>
            <input
              type="number"
              value={maxPrice}
              onChange={(e) => {
                setMaxPrice(e.target.value);
                setPage(0);
              }}
              placeholder="9999"
              min={0}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
            />
          </div>
        </div>
      </div>

      {/* ── Table ── */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm whitespace-nowrap">
            <thead>
              <tr className="bg-gray-50/80 border-b border-gray-200 text-xs uppercase tracking-wide text-gray-500">
                <th className="pl-4 pr-2 py-3 w-12" />
                <th className="px-3 py-3 text-left font-medium">ASIN</th>
                <th className="px-3 py-3 text-left font-medium">Titre</th>
                <th className="px-3 py-3 text-left font-medium">Marque</th>
                <th className="px-3 py-3 text-left font-medium">Niche</th>
                <th
                  className="px-3 py-3 text-right font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("price")}
                >
                  Prix <SortArrow field="price" />
                </th>
                <th
                  className="px-3 py-3 text-right font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("bsr")}
                >
                  BSR <SortArrow field="bsr" />
                </th>
                <th
                  className="px-3 py-3 text-right font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("monthly_sales")}
                >
                  Ventes/mois <SortArrow field="monthly_sales" />
                </th>
                <th
                  className="px-3 py-3 text-right font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("review_count")}
                >
                  Avis <SortArrow field="review_count" />
                </th>
                <th className="px-3 py-3 text-left font-medium">Note</th>
                <th className="px-3 py-3 text-right font-medium">Vendeurs</th>
                <th className="px-3 py-3 text-center font-medium">Source</th>
                <th className="px-3 py-3 text-center font-medium">Stabilité prix</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    {Array.from({ length: 13 }).map((_, j) => (
                      <td key={j} className="px-3 py-3">
                        <div className="h-4 bg-gray-100 rounded w-full" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : displayed.length === 0 ? (
                <tr>
                  <td
                    colSpan={13}
                    className="px-4 py-16 text-center text-gray-400"
                  >
                    Aucun produit trouvé avec ces critères.
                  </td>
                </tr>
              ) : (
                displayed.map((p) => (
                  <tr
                    key={p.id}
                    className="hover:bg-blue-50/40 transition-colors"
                  >
                    {/* Image */}
                    <td className="pl-4 pr-2 py-2">
                      {p.image_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={p.image_url}
                          alt={p.title}
                          className="w-10 h-10 rounded-lg object-cover border border-gray-100"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display =
                              "none";
                          }}
                        />
                      ) : (
                        <div className="w-10 h-10 rounded-lg bg-gray-50 flex items-center justify-center text-gray-300 text-base">
                          📦
                        </div>
                      )}
                    </td>

                    {/* ASIN */}
                    <td className="px-3 py-2">
                      <a
                        href={`https://www.amazon.fr/dp/${p.asin}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-xs text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {p.asin}
                      </a>
                    </td>

                    {/* Title */}
                    <td className="px-3 py-2 max-w-[220px]">
                      <span
                        className="block truncate text-gray-800"
                        title={p.title}
                      >
                        {p.title}
                      </span>
                    </td>

                    {/* Brand */}
                    <td className="px-3 py-2 text-gray-500 text-xs">
                      {p.brand || "—"}
                    </td>

                    {/* Niche */}
                    <td className="px-3 py-2">
                      {p.niche ? (
                        <Badge className="bg-indigo-50 text-indigo-700">
                          {p.niche}
                        </Badge>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>

                    {/* Price */}
                    <td className="px-3 py-2 text-right font-semibold text-gray-900">
                      {fmtPrice(p.price)}
                    </td>

                    {/* BSR */}
                    <td className="px-3 py-2 text-right text-gray-600">
                      {fmtNum(p.bsr)}
                    </td>

                    {/* Monthly sales */}
                    <td className="px-3 py-2 text-right text-gray-600">
                      {fmtNum(p.monthly_sales)}
                    </td>

                    {/* Reviews */}
                    <td className="px-3 py-2 text-right text-gray-600">
                      {fmtNum(p.review_count)}
                    </td>

                    {/* Rating */}
                    <td className="px-3 py-2">
                      <RatingStars value={p.rating} />
                    </td>

                    {/* Sellers */}
                    <td className="px-3 py-2 text-right text-gray-600">
                      {p.seller_count ?? "—"}
                    </td>

                    {/* Source */}
                    <td className="px-3 py-2 text-center">
                      <Badge
                        className={
                          SOURCE_CLASSES[p.source?.toLowerCase()] ||
                          "bg-gray-100 text-gray-600"
                        }
                      >
                        {p.source || "—"}
                      </Badge>
                    </td>

                    {/* Price stability */}
                    <td className="px-3 py-2 text-center">
                      {p.price_stability ? (
                        <Badge
                          className={
                            STABILITY_CLASSES[
                              p.price_stability.toLowerCase()
                            ] || "bg-gray-100 text-gray-600"
                          }
                        >
                          {p.price_stability}
                        </Badge>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Pagination ── */}
      {!loading && (
        <div className="flex items-center justify-between bg-white rounded-xl border border-gray-200 px-5 py-3 shadow-sm">
          <p className="text-sm text-gray-500">
            {displayed.length > 0
              ? `${offset + 1}–${offset + displayed.length} produits`
              : "0 produit"}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => p - 1)}
              disabled={page === 0}
              className="px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-200 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              ← Précédent
            </button>
            <span className="text-sm font-medium text-gray-700 px-3">
              Page {page + 1}
            </span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasMore}
              className="px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-200 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              Suivant →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
