"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/components/toast";
import StatusBadge from "@/components/status-badge";

interface Account {
  id: string;
  platform: string;
  seller_id: string;
  is_active: boolean;
}

interface PushLog {
  id: string;
  listing_id: string;
  marketplace_account_id: string;
  status: string;
  error_message: string;
  pushed_at: string | null;
}

const PLATFORMS = [
  { value: "amazon_fr", label: "Amazon France" },
  { value: "amazon_de", label: "Amazon Allemagne" },
  { value: "amazon_es", label: "Amazon Espagne" },
  { value: "amazon_it", label: "Amazon Italie" },
  { value: "cdiscount", label: "CDiscount" },
  { value: "fnac", label: "Fnac" },
  { value: "manomano", label: "ManoMano" },
  { value: "rdc", label: "Rue du Commerce" },
];

const LOG_STATUSES = [
  { value: "", label: "Tous les statuts" },
  { value: "pending", label: "En attente" },
  { value: "success", label: "Succes" },
  { value: "error", label: "Erreur" },
];

const fmtDate = (d: string | null) => {
  if (!d) return "\u2014";
  return new Date(d).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export default function MarketplacePage() {
  const { toast } = useToast();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [pushLogs, setPushLogs] = useState<PushLog[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(true);
  const [logStatus, setLogStatus] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [formPlatform, setFormPlatform] = useState("amazon_fr");
  const [formSellerId, setFormSellerId] = useState("");
  const [creating, setCreating] = useState(false);

  const fetchAccounts = useCallback(() => {
    api.get<Account[]>("/api/v1/marketplace/accounts").then(setAccounts).catch(() => {});
  }, []);

  const fetchLogs = useCallback(() => {
    setLoadingLogs(true);
    const params = new URLSearchParams();
    params.set("limit", "100");
    if (logStatus) params.set("status", logStatus);
    api
      .get<PushLog[]>(`/api/v1/marketplace/push-logs?${params}`)
      .then(setPushLogs)
      .catch(() => setPushLogs([]))
      .finally(() => setLoadingLogs(false));
  }, [logStatus]);

  useEffect(() => {
    fetchAccounts();
    fetchLogs();
  }, [fetchAccounts, fetchLogs]);

  const handleToggle = async (accountId: string) => {
    try {
      await api.put(`/api/v1/marketplace/accounts/${accountId}/toggle`);
      fetchAccounts();
    } catch {
      toast("Erreur de mise a jour", "error");
    }
  };

  const handleCreate = async () => {
    if (!formPlatform) return;
    setCreating(true);
    try {
      await api.post("/api/v1/marketplace/accounts", {
        platform: formPlatform,
        seller_id: formSellerId,
      });
      toast("Compte marketplace cree", "success");
      setShowForm(false);
      setFormPlatform("amazon_fr");
      setFormSellerId("");
      fetchAccounts();
    } catch {
      toast("Erreur de creation", "error");
    } finally {
      setCreating(false);
    }
  };

  const logCounts = {
    total: pushLogs.length,
    success: pushLogs.filter((l) => l.status === "success").length,
    error: pushLogs.filter((l) => l.status === "error").length,
    pending: pushLogs.filter((l) => l.status === "pending").length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Marketplace</h1>
          <p className="text-sm text-gray-500 mt-1">Comptes de vente et historique des publications</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition shadow-sm"
        >
          {showForm ? "Annuler" : "+ Ajouter un compte"}
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Nouveau compte marketplace</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Plateforme</label>
              <select
                value={formPlatform}
                onChange={(e) => setFormPlatform(e.target.value)}
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none"
              >
                {PLATFORMS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Seller ID</label>
              <input
                type="text"
                value={formSellerId}
                onChange={(e) => setFormSellerId(e.target.value)}
                placeholder="Ex: A1B2C3D4E5F6G7"
                className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleCreate}
                disabled={creating}
                className="w-full px-4 py-2 bg-green-600 text-white text-sm font-semibold rounded-lg hover:bg-green-700 disabled:opacity-60 transition"
              >
                {creating ? "Creation..." : "Creer le compte"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Accounts */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {accounts.map((a) => {
          const platformLabel = PLATFORMS.find((p) => p.value === a.platform)?.label || a.platform;
          return (
            <div
              key={a.id}
              className={`bg-white rounded-xl shadow-sm border p-5 transition ${
                a.is_active ? "border-green-200" : "border-gray-200 opacity-70"
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">{platformLabel}</h3>
                  <p className="text-xs text-gray-500 mt-1">
                    Seller ID: {a.seller_id || "Non configure"}
                  </p>
                </div>
                <button
                  onClick={() => handleToggle(a.id)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    a.is_active ? "bg-green-500" : "bg-gray-300"
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                      a.is_active ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>
              <div className="mt-3">
                <span
                  className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                    a.is_active
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-500"
                  }`}
                >
                  {a.is_active ? "Actif" : "Inactif"}
                </span>
              </div>
            </div>
          );
        })}
        {accounts.length === 0 && !showForm && (
          <div className="col-span-full bg-white rounded-xl border border-dashed border-gray-300 p-8 text-center">
            <p className="text-gray-400 mb-3">Aucun compte marketplace configure</p>
            <button
              onClick={() => setShowForm(true)}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-blue-200 text-blue-600 hover:bg-blue-50 transition"
            >
              Ajouter votre premier compte
            </button>
          </div>
        )}
      </div>

      {/* Push logs */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-gray-900">Historique des publications</h2>
          <div className="flex items-center gap-3">
            <div className="flex gap-2 text-xs">
              <span className="px-2 py-1 bg-green-50 text-green-700 rounded-md font-medium">
                {logCounts.success} succes
              </span>
              <span className="px-2 py-1 bg-red-50 text-red-700 rounded-md font-medium">
                {logCounts.error} erreur{logCounts.error > 1 ? "s" : ""}
              </span>
              <span className="px-2 py-1 bg-yellow-50 text-yellow-700 rounded-md font-medium">
                {logCounts.pending} en attente
              </span>
            </div>
            <select
              value={logStatus}
              onChange={(e) => setLogStatus(e.target.value)}
              className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none"
            >
              {LOG_STATUSES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50/80 border-b border-gray-200 text-xs uppercase tracking-wide text-gray-500">
                <th className="px-4 py-3 text-left font-medium">Listing ID</th>
                <th className="px-4 py-3 text-center font-medium">Statut</th>
                <th className="px-4 py-3 text-left font-medium">Message</th>
                <th className="px-4 py-3 text-right font-medium">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loadingLogs ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    {Array.from({ length: 4 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 bg-gray-100 rounded w-full" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : pushLogs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-12 text-center text-gray-400">
                    Aucune publication enregistree.
                  </td>
                </tr>
              ) : (
                pushLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-gray-600">
                        {log.listing_id.slice(0, 8)}...
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <StatusBadge value={log.status} />
                    </td>
                    <td className="px-4 py-3 max-w-[300px]">
                      {log.error_message ? (
                        <span className="text-xs text-red-600 block truncate" title={log.error_message}>
                          {log.error_message}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">&mdash;</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-gray-500">
                      {fmtDate(log.pushed_at)}
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
