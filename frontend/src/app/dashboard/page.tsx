"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Stats {
  total_products: number;
  total_opportunities: number;
  a_launch_count: number;
  total_listings: number;
  total_pushes: number;
  total_supplier_products: number;
  avg_score: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    api.get<Stats>("/api/v1/dashboard/stats").then(setStats).catch(console.error);
  }, []);

  if (!stats) {
    return <div className="animate-pulse text-gray-400">Chargement...</div>;
  }

  const cards = [
    { label: "Produits", value: stats.total_products, color: "bg-blue-500" },
    { label: "Opportunités", value: stats.total_opportunities, color: "bg-green-500" },
    { label: "A lancer", value: stats.a_launch_count, color: "bg-emerald-500" },
    { label: "Listings", value: stats.total_listings, color: "bg-purple-500" },
    { label: "Publiés", value: stats.total_pushes, color: "bg-orange-500" },
    { label: "Produits fournisseurs", value: stats.total_supplier_products, color: "bg-indigo-500" },
  ];

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {cards.map((card) => (
          <div key={card.label} className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
            <p className="text-sm text-gray-500 mb-1">{card.label}</p>
            <p className="text-3xl font-bold">{card.value.toLocaleString()}</p>
            <div className={`mt-3 h-1 w-16 rounded ${card.color}`} />
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl shadow-sm p-6 border border-gray-100">
        <h3 className="text-lg font-semibold mb-2">Score moyen des opportunités</h3>
        <p className="text-4xl font-bold text-blue-600">{stats.avg_score}/100</p>
      </div>
    </div>
  );
}
