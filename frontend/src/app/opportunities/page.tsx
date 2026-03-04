"use client";

import { useEffect, useState } from "react";
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
}

const DECISION_COLORS: Record<string, string> = {
  A_launch: "bg-green-100 text-green-700",
  B_review: "bg-yellow-100 text-yellow-700",
  C_drop: "bg-red-100 text-red-700",
};

export default function OpportunitiesPage() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [minScore, setMinScore] = useState(0);

  useEffect(() => {
    api
      .get<Opportunity[]>(`/api/v1/scoring/opportunities?min_score=${minScore}`)
      .then(setOpportunities)
      .catch(console.error);
  }, [minScore]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Opportunités</h2>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-500">Score min:</label>
          <input
            type="range"
            min={0}
            max={100}
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="w-32"
          />
          <span className="text-sm font-medium w-8">{minScore}</span>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">ASIN</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Titre</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Prix</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Coût</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Marge %</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Score</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">Décision</th>
            </tr>
          </thead>
          <tbody>
            {opportunities.map((o) => (
              <tr key={o.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-blue-600">{o.asin}</td>
                <td className="px-4 py-3 max-w-xs truncate">{o.title}</td>
                <td className="px-4 py-3 text-right">{o.price.toFixed(2)} €</td>
                <td className="px-4 py-3 text-right">{o.cost_price.toFixed(2)} €</td>
                <td className="px-4 py-3 text-right font-medium">{o.margin_pct.toFixed(1)}%</td>
                <td className="px-4 py-3 text-right font-bold">{o.score.toFixed(1)}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${DECISION_COLORS[o.decision] || ""}`}>
                    {o.decision}
                  </span>
                </td>
              </tr>
            ))}
            {opportunities.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  Aucune opportunité trouvée.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
