"use client";

import { useEffect, useState, useMemo } from "react";
import { api } from "@/lib/api";

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
}

type SortField = "score" | "price" | "decision";
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

const DECISIONS = [
  { value: "A_launch", label: "A — Lancer" },
  { value: "B_review", label: "B — À revoir" },
  { value: "C_drop", label: "C — Abandonner" },
];

const PAGE_SIZE = 50;

const fmtPrice = (n: number) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(n);

const DECISION_STYLES: Record<string, string> = {
  A_launch: "bg-green-100 text-green-700 border-green-200",
  B_review: "bg-yellow-100 text-yellow-700 border-yellow-200",
  C_drop: "bg-red-100 text-red-700 border-red-200",
};

const DECISION_LABELS: Record<string, string> = {
  A_launch: "Lancer",
  B_review: "À revoir",
  C_drop: "Abandonner",
};

function ScoreBar({ value, label }: { value: number; label: string }) {
  const pct = Math.min(100, Math.max(0, value));
  const color =
    pct >= 70 ? "bg-green-400" : pct >= 40 ? "bg-amber-400" : "bg-red-400";
  return (
    <div
      className="flex items-center gap-1.5"
      title={`${label}: ${value.toFixed(1)}`}
    >
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
  const [allData, setAllData] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);

  const [niche, setNiche] = useState("");
  const [decision, setDecision] = useState("");
  const [localScore, setLocalScore] = useState(0);
  const [minScore, setMinScore] = useState(0);

  const [sortField, setSortField] = useState<SortField>("score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(0);

  // Debounce slider value (300ms)
  useEffect(() => {
    const timer = setTimeout(() => setMinScore(localScore), 300);
    return () => clearTimeout(timer);
  }, [localScore]);

  // Fetch opportunities when filters change
  useEffect(() => {
    setLoading(true);
    setPage(0);
    const params = new URLSearchParams();
    params.set("limit", "200");
    if (minScore > 0) params.set("min_score", String(minScore));
    if (decision) params.set("decision", decision);
    if (niche) params.set("niche", niche);

    api
      .get<Opportunity[]>(`/api/v1/scoring/opportunities?${params}`)
      .then(setAllData)
      .catch(() => setAllData([]))
      .finally(() => setLoading(false));
  }, [minScore, decision, niche]);

  // Summary cards
  const summary = useMemo(
    () => ({
      total: allData.length,
      aLaunch: allData.filter((o) => o.decision === "A_launch").length,
      bReview: allData.filter((o) => o.decision === "B_review").length,
      cDrop: allData.filter((o) => o.decision === "C_drop").length,
    }),
    [allData]
  );

  // Sort client-side
  const sorted = useMemo(() => {
    const arr = [...allData];
    const dir = sortDir === "asc" ? 1 : -1;
    arr.sort((a, b) => {
      if (sortField === "score") return (a.score - b.score) * dir;
      if (sortField === "price") return (a.price - b.price) * dir;
      if (sortField === "decision")
        return a.decision.localeCompare(b.decision) * dir;
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

  const SortArrow = ({ field }: { field: SortField }) =>
    sortField === field ? (
      <span className="ml-1 text-blue-600">
        {sortDir === "asc" ? "↑" : "↓"}
      </span>
    ) : (
      <span className="ml-1 text-gray-300">↕</span>
    );

  return (
    <div className="space-y-5">
      {/* ── Header ── */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Opportunités</h1>
        <p className="text-sm text-gray-500 mt-1">
          Produits analysés et scorés par l&#39;algorithme
        </p>
      </div>

      {/* ── Summary Cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Total
          </p>
          <p className="text-3xl font-bold text-gray-900 mt-2">
            {summary.total}
          </p>
        </div>
        <div className="bg-white rounded-xl border-l-4 border-l-green-500 border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-green-600 uppercase tracking-wide">
            A — Lancer
          </p>
          <p className="text-3xl font-bold text-green-700 mt-2">
            {summary.aLaunch}
          </p>
        </div>
        <div className="bg-white rounded-xl border-l-4 border-l-yellow-500 border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-yellow-600 uppercase tracking-wide">
            B — À revoir
          </p>
          <p className="text-3xl font-bold text-yellow-700 mt-2">
            {summary.bReview}
          </p>
        </div>
        <div className="bg-white rounded-xl border-l-4 border-l-red-500 border border-gray-200 p-5 shadow-sm">
          <p className="text-xs font-medium text-red-600 uppercase tracking-wide">
            C — Abandonner
          </p>
          <p className="text-3xl font-bold text-red-700 mt-2">
            {summary.cDrop}
          </p>
        </div>
      </div>

      {/* ── Filters ── */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Niche
            </label>
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
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Décision
            </label>
            <select
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
            >
              <option value="">Toutes les décisions</option>
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

      {/* ── Table ── */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm whitespace-nowrap">
            <thead>
              <tr className="bg-gray-50/80 border-b border-gray-200 text-xs uppercase tracking-wide text-gray-500">
                <th className="px-3 py-3 text-left font-medium">ASIN</th>
                <th className="px-3 py-3 text-left font-medium">Titre</th>
                <th className="px-3 py-3 text-left font-medium">Niche</th>
                <th
                  className="px-3 py-3 text-right font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("price")}
                >
                  Prix <SortArrow field="price" />
                </th>
                <th
                  className="px-3 py-3 text-center font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("score")}
                >
                  Score <SortArrow field="score" />
                </th>
                <th className="px-3 py-3 text-center font-medium">Marge</th>
                <th className="px-3 py-3 text-center font-medium">
                  Concurrence
                </th>
                <th className="px-3 py-3 text-center font-medium">Demande</th>
                <th className="px-3 py-3 text-center font-medium">BSR</th>
                <th
                  className="px-3 py-3 text-center font-medium cursor-pointer select-none hover:text-blue-600 transition-colors"
                  onClick={() => handleSort("decision")}
                >
                  Décision <SortArrow field="decision" />
                </th>
                <th className="px-3 py-3 text-right font-medium">Vendeurs</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    {Array.from({ length: 11 }).map((_, j) => (
                      <td key={j} className="px-3 py-3">
                        <div className="h-4 bg-gray-100 rounded w-full" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : displayed.length === 0 ? (
                <tr>
                  <td
                    colSpan={11}
                    className="px-4 py-16 text-center text-gray-400"
                  >
                    Aucune opportunité trouvée avec ces critères.
                  </td>
                </tr>
              ) : (
                displayed.map((o) => (
                  <tr
                    key={o.id}
                    className="hover:bg-blue-50/40 transition-colors"
                  >
                    {/* ASIN */}
                    <td className="px-3 py-2.5">
                      <a
                        href={`https://www.amazon.fr/dp/${o.asin}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-xs text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {o.asin}
                      </a>
                    </td>

                    {/* Title */}
                    <td className="px-3 py-2.5 max-w-[220px]">
                      <span
                        className="block truncate text-gray-800"
                        title={o.title}
                      >
                        {o.title}
                      </span>
                    </td>

                    {/* Niche */}
                    <td className="px-3 py-2.5">
                      {o.niche ? (
                        <span className="inline-block px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded-full text-xs font-medium">
                          {o.niche}
                        </span>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>

                    {/* Price */}
                    <td className="px-3 py-2.5 text-right font-semibold text-gray-900">
                      {fmtPrice(o.price)}
                    </td>

                    {/* Score */}
                    <td className="px-3 py-2.5 text-center">
                      <ScoreCell score={o.score} />
                    </td>

                    {/* Sub-scores */}
                    <td className="px-3 py-2.5">
                      <ScoreBar value={o.margin_score} label="Marge" />
                    </td>
                    <td className="px-3 py-2.5">
                      <ScoreBar
                        value={o.competition_score}
                        label="Concurrence"
                      />
                    </td>
                    <td className="px-3 py-2.5">
                      <ScoreBar value={o.demand_score} label="Demande" />
                    </td>
                    <td className="px-3 py-2.5">
                      <ScoreBar value={o.bsr_score} label="BSR" />
                    </td>

                    {/* Decision */}
                    <td className="px-3 py-2.5 text-center">
                      <DecisionBadge decision={o.decision} />
                    </td>

                    {/* Sellers */}
                    <td className="px-3 py-2.5 text-right text-gray-600">
                      {o.seller_count ?? "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Pagination ── */}
      {!loading && sorted.length > 0 && (
        <div className="flex items-center justify-between bg-white rounded-xl border border-gray-200 px-5 py-3 shadow-sm">
          <p className="text-sm text-gray-500">
            {page * PAGE_SIZE + 1}–
            {Math.min((page + 1) * PAGE_SIZE, sorted.length)} sur{" "}
            {sorted.length} opportunités
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
              Page {page + 1} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= totalPages - 1}
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
