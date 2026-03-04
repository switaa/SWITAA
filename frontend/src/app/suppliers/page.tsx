"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface SupplierItem {
  id: string;
  name: string;
  access_type: string;
  host: string;
  active: boolean;
}

const SOURCING_TOOLS = [
  {
    name: "Tactical Arbitrage",
    cost: "~99 $/mois",
    description:
      "Scanne 1400+ sites web pour trouver des produits a prix inferieur au prix Amazon. Ideal pour l'arbitrage online.",
    url: "https://tacticalarbitrage.com",
    impact: "Tres eleve",
    impactColor: "text-emerald-600",
    features: [
      "Scan automatique de milliers de sites",
      "Import ASIN en masse (notre export CSV)",
      "Calcul de profit integre",
      "Historique des resultats",
    ],
  },
  {
    name: "PushLap Wholesale",
    cost: "~60 $/mois",
    description:
      "Analyse des listes de prix grossiste pour identifier les produits rentables sur Amazon.",
    url: "https://pushlap.com",
    impact: "Eleve",
    impactColor: "text-blue-600",
    features: [
      "Upload de listes fournisseurs",
      "Detection des restrictions de marque",
      "Calcul de ROI automatique",
      "IP analysis (risques de propriete intellectuelle)",
    ],
  },
  {
    name: "SellerAmp SAS",
    cost: "~20 $/mois",
    description:
      "Extension Chrome pour analyse rapide de rentabilite produit par produit directement sur Amazon.",
    url: "https://selleramp.com",
    impact: "Moyen",
    impactColor: "text-amber-600",
    features: [
      "Analyse en 1 clic sur Amazon",
      "Detection Amazon vendeur",
      "Estimation des frais FBA precis",
      "Verification des restrictions",
    ],
  },
  {
    name: "Alibaba / 1688.com",
    cost: "Gratuit",
    description:
      "Plateformes de sourcing en direct aupres de fabricants chinois. Ideal pour le Private Label.",
    url: "https://www.alibaba.com",
    impact: "Tres eleve (Private Label)",
    impactColor: "text-emerald-600",
    features: [
      "Contact direct fabricants",
      "Prix usine / MOQ",
      "Echantillons possibles",
      "Personalisation produit",
    ],
  },
];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<SupplierItem[]>([]);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    api
      .get<SupplierItem[]>("/api/v1/suppliers/")
      .then(setSuppliers)
      .catch(() => setSuppliers([]));
  }, []);

  const handleExportCSV = async () => {
    setExporting(true);
    try {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("access_token")
          : null;
      const resp = await fetch(
        `${API_BASE}/api/v1/products/export-sourcing?min_score=40&max_bsr=100000&target_margin=35&exclude_amazon_seller=true&limit=100`,
        {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }
      );
      if (!resp.ok) throw new Error("Export failed");
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "marcus_sourcing_top_products.csv";
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
    } finally {
      setExporting(false);
    }
  };

  async function triggerImport(id: string) {
    await api.post(`/api/v1/suppliers/${id}/import`);
    alert("Import lance en arriere-plan");
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Fournisseurs & Sourcing
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Strategie de sourcing et outils recommandes pour atteindre 50K
          EUR/mois
        </p>
      </div>

      {/* Export CTA */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl p-6 text-white shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold">Exporter les Top 100 produits pour le sourcing</h2>
            <p className="text-blue-100 text-sm mt-1">
              Fichier CSV compatible avec Tactical Arbitrage, PushLap et autres
              outils de sourcing.
              <br />
              Contient : ASIN, prix, BuyBox, BSR, ventes, score, cout d&apos;achat
              max, frais FBA.
            </p>
          </div>
          <button
            onClick={handleExportCSV}
            disabled={exporting}
            className="flex-shrink-0 px-6 py-3 bg-white text-blue-700 font-semibold rounded-lg hover:bg-blue-50 disabled:opacity-50 transition"
          >
            {exporting ? "Export en cours..." : "Telecharger CSV"}
          </button>
        </div>
      </div>

      {/* Sourcing Strategy */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <h2 className="text-lg font-bold text-gray-900 mb-4">
          Strategie de sourcing recommandee
        </h2>
        <div className="prose prose-sm max-w-none text-gray-600">
          <ol className="space-y-2">
            <li>
              <strong>Exporter les Top 100 produits</strong> depuis Marcus
              (bouton ci-dessus)
            </li>
            <li>
              <strong>Importer dans Tactical Arbitrage</strong> pour scanner
              automatiquement 1400+ sites et trouver des sources moins cheres
            </li>
            <li>
              <strong>Verifier la rentabilite</strong> avec le calculateur
              Marcus (page Rentabilite) en incluant les frais FBA reels
            </li>
            <li>
              <strong>Valider les restrictions</strong> (marques, hazmat) via
              SellerAmp SAS ou SP-API
            </li>
            <li>
              <strong>Commander des echantillons</strong> puis lister sur
              Amazon FR
            </li>
          </ol>
        </div>

        <div className="mt-6 bg-amber-50 border border-amber-200 rounded-lg p-4">
          <p className="text-sm text-amber-800">
            <strong>Objectif 50K EUR/mois :</strong> avec un portefeuille de
            50-100 produits actifs vendant chacun 15-30 unites/mois a ~75 EUR
            de prix moyen et 40% de marge, le CA cible est de ~125K EUR/mois.
            Le sourcing est le maillon critique.
          </p>
        </div>
      </div>

      {/* Tools */}
      <h2 className="text-lg font-bold text-gray-900">Outils de sourcing</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {SOURCING_TOOLS.map((tool) => (
          <div
            key={tool.name}
            className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-bold text-gray-900">{tool.name}</h3>
                <p className="text-xs text-gray-500 mt-0.5">{tool.cost}</p>
              </div>
              <span
                className={`text-xs font-semibold ${tool.impactColor} bg-gray-50 px-2 py-1 rounded-full`}
              >
                Impact: {tool.impact}
              </span>
            </div>
            <p className="text-sm text-gray-600 mb-3">{tool.description}</p>
            <ul className="space-y-1 mb-4">
              {tool.features.map((f, i) => (
                <li key={i} className="text-xs text-gray-500 flex items-start gap-1.5">
                  <span className="text-emerald-500 mt-0.5">+</span>
                  {f}
                </li>
              ))}
            </ul>
            <a
              href={tool.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:text-blue-800 hover:underline font-medium"
            >
              Visiter le site
            </a>
          </div>
        ))}
      </div>

      {/* Existing Suppliers */}
      <h2 className="text-lg font-bold text-gray-900 mt-8">
        Fournisseurs configures
      </h2>
      <div className="grid gap-4">
        {suppliers.map((s) => (
          <div
            key={s.id}
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex items-center justify-between"
          >
            <div>
              <h3 className="font-semibold">{s.name}</h3>
              <p className="text-sm text-gray-500">
                {s.access_type} - {s.host}
              </p>
            </div>
            <button
              onClick={() => triggerImport(s.id)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition"
            >
              Importer catalogue
            </button>
          </div>
        ))}
        {suppliers.length === 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
            <p className="text-gray-400">Aucun fournisseur configure.</p>
            <p className="text-xs text-gray-400 mt-2">
              Utilisez les outils de sourcing ci-dessus pour trouver des
              fournisseurs, puis ajoutez-les ici.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
