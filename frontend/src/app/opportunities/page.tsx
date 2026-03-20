"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useToast } from "@/components/toast";
import ActionBar from "@/components/action-bar";

interface Opportunity {
  id: string;
  asin: string;
  title: string;
  price: number;
  cost_price: number;
  margin_pct: number;
  score: number;
  decision: string;
  marketplace: string;
  niche: string | null;
  sub_niche: string | null;
  competition_score: number;
  demand_score: number;
  bsr_score: number;
  margin_score: number;
  seller_count: number | null;
  source: string;
  source_url: string | null;
  gross_roi: number | null;
  monthly_sales: number | null;
  bsr: number | null;
  est_monthly_revenue: number | null;
  unlock_priority: number | null;
}

type SortField = "score" | "price" | "decision" | "margin_pct" | "cost_price" | "gross_roi" | "monthly_sales" | "est_monthly_revenue" | "bsr" | "unlock_priority";
type SortDir = "asc" | "desc";

const NICHES = [
  { value: "piscine", label: "Piscine" },
  { value: "chauffage", label: "Chauffage" },
  { value: "electromenager", label: "Electromenager" },
  { value: "automobile", label: "Automobile" },
  { value: "plomberie", label: "Plomberie" },
  { value: "jardinage", label: "Jardinage" },
  { value: "electricite", label: "Electricite" },
  { value: "outillage", label: "Outillage" },
];

const DECISIONS = [
  { value: "A_launch", label: "A \u2014 Lancer" },
  { value: "B_review", label: "B \u2014 A revoir" },
  { value: "C_drop", label: "C \u2014 Abandonner" },
];

const SOURCES = [
  { value: "octopia", label: "OCTOPIA" },
  { value: "tactical_arbitrage", label: "Tactical Arbitrage" },
  { value: "helium10_blackbox", label: "Helium 10" },
  { value: "amazon_search", label: "Amazon Search" },
];

const PAGE_SIZE = 50;

const fmtPrice = (n: number) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(n);

const fmtNum = (n: number) =>
  new Intl.NumberFormat("fr-FR").format(Math.round(n));

const MARKETPLACE_FLAGS: Record<string, { flag: string; label: string }> = {
  amazon_fr: { flag: "\u{1F1EB}\u{1F1F7}", label: "Amazon France" },
  amazon_de: { flag: "\u{1F1E9}\u{1F1EA}", label: "Amazon Allemagne" },
  amazon_es: { flag: "\u{1F1EA}\u{1F1F8}", label: "Amazon Espagne" },
  amazon_it: { flag: "\u{1F1EE}\u{1F1F9}", label: "Amazon Italie" },
  amazon_co_uk: { flag: "\u{1F1EC}\u{1F1E7}", label: "Amazon UK" },
  amazon_nl: { flag: "\u{1F1F3}\u{1F1F1}", label: "Amazon Pays-Bas" },
  amazon_be: { flag: "\u{1F1E7}\u{1F1EA}", label: "Amazon Belgique" },
  amazon_com: { flag: "\u{1F1FA}\u{1F1F8}", label: "Amazon US" },
};

function getSourceCountry(sourceUrl: string | null): { flag: string; label: string } | null {
  if (!sourceUrl) return null;
  try {
    const host = new URL(sourceUrl).hostname;
    if (host.endsWith(".fr")) return { flag: "\u{1F1EB}\u{1F1F7}", label: "France" };
    if (host.endsWith(".de")) return { flag: "\u{1F1E9}\u{1F1EA}", label: "Allemagne" };
    if (host.endsWith(".es")) return { flag: "\u{1F1EA}\u{1F1F8}", label: "Espagne" };
    if (host.endsWith(".it")) return { flag: "\u{1F1EE}\u{1F1F9}", label: "Italie" };
    if (host.endsWith(".co.uk")) return { flag: "\u{1F1EC}\u{1F1E7}", label: "UK" };
    if (host.endsWith(".nl")) return { flag: "\u{1F1F3}\u{1F1F1}", label: "Pays-Bas" };
    if (host.endsWith(".be")) return { flag: "\u{1F1E7}\u{1F1EA}", label: "Belgique" };
    if (host.endsWith(".com")) return { flag: "\u{1F1FA}\u{1F1F8}", label: "US" };
  } catch { /* invalid URL */ }
  return null;
}

const DECISION_STYLES: Record<string, string> = {
  A_launch: "bg-green-100 text-green-700 border-green-200",
  B_review: "bg-yellow-100 text-yellow-700 border-yellow-200",
  C_drop: "bg-red-100 text-red-700 border-red-200",
};

const DECISION_LABELS: Record<string, string> = {
  A_launch: "Lancer",
  B_review: "A revoir",
  C_drop: "Abandonner",
};

function ScoreBar({ value, label }: { value: number; label: string }) {
  const pct = Math.min(100, Math.max(0, value));
  const color =
    pct >= 70 ? "bg-green-400" : pct >= 40 ? "bg-amber-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-1.5" title={`${label}: ${value.toFixed(1)}`}>
      <div className="w-14 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-500 w-6 text-right tabular-nums">
        {Math.round(value)}
      </span>
    </div>
  );
}

function DecisionBadge({ decision }: { decision: string }) {
  return (
    <span
      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold border whitespace-nowrap ${
        DECISION_STYLES[decision] || "bg-gray-100 text-gray-600 border-gray-200"
      }`}
    >
      {DECISION_LABELS[decision] || decision}
    </span>
  );
}

function ScoreCell({ score }: { score: number }) {
  const bg =
    score >= 70
      ? "bg-green-50 text-green-700"
      : score >= 40
        ? "bg-yellow-50 text-yellow-700"
        : "bg-red-50 text-red-700";
  return (
    <span className={`inline-block px-2.5 py-0.5 rounded-lg font-bold text-sm tabular-nums ${bg}`}>
      {score.toFixed(1)}
    </span>
  );
}

export default function OpportunitiesPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [allData, setAllData] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const [niche, setNiche] = useState("");
  const [decision, setDecision] = useState("");
  const [source, setSource] = useState("");
  const [localScore, setLocalScore] = useState(0);
  const [minScore, setMinScore] = useState(0);

  const [sortField, setSortField] = useState<SortField>("score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(0);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [strategy, setStrategy] = useState("clone_best");
  const [fulfillmentMode, setFulfillmentMode] = useState("FBM");

  useEffect(() => {
    const timer = setTimeout(() => setMinScore(localScore), 300);
    return () => clearTimeout(timer);
  }, [localScore]);

  useEffect(() => {
    setLoading(true);
    setPage(0);
    setSelected(new Set());
    const params = new URLSearchParams();
    params.set("limit", "200");
    if (minScore > 0) params.set("min_score", String(minScore));
    if (decision) params.set("decision", decision);
    if (niche) params.set("niche", niche);
    if (source) params.set("source", source);

    api
      .get<Opportunity[]>(`/api/v1/scoring/opportunities?${params}`)
      .then(setAllData)
      .catch(() => setAllData([]))
      .finally(() => setLoading(false));
  }, [minScore, decision, niche, source]);

  const summary = useMemo(
    () => ({
      total: allData.length,
      aLaunch: allData.filter((o) => o.decision === "A_launch").length,
      bReview: allData.filter((o) => o.decision === "B_review").length,
      cDrop: allData.filter((o) => o.decision === "C_drop").length,
    }),
    [allData],
  );

  const sorted = useMemo(() => {
    const arr = [...allData];
    const dir = sortDir === "asc" ? 1 : -1;
    arr.sort((a, b) => {
      if (sortField === "score") return (a.score - b.score) * dir;
      if (sortField === "price") return (a.price - b.price) * dir;
      if (sortField === "cost_price") return (a.cost_price - b.cost_price) * dir;
      if (sortField === "margin_pct") return (a.margin_pct - b.margin_pct) * dir;
      if (sortField === "gross_roi") return ((a.gross_roi ?? 0) - (b.gross_roi ?? 0)) * dir;
      if (sortField === "monthly_sales") return ((a.monthly_sales ?? 0) - (b.monthly_sales ?? 0)) * dir;
      if (sortField === "est_monthly_revenue") return ((a.est_monthly_revenue ?? 0) - (b.est_monthly_revenue ?? 0)) * dir;
      if (sortField === "bsr") return ((a.bsr ?? 999999) - (b.bsr ?? 999999)) * dir;
      if (sortField === "unlock_priority") return ((a.unlock_priority ?? 0) - (b.unlock_priority ?? 0)) * dir;
      if (sortField === "decision") return a.decision.localeCompare(b.decision) * dir;
      return 0;
    });
    return arr;
  }, [allData, sortField, sortDir]);

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  const displayed = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("desc");
    }
    setPage(0);
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === displayed.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(displayed.map((o) => o.id)));
    }
  };

  const selectAllALaunch = () => {
    const ids = allData.filter((o) => o.decision === "A_launch").map((o) => o.id);
    setSelected(new Set(ids));
  };

  const handleGenerate = async () => {
    if (selected.size === 0) return;
    setGenerating(true);
    try {
      const res = await api.post<{
        total_opportunities: number;
        listings_created: number;
        listings_updated: number;
        errors: number;
      }>("/api/v1/listings/generate-batch", {
        strategy,
        min_score: 0,
        decision: null,
        limit: selected.size,
      });

      toast(
        `${res.listings_created} listing${res.listings_created > 1 ? "s" : ""} genere${res.listings_created > 1 ? "s" : ""}${res.errors > 0 ? `, ${res.errors} erreur${res.errors > 1 ? "s" : ""}` : ""}`,
        res.errors > 0 ? "error" : "success",
        { href: "/listings", label: "Voir les listings" },
      );
      setSelected(new Set());
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Erreur inconnue";
      toast(`Erreur de generation : ${message}`, "error");
    } finally {
      setGenerating(false);
    }
  };

  const SortArrow = ({ field }: { field: SortField }) =>
    sortField === field ? (
      <span className="ml-1 text-blue-600">{sortDir === "asc" ? "\u2191" : "\u2193"}</span>
    ) : (
      <span className="ml-1 text-gray-300">{"\u2195"}</span>
    );

  const allChecked = displayed.length > 0 && selected.size === displayed.length;
  const someChecked = selected.size > 0 && selected.size < displayed.length;

  return (
    <div className="space-y-5 pb-20">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Opportunites</h1>
          <p className="text-sm text-gray-500 mt-1">
            Produits analyses et scores par l&apos;algorithme
          </p>
        </div>
        {summary.aLaunch > 0 && (
          <button
            onClick={selectAllALaunch}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-green-600 text-white hover:bg-green-700 transition shadow-sm"
          >
            Selectionner les {summary.aLaunch} A_launch
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Total</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{summary.total}</p>
        </div>
        <div className="bg-white rounded-xl border-l-4 border-l-green-500 border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-green-600 uppercase tracking-wide">
            A &mdash; Lancer
          </p>
          <p className="text-3xl font-bold text-green-700 mt-2">{summary.aLaunch}</p>
        </div>
        <div className="bg-white rounded-xl border-l-4 border-l-yellow-500 border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-yellow-600 uppercase tracking-wide">
            B &mdash; A revoir
          </p>
          <p className="text-3xl font-bold text-yellow-700 mt-2">{summary.bReview}</p>
        </div>
        <div className="bg-white rounded-xl border-l-4 border-l-red-500 border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-red-600 uppercase tracking-wide">
            C &mdash; Abandonner
          </p>
          <p className="text-3xl font-bold text-red-700 mt-2">{summary.cDrop}</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Source</label>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
            >
              <option value="">Toutes les sources</option>
              {SOURCES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Niche</label>
            <select
              value={niche}
              onChange={(e) => setNiche(e.target.value)}
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
            <label className="block text-xs font-medium text-gray-500 mb-1">Decision</label>
            <select
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
            >
              <option value="">Toutes les decisions</option>
              {DECISIONS.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Score minimum :{" "}
              <span className="font-bold text-gray-900">{localScore}</span>
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={localScore}
              onChange={(e) => setLocalScore(Number(e.target.value))}
              className="w-full h-2 mt-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>0</span>
              <span>50</span>
              <span>100</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm whitespace-nowrap">
            <thead>
              <tr className="bg-gray-50/80 border-b border-gray-200 text-xs uppercase tracking-wide text-gray-500">
                <th className="px-3 py-3 text-center w-10">
                  <input
                    type="checkbox"
                    checked={allChecked}
                    ref={(el) => {
                      if (el) el.indeterminate = someChecked;
                    }}
                    onChange={toggleSelectAll}
                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                  />
                </th>
                <th className="px-3 py-3 text-left font-medium">ASIN</th>
                <th className="px-3 py-3 text-left font-medium">Titre</th>
                <th className="px-3 py-3 text-left font-medium">Niche</th>
                <th
                  className="px-3 py-3 text-right font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("price")}
                >
                  Prix vente <SortArrow field="price" />
                </th>
                <th
                  className="px-3 py-3 text-right font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("cost_price")}
                >
                  Prix achat <SortArrow field="cost_price" />
                </th>
                <th
                  className="px-3 py-3 text-center font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("margin_pct")}
                >
                  Marge % <SortArrow field="margin_pct" />
                </th>
                <th
                  className="px-3 py-3 text-center font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("gross_roi")}
                >
                  ROI <SortArrow field="gross_roi" />
                </th>
                <th
                  className="px-3 py-3 text-right font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("monthly_sales")}
                >
                  Ventes/mois <SortArrow field="monthly_sales" />
                </th>
                <th
                  className="px-3 py-3 text-right font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("est_monthly_revenue")}
                >
                  CA mensuel <SortArrow field="est_monthly_revenue" />
                </th>
                <th
                  className="px-3 py-3 text-right font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("bsr")}
                >
                  BSR <SortArrow field="bsr" />
                </th>
                <th
                  className="px-3 py-3 text-center font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("score")}
                >
                  Score <SortArrow field="score" />
                </th>
                <th className="px-3 py-3 text-center font-medium">Concurrence</th>
                <th className="px-3 py-3 text-center font-medium">Demande</th>
                <th
                  className="px-3 py-3 text-center font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("decision")}
                >
                  Decision <SortArrow field="decision" />
                </th>
                <th
                  className="px-3 py-3 text-center font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("unlock_priority")}
                >
                  Priorite <SortArrow field="unlock_priority" />
                </th>
                <th className="px-3 py-3 text-center font-medium">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    {Array.from({ length: 16 }).map((_, j) => (
                      <td key={j} className="px-3 py-3">
                        <div className="h-4 bg-gray-100 rounded w-full" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : displayed.length === 0 ? (
                <tr>
                  <td colSpan={16} className="px-4 py-16 text-center text-gray-400">
                    Aucune opportunite trouvee avec ces criteres.
                  </td>
                </tr>
              ) : (
                displayed.map((o) => {
                  const isSelected = selected.has(o.id);
                  return (
                    <tr
                      key={o.id}
                      className={`transition-colors cursor-pointer ${
                        isSelected ? "bg-blue-50/60" : "hover:bg-blue-50/40"
                      }`}
                      onClick={() => toggleSelect(o.id)}
                    >
                      <td className="px-3 py-2.5 text-center" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(o.id)}
                          className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                        />
                      </td>
                      <td className="px-3 py-2.5">
                        <a
                          href={`https://www.amazon.fr/dp/${o.asin}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-mono text-xs text-blue-600 hover:text-blue-800 hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {o.asin}
                        </a>
                      </td>
                      <td className="px-3 py-2.5 max-w-[220px]">
                        <span className="block truncate text-gray-800" title={o.title}>
                          {o.title}
                        </span>
                      </td>
                      <td className="px-3 py-2.5">
                        {o.niche ? (
                          <span className="inline-block px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full text-xs font-medium">
                            {o.niche}
                          </span>
                        ) : (
                          <span className="text-gray-300">&mdash;</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        {(() => {
                          const mk = MARKETPLACE_FLAGS[o.marketplace];
                          return (
                            <span className="inline-flex items-center gap-1 font-semibold text-gray-900" title={mk?.label || o.marketplace}>
                              {mk && <span className="text-sm">{mk.flag}</span>}
                              {fmtPrice(o.price)}
                            </span>
                          );
                        })()}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        {o.cost_price > 0 ? (
                          (() => {
                            const sc = getSourceCountry(o.source_url);
                            return (
                              <span className="inline-flex items-center gap-1 font-semibold text-orange-700" title={sc?.label || "Source"}>
                                {sc && <span className="text-sm">{sc.flag}</span>}
                                {fmtPrice(o.cost_price)}
                              </span>
                            );
                          })()
                        ) : (
                          <span className="text-gray-300">&mdash;</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-lg text-xs font-bold tabular-nums ${
                            o.margin_pct >= 30
                              ? "bg-green-50 text-green-700"
                              : o.margin_pct >= 15
                                ? "bg-yellow-50 text-yellow-700"
                                : "bg-red-50 text-red-700"
                          }`}
                        >
                          {o.margin_pct.toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        {o.gross_roi != null ? (
                          <span
                            className={`inline-block px-2 py-0.5 rounded-lg text-xs font-bold tabular-nums ${
                              o.gross_roi >= 50
                                ? "bg-green-50 text-green-700"
                                : o.gross_roi >= 20
                                  ? "bg-yellow-50 text-yellow-700"
                                  : "bg-red-50 text-red-700"
                            }`}
                          >
                            {o.gross_roi.toFixed(0)}%
                          </span>
                        ) : (
                          <span className="text-gray-300">&mdash;</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        {o.monthly_sales != null ? (
                          <span
                            className="font-semibold text-gray-900 cursor-help"
                            title={`${(o.monthly_sales / 30).toFixed(1)} ventes/jour\n${(o.monthly_sales / 4.33).toFixed(1)} ventes/semaine\n${o.monthly_sales} ventes/mois`}
                          >
                            {fmtNum(o.monthly_sales)}
                            <span className="text-xs text-gray-400 ml-1">u.</span>
                          </span>
                        ) : (
                          <span className="text-gray-300">&mdash;</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        {o.est_monthly_revenue != null ? (
                          <span
                            className={`font-semibold cursor-help ${
                              o.est_monthly_revenue >= 3000
                                ? "text-green-700"
                                : o.est_monthly_revenue >= 1000
                                  ? "text-yellow-700"
                                  : "text-gray-600"
                            }`}
                            title={`${fmtPrice(o.est_monthly_revenue / 30)} CA/jour\n${fmtPrice(o.est_monthly_revenue / 4.33)} CA/semaine\n${fmtPrice(o.est_monthly_revenue)} CA/mois`}
                          >
                            {fmtPrice(o.est_monthly_revenue)}
                          </span>
                        ) : (
                          <span className="text-gray-300">&mdash;</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        {o.bsr != null ? (
                          <span
                            className={`font-mono text-xs tabular-nums ${
                              o.bsr <= 20000
                                ? "text-green-700 font-semibold"
                                : o.bsr <= 100000
                                  ? "text-yellow-700"
                                  : "text-gray-500"
                            }`}
                            title={`BSR (Best Sellers Rank): #${fmtNum(o.bsr)}\nPlus le BSR est bas, plus le produit se vend`}
                          >
                            #{fmtNum(o.bsr)}
                          </span>
                        ) : (
                          <span className="text-gray-300">&mdash;</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <ScoreCell score={o.score} />
                      </td>
                      <td className="px-3 py-2.5">
                        <ScoreBar value={o.competition_score} label="Concurrence" />
                      </td>
                      <td className="px-3 py-2.5">
                        <ScoreBar value={o.demand_score} label="Demande" />
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <DecisionBadge decision={o.decision} />
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        {o.unlock_priority != null ? (
                          <span
                            className={`inline-block px-2 py-0.5 rounded-lg text-xs font-bold tabular-nums ${
                              o.unlock_priority >= 70
                                ? "bg-green-50 text-green-700"
                                : o.unlock_priority >= 40
                                  ? "bg-yellow-50 text-yellow-700"
                                  : "bg-gray-100 text-gray-500"
                            }`}
                            title={`Priorite de deblocage : ${o.unlock_priority.toFixed(1)}/100\nBasee sur: profit mensuel, volume, marge, score`}
                          >
                            {o.unlock_priority.toFixed(0)}
                          </span>
                        ) : (
                          <span className="text-gray-300">&mdash;</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        {(() => {
                          const SOURCE_BADGES: Record<string, { label: string; cls: string }> = {
                            octopia: { label: "OCTOPIA", cls: "bg-purple-50 text-purple-700" },
                            tactical_arbitrage: { label: "TA", cls: "bg-orange-50 text-orange-700" },
                            helium10_blackbox: { label: "H10", cls: "bg-blue-50 text-blue-700" },
                            amazon_search: { label: "AMZ", cls: "bg-gray-100 text-gray-600" },
                          };
                          const badge = SOURCE_BADGES[o.source];
                          if (o.source_url) {
                            return (
                              <a
                                href={o.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium hover:opacity-80 transition ${badge?.cls || "bg-gray-100 text-gray-600"}`}
                                onClick={(e) => e.stopPropagation()}
                              >
                                {badge?.label || o.source}
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                              </a>
                            );
                          }
                          return (
                            <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${badge?.cls || "bg-gray-100 text-gray-600"}`}>
                              {badge?.label || o.source || "\u2014"}
                            </span>
                          );
                        })()}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {!loading && sorted.length > 0 && (
        <div className="flex items-center justify-between bg-white rounded-xl border border-gray-200 px-5 py-3 shadow-sm">
          <p className="text-sm text-gray-500">
            {page * PAGE_SIZE + 1}&ndash;
            {Math.min((page + 1) * PAGE_SIZE, sorted.length)} sur {sorted.length} opportunites
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => p - 1)}
              disabled={page === 0}
              className="px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-200 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              &larr; Precedent
            </button>
            <span className="text-sm font-medium text-gray-700 px-3">
              Page {page + 1} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= totalPages - 1}
              className="px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-200 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              Suivant &rarr;
            </button>
          </div>
        </div>
      )}

      <ActionBar count={selected.size} onClear={() => setSelected(new Set())}>
        <select
          value={strategy}
          onChange={(e) => setStrategy(e.target.value)}
          className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none"
        >
          <option value="clone_best">Clone (SP-API)</option>
          <option value="ai_optimize">IA (OpenAI)</option>
        </select>
        <select
          value={fulfillmentMode}
          onChange={(e) => setFulfillmentMode(e.target.value)}
          className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none"
        >
          <option value="FBM">FBM (expedition directe)</option>
          <option value="FBA">FBA (stock Amazon)</option>
        </select>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="px-5 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-60 disabled:cursor-wait transition shadow-sm"
        >
          {generating ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Generation...
            </span>
          ) : (
            `Generer ${selected.size} listing${selected.size > 1 ? "s" : ""}`
          )}
        </button>
      </ActionBar>
    </div>
  );
}
