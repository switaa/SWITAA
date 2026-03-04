"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Account {
  id: string;
  platform: string;
  seller_id: string;
  is_active: boolean;
}

export default function MarketplacePage() {
  const [accounts, setAccounts] = useState<Account[]>([]);

  useEffect(() => {
    api.get<Account[]>("/api/v1/marketplace/accounts").then(setAccounts).catch(console.error);
  }, []);

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Comptes Marketplace</h2>

      <div className="grid gap-4">
        {accounts.map((a) => (
          <div key={a.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold capitalize">{a.platform.replace("_", " ")}</h3>
                <p className="text-sm text-gray-500">Seller ID: {a.seller_id || "Non configuré"}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                a.is_active ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
              }`}>
                {a.is_active ? "Actif" : "Inactif"}
              </span>
            </div>
          </div>
        ))}
        {accounts.length === 0 && (
          <p className="text-gray-400 text-center py-8">Aucun compte marketplace configuré.</p>
        )}
      </div>
    </div>
  );
}
