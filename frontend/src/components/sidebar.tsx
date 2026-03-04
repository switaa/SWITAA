"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logout } from "@/lib/auth";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/research", label: "Recherche", icon: "🔍" },
  { href: "/products", label: "Produits", icon: "📦" },
  { href: "/opportunities", label: "Opportunités", icon: "🎯" },
  { href: "/profitability", label: "Rentabilité", icon: "💰" },
  { href: "/suppliers", label: "Fournisseurs", icon: "🏭" },
  { href: "/listings", label: "Listings", icon: "📝" },
  { href: "/marketplace", label: "Marketplace", icon: "🛒" },
  { href: "/settings", label: "Paramètres", icon: "⚙️" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <h1 className="text-2xl font-bold text-blue-600">Marcus</h1>
        <p className="text-xs text-gray-400 mt-1">Product Research SaaS</p>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition ${
                active
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <span>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-200">
        <button
          onClick={logout}
          className="w-full px-4 py-2 text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition"
        >
          Déconnexion
        </button>
      </div>
    </aside>
  );
}
