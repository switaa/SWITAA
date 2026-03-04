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

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<SupplierItem[]>([]);

  useEffect(() => {
    api.get<SupplierItem[]>("/api/v1/suppliers/").then(setSuppliers).catch(console.error);
  }, []);

  async function triggerImport(id: string) {
    await api.post(`/api/v1/suppliers/${id}/import`);
    alert("Import lancé en arrière-plan");
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Fournisseurs</h2>

      <div className="grid gap-4">
        {suppliers.map((s) => (
          <div key={s.id} className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex items-center justify-between">
            <div>
              <h3 className="font-semibold">{s.name}</h3>
              <p className="text-sm text-gray-500">{s.access_type} - {s.host}</p>
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
          <p className="text-gray-400 text-center py-8">Aucun fournisseur configuré.</p>
        )}
      </div>
    </div>
  );
}
