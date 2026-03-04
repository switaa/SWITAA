"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

interface Campaign {
  id: string;
  name: string;
  niche: string;
  sub_niche: string;
  marketplace: string;
  status: string;
  phase: string;
  progress_pct: number;
  target_count: number;
  found_count: number;
  keywords: string[];
  created_at: string;
  completed_at: string | null;
  error_message: string;
}

interface ProductResult {
  id: string;
  asin: string;
  title: string;
  brand: string;
  category: string;
  marketplace: string;
  price: number;
  bsr: number | null;
  monthly_sales: number | null;
  review_count: number | null;
  rating: number | null;
  seller_count: number | null;
  image_url: string;
  amazon_is_seller: boolean | null;
  score: number | null;
  decision: string | null;
  keyword: string;
}

const DECISION_STYLES: Record<string, string> = {
  A_launch: "bg-green-100 text-green-700",
  B_review: "bg-yellow-100 text-yellow-700",
  C_drop: "bg-red-100 text-red-700",
};

const DECISION_LABELS: Record<string, string> = {
  A_launch: "Lancer",
  B_review: "A evaluer",
  C_drop: "Rejete",
};

export default function CampaignDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [results, setResults] = useState<ProductResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<string>("score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [filters, setFilters] = useState({
    minPrice: "",
    maxSellers: "",
    hideAmazon: false,
    minScore: "",
  });

  const fetchData = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (filters.minPrice) params.set("min_price", filters.minPrice);
      if (filters.maxSellers) params.set("max_sellers", filters.maxSellers);
      if (filters.hideAmazon) params.set("amazon_is_seller", "false");
      if (filters.minScore) params.set("min_score", filters.minScore);
      const qs = params.toString() ? `?${params.toString()}` : "";

      const [c, r] = await Promise.all([
        api.get<Campaign>(`/api/v1/campaigns/${id}`),
        api.get<ProductResult[]>(`/api/v1/campaigns/${id}/results${qs}`),
      ]);
      setCampaign(c);
      setResults(r);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [id, filters]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const sortedResults = [...results].sort((a, b) => {
    const av = (a as Record<string, unknown>)[sortKey];
    const bv = (b as Record<string, unknown>)[sortKey];
    const na = av == null ? -Infinity : Number(av);
    const nb = bv == null ? -Infinity : Number(bv);
    return sortDir === "asc" ? na - nb : nb - na;
  });

  const exportCSV = () => {
    if (!results.length) return;
    const headers = ["ASIN", "Titre", "Marque", "Prix", "BSR", "Ventes/mois", "Avis", "Vendeurs", "Amazon?", "Score", "Decision", "Mot-cle"];
    const rows = results.map((r) => [
      r.asin, `"${(r.title || "").replace(/"/g, '""')}"`, r.brand, r.price,
      r.bsr ?? "", r.monthly_sales ?? "", r.review_count ?? "", r.seller_count ?? "",
      r.amazon_is_seller === true ? "Oui" : r.amazon_is_seller === false ? "Non" : "",
      r.score ?? "", r.decision ?? "", r.keyword,
    ]);
    const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `campaign_${id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return <div className="text-center py-12 text-gray-400">Chargement...</div>;
  if (!campaign) return <div className="text-center py-12 text-red-500">Campagne introuvable</div>;

  return (
    <div>
      <div className="mb-6">
        <Link href="/research" className="text-blue-600 hover:text-blue-700 text-sm">
          &larr; Retour aux campagnes
        </Link>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{campaign.name}</h1>
            <div className="flex gap-4 mt-2 text-sm text-gray-500">
              <span>Niche: <strong>{campaign.niche}</strong></span>
              {campaign.sub_niche && <span>Sous-niche: <strong>{campaign.sub_niche}</strong></span>}
              <span>Trouve: <strong className="text-gray-900">{campaign.found_count}</strong> / {campaign.target_count}</span>
            </div>
          </div>
          <div className="flex gap-3 items-center">
            {campaign.status === "running" && (
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
                <span className="text-sm text-blue-600 font-medium">{campaign.phase} ({campaign.progress_pct}%)</span>
              </div>
            )}
            <button
              onClick={exportCSV}
              disabled={results.length === 0}
              className="px-4 py-2 text-sm bg-gray-800 text-white rounded-lg hover:bg-gray-900 disabled:opacity-50 transition"
            >
              Export CSV
            </button>
          </div>
        </div>

        {campaign.status === "running" && (
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div
                className="bg-blue-600 rounded-full h-2.5 transition-all duration-500"
                style={{ width: `${campaign.progress_pct}%` }}
              />
            </div>
          </div>
        )}

        {campaign.error_message && (
          <div className="mt-4 p-3 bg-red-50 border border-red-100 rounded-lg text-sm text-red-700">
            {campaign.error_message}
          </div>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Prix min</label>
            <input
              type="number"
              value={filters.minPrice}
              onChange={(e) => setFilters({ ...filters, minPrice: e.target.value })}
              className="w-24 px-3 py-1.5 border border-gray-200 rounded-lg text-sm"
              placeholder="35"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Max vendeurs</label>
            <input
              type="number"
              value={filters.maxSellers}
              onChange={(e) => setFilters({ ...filters, maxSellers: e.target.value })}
              className="w-24 px-3 py-1.5 border border-gray-200 rounded-lg text-sm"
              placeholder="6"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Score min</label>
            <input
              type="number"
              value={filters.minScore}
              onChange={(e) => setFilters({ ...filters, minScore: e.target.value })}
              className="w-24 px-3 py-1.5 border border-gray-200 rounded-lg text-sm"
              placeholder="50"
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-600 pb-1">
            <input
              type="checkbox"
              checked={filters.hideAmazon}
              onChange={(e) => setFilters({ ...filters, hideAmazon: e.target.checked })}
              className="rounded border-gray-300"
            />
            Exclure Amazon vendeur
          </label>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                {[
                  { key: "asin", label: "ASIN" },
                  { key: "title", label: "Titre" },
                  { key: "price", label: "Prix" },
                  { key: "bsr", label: "BSR" },
                  { key: "monthly_sales", label: "Ventes/mois" },
                  { key: "seller_count", label: "Vendeurs" },
                  { key: "review_count", label: "Avis" },
                  { key: "score", label: "Score" },
                  { key: "decision", label: "Decision" },
                ].map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-700 select-none"
                  >
                    {col.label}
                    {sortKey === col.key && (sortDir === "asc" ? " ↑" : " ↓")}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sortedResults.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-12 text-center text-gray-400">
                    {campaign.status === "running" ? "Recherche en cours..." : "Aucun resultat"}
                  </td>
                </tr>
              ) : (
                sortedResults.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50 transition">
                    <td className="px-4 py-3">
                      <a
                        href={`https://www.amazon.fr/dp/${r.asin}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline font-mono text-xs"
                      >
                        {r.asin}
                      </a>
                    </td>
                    <td className="px-4 py-3 max-w-xs truncate" title={r.title}>
                      {r.title}
                    </td>
                    <td className="px-4 py-3 font-medium">
                      {r.price > 0 ? `${r.price.toFixed(2)} EUR` : "-"}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {r.bsr != null ? r.bsr.toLocaleString() : "-"}
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {r.monthly_sales != null ? r.monthly_sales.toLocaleString() : "-"}
                    </td>
                    <td className="px-4 py-3">
                      <span className={r.seller_count != null && r.seller_count <= 5 ? "text-green-600 font-medium" : "text-gray-600"}>
                        {r.seller_count ?? "-"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {r.review_count != null ? r.review_count.toLocaleString() : "-"}
                    </td>
                    <td className="px-4 py-3">
                      {r.score != null ? (
                        <span className={`font-semibold ${r.score >= 70 ? "text-green-600" : r.score >= 40 ? "text-yellow-600" : "text-red-500"}`}>
                          {r.score.toFixed(0)}
                        </span>
                      ) : "-"}
                    </td>
                    <td className="px-4 py-3">
                      {r.decision ? (
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${DECISION_STYLES[r.decision] || "bg-gray-100 text-gray-600"}`}>
                          {DECISION_LABELS[r.decision] || r.decision}
                        </span>
                      ) : "-"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {results.length > 0 && (
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
            {results.length} produit{results.length > 1 ? "s" : ""} trouve{results.length > 1 ? "s" : ""}
            {results.filter((r) => r.decision === "A_launch").length > 0 && (
              <span className="ml-4 text-green-600 font-medium">
                {results.filter((r) => r.decision === "A_launch").length} a lancer
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
