"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface ListingItem {
  id: string;
  product_id: string;
  marketplace: string;
  title: string;
  status: string;
}

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  ready: "bg-blue-100 text-blue-700",
  published: "bg-green-100 text-green-700",
};

export default function ListingsPage() {
  const [listings, setListings] = useState<ListingItem[]>([]);

  useEffect(() => {
    api.get<ListingItem[]>("/api/v1/listings/").then(setListings).catch(console.error);
  }, []);

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Listings</h2>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Titre</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">Marketplace</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">Statut</th>
            </tr>
          </thead>
          <tbody>
            {listings.map((l) => (
              <tr key={l.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3">{l.title}</td>
                <td className="px-4 py-3 text-center">{l.marketplace}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[l.status] || ""}`}>
                    {l.status}
                  </span>
                </td>
              </tr>
            ))}
            {listings.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-8 text-center text-gray-400">
                  Aucun listing créé.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
