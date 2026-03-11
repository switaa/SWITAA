"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/components/toast";
import StatusBadge from "@/components/status-badge";
import ActionBar from "@/components/action-bar";

interface ListingItem {
  id: string;
  product_id: string;
  marketplace: string;
  title: string;
  bullets: string[] | null;
  description: string;
  search_terms: string;
  brand_name: string;
  strategy: string;
  status: string;
  sku: string;
  marketplace_status: string;
  fulfillment_channel: string;
  created_at: string | null;
  asin: string | null;
  price: number | null;
  image_url: string | null;
}

interface Account {
  id: string;
  platform: string;
  seller_id: string;
  is_active: boolean;
}

const STATUSES = [
  { value: "", label: "Tous" },
  { value: "draft", label: "Brouillon" },
  { value: "auto_generated", label: "Genere" },
  { value: "approved", label: "Approuve" },
  { value: "published", label: "Publie" },
];

const fmtPrice = (n: number) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(n);

const fmtDate = (d: string | null) => {
  if (!d) return "\u2014";
  return new Date(d).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

const PIPELINE_STEPS = ["draft", "auto_generated", "approved", "published"];
const PIPELINE_LABELS: Record<string, string> = {
  draft: "Brouillon",
  auto_generated: "Genere",
  approved: "Approuve",
  published: "Publie",
};

function PipelineIndicator({ status }: { status: string }) {
  const idx = PIPELINE_STEPS.indexOf(status);
  return (
    <div className="flex items-center gap-0.5">
      {PIPELINE_STEPS.map((step, i) => {
        const active = i <= idx;
        const isCurrent = step === status;
        return (
          <div key={step} className="flex items-center gap-0.5" title={PIPELINE_LABELS[step]}>
            <div
              className={`w-2.5 h-2.5 rounded-full transition ${
                active
                  ? isCurrent
                    ? "bg-blue-600 ring-2 ring-blue-200"
                    : "bg-blue-400"
                  : "bg-gray-200"
              }`}
            />
            {i < PIPELINE_STEPS.length - 1 && (
              <div className={`w-3 h-0.5 ${active ? "bg-blue-400" : "bg-gray-200"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function ListingsPage() {
  const { toast } = useToast();
  const [listings, setListings] = useState<ListingItem[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<ListingItem>>({});
  const [saving, setSaving] = useState(false);
  const [pushAccountId, setPushAccountId] = useState("");
  const [pushing, setPushing] = useState(false);
  const [approving, setApproving] = useState(false);

  const fetchListings = useCallback(() => {
    setLoading(true);
    const params = new URLSearchParams();
    params.set("limit", "200");
    if (statusFilter) params.set("status", statusFilter);
    api
      .get<ListingItem[]>(`/api/v1/listings/?${params}`)
      .then((data) => {
        setListings(data);
        setSelected(new Set());
      })
      .catch(() => setListings([]))
      .finally(() => setLoading(false));
  }, [statusFilter]);

  useEffect(() => {
    fetchListings();
    api.get<Account[]>("/api/v1/marketplace/accounts").then(setAccounts).catch(() => {});
  }, [fetchListings]);

  const filtered = useMemo(() => {
    if (!search) return listings;
    const q = search.toLowerCase();
    return listings.filter(
      (l) =>
        l.title.toLowerCase().includes(q) ||
        (l.asin && l.asin.toLowerCase().includes(q)) ||
        (l.sku && l.sku.toLowerCase().includes(q)),
    );
  }, [listings, search]);

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { draft: 0, auto_generated: 0, approved: 0, published: 0 };
    listings.forEach((l) => {
      if (counts[l.status] !== undefined) counts[l.status]++;
    });
    return counts;
  }, [listings]);

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === filtered.length) setSelected(new Set());
    else setSelected(new Set(filtered.map((l) => l.id)));
  };

  const openEdit = (listing: ListingItem) => {
    setEditingId(listing.id);
    setEditForm({
      title: listing.title,
      bullets: listing.bullets || ["", "", "", "", ""],
      description: listing.description,
      search_terms: listing.search_terms,
      brand_name: listing.brand_name,
    });
  };

  const handleSave = async () => {
    if (!editingId) return;
    setSaving(true);
    const listing = listings.find((l) => l.id === editingId);
    if (!listing) return;
    try {
      await api.put(`/api/v1/listings/${editingId}`, {
        product_id: listing.product_id,
        marketplace: listing.marketplace,
        title: editForm.title || "",
        bullets: editForm.bullets,
        description: editForm.description || "",
        search_terms: editForm.search_terms || "",
        brand_name: editForm.brand_name || "",
        strategy: listing.strategy,
        fulfillment_channel: listing.fulfillment_channel,
      });
      toast("Listing sauvegarde", "success");
      setEditingId(null);
      fetchListings();
    } catch {
      toast("Erreur de sauvegarde", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await api.post(`/api/v1/listings/${id}/approve`);
      toast("Listing approuve", "success");
      fetchListings();
    } catch {
      toast("Erreur d'approbation", "error");
    }
  };

  const handleApproveBatch = async () => {
    setApproving(true);
    try {
      const ids = Array.from(selected);
      await api.post("/api/v1/listings/approve-batch", ids);
      toast(`${ids.length} listing${ids.length > 1 ? "s" : ""} approuve${ids.length > 1 ? "s" : ""}`, "success");
      setSelected(new Set());
      fetchListings();
    } catch {
      toast("Erreur d'approbation batch", "error");
    } finally {
      setApproving(false);
    }
  };

  const handlePush = async (listingId: string) => {
    const account = accounts.find((a) => a.is_active);
    if (!account) {
      toast("Aucun compte marketplace actif", "error");
      return;
    }
    try {
      await api.post("/api/v1/marketplace/push", {
        listing_id: listingId,
        marketplace_account_id: account.id,
      });
      toast("Listing pousse vers Amazon", "success");
      fetchListings();
    } catch {
      toast("Erreur de push", "error");
    }
  };

  const handlePushBatch = async () => {
    if (!pushAccountId) {
      toast("Selectionnez un compte marketplace", "error");
      return;
    }
    setPushing(true);
    try {
      const ids = Array.from(selected);
      const res = await api.post<{ total: number; queued: number; skipped: number; errors: number }>(
        "/api/v1/marketplace/push-batch",
        { listing_ids: ids, marketplace_account_id: pushAccountId },
      );
      toast(
        `${res.queued} listing${res.queued > 1 ? "s" : ""} pousse${res.queued > 1 ? "s" : ""}${res.errors > 0 ? `, ${res.errors} erreur${res.errors > 1 ? "s" : ""}` : ""}`,
        res.errors > 0 ? "error" : "success",
      );
      setSelected(new Set());
      fetchListings();
    } catch {
      toast("Erreur de push batch", "error");
    } finally {
      setPushing(false);
    }
  };

  const allChecked = filtered.length > 0 && selected.size === filtered.length;
  const someChecked = selected.size > 0 && selected.size < filtered.length;
  const activeAccounts = accounts.filter((a) => a.is_active);

  return (
    <div className="space-y-5 pb-20">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Listings</h1>
        <p className="text-sm text-gray-500 mt-1">
          Gerez vos listings Amazon avant publication
        </p>
      </div>

      {/* Status counters */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {STATUSES.filter((s) => s.value).map((s) => (
          <button
            key={s.value}
            onClick={() => setStatusFilter(statusFilter === s.value ? "" : s.value)}
            className={`bg-white rounded-xl border p-4 shadow-sm text-left transition hover:shadow-md ${
              statusFilter === s.value ? "border-blue-400 ring-2 ring-blue-100" : "border-gray-200"
            }`}
          >
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{s.label}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{statusCounts[s.value] || 0}</p>
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="flex gap-4">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Rechercher par titre, ASIN ou SKU..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-4 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none"
          >
            {STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
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
                <th className="px-3 py-3 text-left font-medium">Produit</th>
                <th className="px-3 py-3 text-left font-medium">Titre listing</th>
                <th className="px-3 py-3 text-center font-medium">Mode</th>
                <th className="px-3 py-3 text-center font-medium">Strategie</th>
                <th className="px-3 py-3 text-center font-medium">Pipeline</th>
                <th className="px-3 py-3 text-center font-medium">Marketplace</th>
                <th className="px-3 py-3 text-right font-medium">Prix</th>
                <th className="px-3 py-3 text-center font-medium">Date</th>
                <th className="px-3 py-3 text-center font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    {Array.from({ length: 10 }).map((_, j) => (
                      <td key={j} className="px-3 py-3">
                        <div className="h-4 bg-gray-100 rounded w-full" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-4 py-16 text-center text-gray-400">
                    Aucun listing{statusFilter ? ` avec statut "${statusFilter}"` : ""}.
                  </td>
                </tr>
              ) : (
                filtered.map((l) => {
                  const isSelected = selected.has(l.id);
                  return (
                    <tr
                      key={l.id}
                      className={`transition-colors ${isSelected ? "bg-blue-50/60" : "hover:bg-gray-50"}`}
                    >
                      <td className="px-3 py-2.5 text-center">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(l.id)}
                          className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                        />
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          {l.image_url && (
                            <img
                              src={l.image_url}
                              alt=""
                              className="w-8 h-8 rounded object-cover bg-gray-100"
                            />
                          )}
                          <div>
                            {l.asin ? (
                              <a
                                href={`https://www.amazon.fr/dp/${l.asin}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-mono text-xs text-blue-600 hover:underline"
                              >
                                {l.asin}
                              </a>
                            ) : (
                              <span className="text-xs text-gray-400">N/A</span>
                            )}
                            {l.sku && (
                              <p className="text-[10px] text-gray-400 mt-0.5">{l.sku}</p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 max-w-[250px]">
                        <span className="block truncate text-gray-800" title={l.title}>
                          {l.title}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <StatusBadge value={l.fulfillment_channel} />
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <StatusBadge value={l.strategy} />
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <PipelineIndicator status={l.status} />
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <StatusBadge value={l.marketplace_status} />
                      </td>
                      <td className="px-3 py-2.5 text-right font-semibold text-gray-900">
                        {l.price != null ? fmtPrice(l.price) : "\u2014"}
                      </td>
                      <td className="px-3 py-2.5 text-center text-xs text-gray-500">
                        {fmtDate(l.created_at)}
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <button
                            onClick={() => openEdit(l)}
                            className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition"
                            title="Editer"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          {l.status !== "approved" && l.status !== "published" && (
                            <button
                              onClick={() => handleApprove(l.id)}
                              className="p-1.5 rounded hover:bg-green-50 text-gray-500 hover:text-green-600 transition"
                              title="Approuver"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            </button>
                          )}
                          {(l.status === "approved" || l.status === "auto_generated") && l.marketplace_status !== "live" && (
                            <button
                              onClick={() => handlePush(l.id)}
                              className="p-1.5 rounded hover:bg-blue-50 text-gray-500 hover:text-blue-600 transition"
                              title="Pousser"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit modal */}
      {editingId && (
        <div className="fixed inset-0 z-50 flex items-center justify-end">
          <div className="absolute inset-0 bg-black/30" onClick={() => setEditingId(null)} />
          <div className="relative w-full max-w-lg h-full bg-white shadow-xl overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
              <h2 className="text-lg font-bold text-gray-900">Editer le listing</h2>
              <button
                onClick={() => setEditingId(null)}
                className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-5">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Titre</label>
                <input
                  type="text"
                  value={editForm.title || ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, title: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Bullet Points</label>
                <div className="space-y-2">
                  {(editForm.bullets || ["", "", "", "", ""]).map((b, i) => (
                    <textarea
                      key={i}
                      value={b}
                      onChange={(e) => {
                        const newBullets = [...(editForm.bullets || ["", "", "", "", ""])];
                        newBullets[i] = e.target.value;
                        setEditForm((f) => ({ ...f, bullets: newBullets }));
                      }}
                      rows={2}
                      placeholder={`Bullet point ${i + 1}`}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                    />
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Description</label>
                <textarea
                  value={editForm.description || ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, description: e.target.value }))}
                  rows={5}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Search Terms</label>
                <input
                  type="text"
                  value={editForm.search_terms || ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, search_terms: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Marque</label>
                <input
                  type="text"
                  value={editForm.brand_name || ""}
                  onChange={(e) => setEditForm((f) => ({ ...f, brand_name: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
            </div>
            <div className="sticky bottom-0 bg-white border-t border-gray-200 px-6 py-4 flex items-center gap-3">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 px-4 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-60 transition"
              >
                {saving ? "Sauvegarde..." : "Sauvegarder"}
              </button>
              {(() => {
                const l = listings.find((x) => x.id === editingId);
                if (l && l.status !== "approved" && l.status !== "published") {
                  return (
                    <button
                      onClick={async () => {
                        await handleSave();
                        await handleApprove(editingId);
                        setEditingId(null);
                      }}
                      className="flex-1 px-4 py-2.5 bg-green-600 text-white text-sm font-semibold rounded-lg hover:bg-green-700 transition"
                    >
                      Sauvegarder & Approuver
                    </button>
                  );
                }
                return null;
              })()}
            </div>
          </div>
        </div>
      )}

      {/* Batch action bar */}
      <ActionBar count={selected.size} onClear={() => setSelected(new Set())}>
        <button
          onClick={handleApproveBatch}
          disabled={approving}
          className="px-4 py-2 bg-emerald-600 text-white text-sm font-semibold rounded-lg hover:bg-emerald-700 disabled:opacity-60 transition"
        >
          {approving ? "Approbation..." : `Approuver ${selected.size}`}
        </button>
        <div className="h-5 w-px bg-gray-200" />
        {activeAccounts.length > 0 && (
          <>
            <select
              value={pushAccountId}
              onChange={(e) => setPushAccountId(e.target.value)}
              className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none"
            >
              <option value="">Compte marketplace...</option>
              {activeAccounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.platform} ({a.seller_id || "N/A"})
                </option>
              ))}
            </select>
            <button
              onClick={handlePushBatch}
              disabled={pushing || !pushAccountId}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-60 transition"
            >
              {pushing ? "Push..." : `Pousser ${selected.size}`}
            </button>
          </>
        )}
      </ActionBar>
    </div>
  );
}
