"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Product {
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
  source: string;
  status: string;
}

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [marketplace, setMarketplace] = useState("");

  useEffect(() => {
    const params = marketplace ? `?marketplace=${marketplace}` : "";
    api.get<Product[]>(`/api/v1/products/${params}`).then(setProducts).catch(console.error);
  }, [marketplace]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Produits</h2>
        <select
          value={marketplace}
          onChange={(e) => setMarketplace(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">Toutes les marketplaces</option>
          <option value="amazon_fr">Amazon FR</option>
          <option value="amazon_de">Amazon DE</option>
          <option value="amazon_us">Amazon US</option>
          <option value="amazon_uk">Amazon UK</option>
        </select>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">ASIN</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Titre</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Prix</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">BSR</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Ventes/mois</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Avis</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">Source</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-blue-600">{p.asin}</td>
                <td className="px-4 py-3 max-w-xs truncate">{p.title}</td>
                <td className="px-4 py-3 text-right">{p.price.toFixed(2)} €</td>
                <td className="px-4 py-3 text-right">{p.bsr?.toLocaleString() ?? "-"}</td>
                <td className="px-4 py-3 text-right">{p.monthly_sales?.toLocaleString() ?? "-"}</td>
                <td className="px-4 py-3 text-right">{p.review_count?.toLocaleString() ?? "-"}</td>
                <td className="px-4 py-3 text-center">
                  <span className="px-2 py-1 bg-gray-100 rounded text-xs">{p.source}</span>
                </td>
              </tr>
            ))}
            {products.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  Aucun produit. Lancez une découverte.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
