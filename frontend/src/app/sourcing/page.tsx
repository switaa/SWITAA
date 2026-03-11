"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

interface SourcingSearch {
  id: string;
  name: string;
  search_type: string;
  status: string;
  total_products: number;
  products_checked: number;
  matches_found: number;
  profitable_count: number;
  created_at: string;
  completed_at: string | null;
}

interface SourcingResult {
  id: string;
  asin: string;
  product_title: string | null;
  product_image: string | null;
  source_name: string;
  source_url: string;
  source_price: number;
  source_price_ht: number | null;
  amazon_price: number;
  net_profit: number;
  margin_pct: number;
  roi_pct: number;
  match_type: string;
  match_confidence: number;
  source_in_stock: boolean | null;
}

interface SourcingStats {
  total_searches: number;
  total_matches: number;
  profitable_matches: number;
  best_roi: number;
  avg_margin: number;
}

type SortBy = "roi" | "margin" | "profit" | "price";

export default function SourcingPage() {
  const [stats, setStats] = useState<SourcingStats | null>(null);
  const [searches, setSearches] = useState<SourcingSearch[]>([]);
  const [results, setResults] = useState<SourcingResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [sortBy, setSortBy] = useState<SortBy>("roi");
  const [profitableOnly, setProfitableOnly] = useState(true);
  const [activeSearchId, setActiveSearchId] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadData = useCallback(async () => {
    try {
      const [s, sr, r] = await Promise.all([
        api.get<SourcingStats>("/api/v1/sourcing/stats"),
        api.get<SourcingSearch[]>("/api/v1/sourcing/searches"),
        api.get<SourcingResult[]>(
          `/api/v1/sourcing/results?sort_by=${sortBy}&profitable_only=${profitableOnly}&limit=100${activeSearchId ? `&search_id=${activeSearchId}` : ""}`
        ),
      ]);
      setStats(s);
      setSearches(sr);
      setResults(r);
    } catch {
      /* noop */
    } finally {
      setLoading(false);
    }
  }, [sortBy, profitableOnly, activeSearchId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const triggerWebSearch = async () => {
    setSearching(true);
    try {
      await api.post("/api/v1/sourcing/search/web?min_score=30&max_products=50");
      setTimeout(loadData, 2000);
    } catch {
      /* noop */
    } finally {
      setSearching(false);
    }
  };

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const token = localStorage.getItem("access_token");
      const form = new FormData();
      form.append("file", file);
      form.append("source_name", file.name.replace(/\.\w+$/, ""));

      const res = await fetch(`${API_BASE}/api/v1/sourcing/search/csv`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      });

      if (!res.ok) throw new Error("Upload failed");
      await loadData();
    } catch {
      /* noop */
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const deleteSearch = async (id: string) => {
    await api.delete(`/api/v1/sourcing/searches/${id}`);
    if (activeSearchId === id) setActiveSearchId(null);
    loadData();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Sourcing</h1>
          <p className="text-sm text-gray-500 mt-1">
            Trouvez les meilleurs prix fournisseurs pour vos produits Amazon
          </p>
        </div>
        <div className="flex gap-3">
          <label className="cursor-pointer">
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.txt"
              className="hidden"
              onChange={handleCsvUpload}
            />
            <span className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border transition ${
              uploading
                ? "bg-gray-100 text-gray-400 cursor-wait"
                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
            }`}>
              {uploading ? "Import..." : "Importer CSV"}
            </span>
          </label>
          <button
            onClick={triggerWebSearch}
            disabled={searching}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {searching ? "Recherche..." : "Recherche Web"}
          </button>
        </div>
      </div>

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-5 gap-4">
          <StatCard label="Recherches" value={stats.total_searches} />
          <StatCard label="Correspondances" value={stats.total_matches} />
          <StatCard label="Rentables" value={stats.profitable_matches} color="green" />
          <StatCard label="Meilleur ROI" value={`${stats.best_roi}%`} color="blue" />
          <StatCard label="Marge moyenne" value={`${stats.avg_margin}%`} color="purple" />
        </div>
      )}

      {/* Searches history */}
      {searches.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Historique des recherches</h2>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveSearchId(null)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition ${
                !activeSearchId
                  ? "bg-blue-100 text-blue-700"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              Toutes
            </button>
            {searches.map((s) => (
              <div key={s.id} className="flex items-center gap-1">
                <button
                  onClick={() => setActiveSearchId(s.id)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition ${
                    activeSearchId === s.id
                      ? "bg-blue-100 text-blue-700"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {s.name}
                  <span className="ml-1 opacity-60">
                    ({s.profitable_count}/{s.matches_found})
                  </span>
                  {s.status === "running" && (
                    <span className="ml-1 inline-block w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
                  )}
                </button>
                <button
                  onClick={() => deleteSearch(s.id)}
                  className="text-gray-400 hover:text-red-500 p-0.5"
                  title="Supprimer"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M18 6L6 18M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Trier par :</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortBy)}
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5"
          >
            <option value="roi">ROI</option>
            <option value="margin">Marge</option>
            <option value="profit">Profit</option>
            <option value="price">Prix source</option>
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={profitableOnly}
            onChange={(e) => setProfitableOnly(e.target.checked)}
            className="rounded"
          />
          Rentables uniquement
        </label>
      </div>

      {/* Results table */}
      {results.length === 0 ? (
        <EmptyState onSearch={triggerWebSearch} searching={searching} />
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Produit</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Source</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Prix source</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Prix Amazon</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Profit net</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Marge</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">ROI</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Match</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {results.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50 transition">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        {r.product_image && (
                          <img
                            src={r.product_image}
                            alt=""
                            className="w-10 h-10 rounded object-cover border"
                          />
                        )}
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate max-w-xs">
                            {r.product_title || r.asin}
                          </p>
                          <p className="text-xs text-gray-400">{r.asin}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm text-gray-700">{r.source_name}</p>
                        {r.source_url && (
                          <a
                            href={r.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-blue-500 hover:underline"
                          >
                            Voir
                          </a>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-sm text-gray-700">
                      {r.source_price.toFixed(2)} &euro;
                      {r.source_price_ht && (
                        <span className="block text-xs text-gray-400">
                          {r.source_price_ht.toFixed(2)} &euro; HT
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-sm font-medium text-gray-900">
                      {r.amazon_price.toFixed(2)} &euro;
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`text-sm font-semibold ${r.net_profit > 0 ? "text-green-600" : "text-red-500"}`}>
                        {r.net_profit > 0 ? "+" : ""}{r.net_profit.toFixed(2)} &euro;
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-semibold ${
                        r.margin_pct >= 35
                          ? "bg-green-100 text-green-700"
                          : r.margin_pct >= 20
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-red-100 text-red-600"
                      }`}>
                        {r.margin_pct.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`text-sm font-bold ${r.roi_pct >= 100 ? "text-green-600" : r.roi_pct >= 50 ? "text-blue-600" : "text-gray-600"}`}>
                        {r.roi_pct.toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs ${
                        r.match_confidence >= 0.9
                          ? "bg-green-100 text-green-700"
                          : r.match_confidence >= 0.7
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-gray-100 text-gray-600"
                      }`}>
                        {r.match_type}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color = "gray" }: { label: string; value: string | number; color?: string }) {
  const colors: Record<string, string> = {
    gray: "bg-gray-50 text-gray-900",
    green: "bg-green-50 text-green-700",
    blue: "bg-blue-50 text-blue-700",
    purple: "bg-purple-50 text-purple-700",
  };
  return (
    <div className={`rounded-xl p-4 ${colors[color] || colors.gray}`}>
      <p className="text-xs font-medium opacity-60 uppercase">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
}

function EmptyState({ onSearch, searching }: { onSearch: () => void; searching: boolean }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
      <div className="text-4xl mb-4">🔎</div>
      <h3 className="text-lg font-semibold text-gray-900">Aucun resultat de sourcing</h3>
      <p className="text-sm text-gray-500 mt-2 max-w-md mx-auto">
        Lancez une recherche web pour trouver des prix fournisseurs, ou importez un fichier CSV
        de catalogue grossiste pour un matching automatique avec vos produits Amazon.
      </p>
      <div className="flex justify-center gap-3 mt-6">
        <button
          onClick={onSearch}
          disabled={searching}
          className="px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition"
        >
          {searching ? "Recherche en cours..." : "Lancer une recherche web"}
        </button>
      </div>
    </div>
  );
}
