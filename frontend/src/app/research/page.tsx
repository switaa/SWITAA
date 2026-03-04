"use client";

import { useEffect, useState, useCallback } from "react";
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
  created_at: string;
  completed_at: string | null;
  error_message: string;
}

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  running: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  error: "bg-red-100 text-red-700",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "En attente",
  running: "En cours",
  completed: "Terminee",
  error: "Erreur",
};

export default function ResearchPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("");

  const fetchCampaigns = useCallback(async () => {
    try {
      const params = statusFilter ? `?status=${statusFilter}` : "";
      const data = await api.get<Campaign[]>(`/api/v1/campaigns/${params}`);
      setCampaigns(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchCampaigns();
    const interval = setInterval(fetchCampaigns, 5000);
    return () => clearInterval(interval);
  }, [fetchCampaigns]);

  const handleQuickStart = async () => {
    if (!confirm("Lancer les 8 sous-niches ? Cela va demarrer 8 campagnes de recherche en parallele.")) return;
    setLaunching(true);
    try {
      await api.post("/api/v1/campaigns/quick-start/");
      await fetchCampaigns();
    } catch (e) {
      alert(`Erreur: ${e}`);
    } finally {
      setLaunching(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Supprimer cette campagne ?")) return;
    try {
      await api.delete(`/api/v1/campaigns/${id}`);
      await fetchCampaigns();
    } catch (e) {
      alert(`Erreur: ${e}`);
    }
  };

  const handleRun = async (id: string) => {
    try {
      await api.post(`/api/v1/campaigns/${id}/run`);
      await fetchCampaigns();
    } catch (e) {
      alert(`Erreur: ${e}`);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Recherche de produits</h1>
          <p className="text-gray-500 mt-1">Campagnes de recherche automatisee - 400 references</p>
        </div>
        <button
          onClick={handleQuickStart}
          disabled={launching}
          className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition"
        >
          {launching ? "Lancement..." : "Quick Start 8 niches"}
        </button>
      </div>

      <div className="flex gap-2 mb-6">
        {["", "pending", "running", "completed", "error"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 text-sm rounded-lg transition ${
              statusFilter === s
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
            }`}
          >
            {s === "" ? "Toutes" : STATUS_LABELS[s] || s}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Chargement...</div>
      ) : campaigns.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <p className="text-gray-500 text-lg">Aucune campagne</p>
          <p className="text-gray-400 mt-2">
            Cliquez sur &quot;Quick Start 8 niches&quot; pour lancer la recherche automatisee
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {campaigns.map((c) => (
            <div key={c.id} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-sm transition">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <Link
                      href={`/research/${c.id}`}
                      className="text-lg font-semibold text-gray-900 hover:text-blue-600 transition"
                    >
                      {c.name}
                    </Link>
                    <span className={`px-2.5 py-0.5 text-xs font-medium rounded-full ${STATUS_STYLES[c.status] || "bg-gray-100 text-gray-600"}`}>
                      {STATUS_LABELS[c.status] || c.status}
                    </span>
                  </div>
                  <div className="flex gap-4 text-sm text-gray-500">
                    <span>Niche: <strong className="text-gray-700">{c.niche}</strong></span>
                    {c.sub_niche && <span>Sous-niche: <strong className="text-gray-700">{c.sub_niche}</strong></span>}
                    <span>Marketplace: {c.marketplace}</span>
                    <span>Trouve: <strong className="text-gray-700">{c.found_count}</strong> / {c.target_count}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  {c.status === "pending" && (
                    <button
                      onClick={() => handleRun(c.id)}
                      className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
                    >
                      Lancer
                    </button>
                  )}
                  {c.status === "error" && (
                    <button
                      onClick={() => handleRun(c.id)}
                      className="px-3 py-1.5 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition"
                    >
                      Relancer
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(c.id)}
                    className="px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition"
                  >
                    Suppr.
                  </button>
                </div>
              </div>

              {c.status === "running" && (
                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm text-gray-500 mb-1">
                    <span>Phase: {c.phase}</span>
                    <span>{c.progress_pct}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 rounded-full h-2 transition-all duration-500"
                      style={{ width: `${c.progress_pct}%` }}
                    />
                  </div>
                </div>
              )}

              {c.error_message && (
                <div className="mt-3 p-3 bg-red-50 border border-red-100 rounded-lg text-sm text-red-700">
                  {c.error_message}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
