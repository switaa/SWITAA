"use client";

import { useEffect, useState } from "react";
import { getMe } from "@/lib/auth";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    getMe().then(setUser);
  }, []);

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Paramètres</h2>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 max-w-lg">
        <h3 className="text-lg font-semibold mb-4">Profil</h3>
        {user ? (
          <div className="space-y-3 text-sm">
            <div>
              <label className="text-gray-500">Email</label>
              <p className="font-medium">{user.email}</p>
            </div>
            <div>
              <label className="text-gray-500">Nom</label>
              <p className="font-medium">{user.full_name || "Non renseigné"}</p>
            </div>
            <div>
              <label className="text-gray-500">Rôle</label>
              <p className="font-medium capitalize">{user.role}</p>
            </div>
          </div>
        ) : (
          <p className="text-gray-400">Chargement...</p>
        )}
      </div>
    </div>
  );
}
