"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { api } from "@/lib/api";

interface TopProduct {
  id: string;
  asin: string;
  title: string;
  brand: string;
  niche: string | null;
  price: number;
  buybox_price: number | null;
  bsr: number | null;
  monthly_sales: number | null;
  seller_count: number | null;
  review_count: number | null;
  rating: number | null;
  amazon_is_seller: boolean | null;
  score: number;
  max_cost_price: number;
  total_fees: number;
  image_url: string;
}

interface ProfitCalc {
  selling_price: number;
  cost_price: number;
  referral_fee: number;
  fba_fee: number;
  shipping_to_fba: number;
  total_fees: number;
  net_profit: number;
  margin_pct: number;
  roi: number;
  break_even_cost: number;
}

interface EnrichStatus {
  loading: boolean;
  result: string | null;
}

type SortField = "score" | "price" | "max_cost_price" | "bsr" | "monthly_sales";
type SortDir = "asc" | "desc";

const fmtPrice = (n: number) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(n);

const fmtNum = (n: number | null | undefined) =>
  n != null ? n.toLocaleString("fr-FR") : "\u2014";

export default function ProfitabilityPage() {
  const [products, setProducts] = useState<TopProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [minScore, setMinScore] = useState(40);
  const [maxBsr, setMaxBsr] = useState(100000);
  const [targetMargin, setTargetMargin] = useState(35);
  const [excludeAmazon, setExcludeAmazon] = useState(true);

  const [calcPrice, setCalcPrice] = useState("50");
  const [calcCost, setCalcCost] = useState("20");
  const [calcWeight, setCalcWeight] = useState("0.5");
  const [calcResult, setCalcResult] = useState<ProfitCalc | null>(null);

  const [enrichStatus, setEnrichStatus] = useState<EnrichStatus>({ loading: false, result: null });
  const [profitStatus, setProfitStatus] = useState<EnrichStatus>({ loading: false, result: null });

  const [sortField, setSortField] = useState<SortField>("score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const fetchTopProducts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("min_score", String(minScore));
      params.set("max_bsr", String(maxBsr));
      params.set("target_margin", String(targetMargin));
      params.set("exclude_amazon_seller", String(excludeAmazon));
      params.set("limit", "100");
      const data = await api.get<TopProduct[]>(`/api/v1/products/top?${params}`);
      setProducts(data);
    } catch {
      setProducts([]);
    } finally {
      setLoading(false);
    }
  }, [minScore, maxBsr, targetMargin, excludeAmazon]);

  useEffect(() => {
    fetchTopProducts();
  }, [fetchTopProducts]);

  const sorted = useMemo(() => {
    const arr = [...products];
    const dir = sortDir === "asc" ? 1 : -1;
    arr.sort((a, b) => {
      const va = a[sortField] ?? 0;
      const vb = b[sortField] ?? 0;
      return ((va as number) - (vb as number)) * dir;
    });
    return arr;
  }, [products, sortField, sortDir]);

  const stats = useMemo(() => {
    if (!products.length)
      return { count: 0, avgPrice: 0, avgMaxCost: 0, avgFees: 0, potentialRevenue: 0 };
    const avgPrice = products.reduce((s, p) => s + (p.buybox_price || p.price), 0) / products.length;
    const avgMaxCost = products.reduce((s, p) => s + p.max_cost_price, 0) / products.length;
    const avgFees = products.reduce((s, p) => s + p.total_fees, 0) / products.length;
    const potentialRevenue = products.reduce(
      (s, p) => s + (p.monthly_sales || 0) * (p.buybox_price || p.price),
      0
    );
    return { count: products.length, avgPrice, avgMaxCost, avgFees, potentialRevenue };
  }, [products]);

  const handleCalc = async () => {
    try {
      const result = await api.post<ProfitCalc>("/api/v1/products/calc-profit", {
        selling_price: parseFloat(calcPrice),
        cost_price: parseFloat(calcCost),
        weight_kg: parseFloat(calcWeight) || null,
      });
      setCalcResult(result);
    } catch {
      setCalcResult(null);
    }
  };

  const handleEnrichSPAPI = async () => {
    setEnrichStatus({ loading: true, result: null });
    try {
      const data = await api.post<{ enriched: number; errors: number; remaining: number }>(
        "/api/v1/products/enrich-spapi?source=helium10_blackbox"
      );
      setEnrichStatus({
        loading: false,
        result: `${data.enriched} produits enrichis, ${data.errors} erreurs, ${data.remaining} restants`,
      });
      fetchTopProducts();
    } catch (e) {
      setEnrichStatus({ loading: false, result: `Erreur: ${e}` });
    }
  };

  const handleRecalcProfitability = async () => {
    setProfitStatus({ loading: true, result: null });
    try {
      const data = await api.post<{ updated: number }>(
        `/api/v1/products/recalc-profitability?target_margin_pct=${targetMargin}`
      );
      setProfitStatus({ loading: false, result: `${data.updated} opportunites mises a jour` });
      fetchTopProducts();
    } catch (e) {
      setProfitStatus({ loading: false, result: `Erreur: ${e}` });
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  };

  const SortArrow = ({ field }: { field: SortField }) =>
    sortField === field ? (
      <span className="ml-1 text-blue-600">{sortDir === "asc" ? "\u2191" : "\u2193"}</span>
    ) : (
      <span className="ml-1 text-gray-300">\u2195</span>
    );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Rentabilite FBA</h1>
        <p className="text-sm text-gray-500 mt-1">
          Analyse de rentabilite, frais Amazon et Top 100 produits
        </p>
      </div>

      {/* Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Enrichissement SP-API (gratuit)</h3>
          <p className="text-xs text-gray-500 mb-4">
            Recupere les prix competitifs, BuyBox et donnees vendeurs via Amazon SP-API.
          </p>
          <button
            onClick={handleEnrichSPAPI}
            disabled={enrichStatus.loading}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {enrichStatus.loading ? "Enrichissement en cours..." : "Enrichir via SP-API"}
          </button>
          {enrichStatus.result && (
            <p className="mt-3 text-xs text-gray-600 bg-gray-50 rounded-lg p-2">{enrichStatus.result}</p>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Recalculer la rentabilite</h3>
          <p className="text-xs text-gray-500 mb-4">
            Recalcule les frais FBA et le prix d&apos;achat max pour toutes les opportunites.
          </p>
          <button
            onClick={handleRecalcProfitability}
            disabled={profitStatus.loading}
            className="px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition"
          >
            {profitStatus.loading ? "Calcul en cours..." : "Recalculer"}
          </button>
          {profitStatus.result && (
            <p className="mt-3 text-xs text-gray-600 bg-gray-50 rounded-lg p-2">{profitStatus.result}</p>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Top produits</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{stats.count}</p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Prix moyen</p>
          <p className="text-2xl font-bold text-blue-600 mt-2">
            {stats.count > 0 ? fmtPrice(stats.avgPrice) : "\u2014"}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Cout achat max moy.</p>
          <p className="text-2xl font-bold text-emerald-600 mt-2">
            {stats.count > 0 ? fmtPrice(stats.avgMaxCost) : "\u2014"}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Frais Amazon moy.</p>
          <p className="text-2xl font-bold text-orange-600 mt-2">
            {stats.count > 0 ? fmtPrice(stats.avgFees) : "\u2014"}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">CA potentiel/mois</p>
          <p className="text-2xl font-bold text-purple-600 mt-2">
            {stats.count > 0 ? fmtPrice(stats.potentialRevenue) : "\u2014"}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Score min: <span className="font-bold text-gray-900">{minScore}</span>
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">BSR max</label>
            <input
              type="number"
              value={maxBsr}
              onChange={(e) => setMaxBsr(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Marge cible: <span className="font-bold text-gray-900">{targetMargin}%</span>
            </label>
            <input
              type="range"
              min={10}
              max={60}
              value={targetMargin}
              onChange={(e) => setTargetMargin(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
            />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={excludeAmazon}
                onChange={(e) => setExcludeAmazon(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">Exclure Amazon vendeur</span>
            </label>
          </div>
        </div>
      </div>

      {/* Calculator */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Calculateur de rentabilite</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Prix de vente</label>
            <input
              type="number"
              value={calcPrice}
              onChange={(e) => setCalcPrice(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Cout d&apos;achat</label>
            <input
              type="number"
              value={calcCost}
              onChange={(e) => setCalcCost(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Poids (kg)</label>
            <input
              type="number"
              value={calcWeight}
              onChange={(e) => setCalcWeight(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              step="0.1"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={handleCalc}
              className="w-full px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition"
            >
              Calculer
            </button>
          </div>
        </div>

        {calcResult && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { label: "Frais referral (15%)", value: fmtPrice(calcResult.referral_fee), color: "text-orange-600" },
              { label: "Frais FBA", value: fmtPrice(calcResult.fba_fee), color: "text-orange-600" },
              { label: "Total frais", value: fmtPrice(calcResult.total_fees), color: "text-red-600" },
              {
                label: "Profit net",
                value: fmtPrice(calcResult.net_profit),
                color: calcResult.net_profit >= 0 ? "text-emerald-600" : "text-red-600",
              },
              {
                label: "Marge",
                value: `${calcResult.margin_pct.toFixed(1)}%`,
                color: calcResult.margin_pct >= 35 ? "text-emerald-600" : "text-amber-600",
              },
            ].map((item) => (
              <div key={item.label} className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500">{item.label}</p>
                <p className={`text-lg font-bold ${item.color} mt-1`}>{item.value}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Top Products Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3 border-b border-gray-200 bg-gray-50/50">
          <h3 className="text-sm font-semibold text-gray-700">
            Top {products.length} produits — Marge cible {targetMargin}%
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm whitespace-nowrap">
            <thead>
              <tr className="bg-gray-50/80 border-b border-gray-200 text-xs uppercase tracking-wide text-gray-500">
                <th className="pl-4 pr-2 py-3 w-12" />
                <th className="px-3 py-3 text-left font-medium">ASIN</th>
                <th className="px-3 py-3 text-left font-medium">Titre</th>
                <th className="px-3 py-3 text-left font-medium">Niche</th>
                <th
                  className="px-3 py-3 text-right font-medium cursor-pointer select-none hover:text-blue-600"
                  onClick={() => handleSort("price")}
                >
                  Prix <SortArrow field="price" />
                </th>
                <th className="px-3 py-3 text-right font-medium">BuyBox</th>
                <th
                  className="px-3 py-3 text-right font-medium cursor-pointer select-none hover:text-blue-600"
                  onClick={() => handleSort("max_cost_price")}
                >
                  Cout max <SortArrow field="max_cost_price" />
                </th>
                <th className="px-3 py-3 text-right font-medium">Frais</th>
                <th
                  className="px-3 py-3 text-right font-medium cursor-pointer select-none hover:text-blue-600"
                  onClick={() => handleSort("bsr")}
                >
                  BSR <SortArrow field="bsr" />
                </th>
                <th
                  className="px-3 py-3 text-right font-medium cursor-pointer select-none hover:text-blue-600"
                  onClick={() => handleSort("monthly_sales")}
                >
                  Ventes/m <SortArrow field="monthly_sales" />
                </th>
                <th className="px-3 py-3 text-right font-medium">Vendeurs</th>
                <th
                  className="px-3 py-3 text-center font-medium cursor-pointer select-none hover:text-blue-600"
                  onClick={() => handleSort("score")}
                >
                  Score <SortArrow field="score" />
                </th>
                <th className="px-3 py-3 text-center font-medium">Amazon?</th>
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
              ) : sorted.length === 0 ? (
                <tr>
                  <td colSpan={13} className="px-4 py-16 text-center text-gray-400">
                    Aucun produit ne correspond aux criteres.
                  </td>
                </tr>
              ) : (
                sorted.map((p) => (
                  <tr key={p.id} className="hover:bg-blue-50/40 transition-colors">
                    <td className="pl-4 pr-2 py-2">
                      {p.image_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={p.image_url}
                          alt={p.title}
                          className="w-10 h-10 rounded-lg object-cover border border-gray-100"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = "none";
                          }}
                        />
                      ) : (
                        <div className="w-10 h-10 rounded-lg bg-gray-50 flex items-center justify-center text-gray-300">
                          -
                        </div>
                      )}
                    </td>
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
                    <td className="px-3 py-2 max-w-[200px]">
                      <span className="block truncate text-gray-800" title={p.title}>
                        {p.title}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      {p.niche ? (
                        <span className="inline-block px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full text-xs font-medium">
                          {p.niche}
                        </span>
                      ) : (
                        <span className="text-gray-300">{"\u2014"}</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right font-semibold text-gray-900">
                      {fmtPrice(p.price)}
                    </td>
                    <td className="px-3 py-2 text-right text-gray-600">
                      {p.buybox_price ? fmtPrice(p.buybox_price) : "\u2014"}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <span
                        className={`font-bold ${p.max_cost_price > 0 ? "text-emerald-600" : "text-gray-400"}`}
                      >
                        {p.max_cost_price > 0 ? fmtPrice(p.max_cost_price) : "\u2014"}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right text-orange-600 text-xs">
                      {fmtPrice(p.total_fees)}
                    </td>
                    <td className="px-3 py-2 text-right text-gray-600">{fmtNum(p.bsr)}</td>
                    <td className="px-3 py-2 text-right text-gray-600">{fmtNum(p.monthly_sales)}</td>
                    <td className="px-3 py-2 text-right text-gray-600">{p.seller_count ?? "\u2014"}</td>
                    <td className="px-3 py-2 text-center">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded-lg font-bold text-sm tabular-nums ${
                          p.score >= 70
                            ? "bg-green-50 text-green-700"
                            : p.score >= 40
                              ? "bg-yellow-50 text-yellow-700"
                              : "bg-red-50 text-red-700"
                        }`}
                      >
                        {p.score.toFixed(1)}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-center">
                      {p.amazon_is_seller === true ? (
                        <span className="inline-block px-2 py-0.5 bg-red-50 text-red-600 rounded-full text-xs font-medium">
                          Oui
                        </span>
                      ) : p.amazon_is_seller === false ? (
                        <span className="inline-block px-2 py-0.5 bg-green-50 text-green-600 rounded-full text-xs font-medium">
                          Non
                        </span>
                      ) : (
                        <span className="text-gray-300">{"\u2014"}</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
