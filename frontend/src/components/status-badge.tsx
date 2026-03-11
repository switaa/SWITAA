const STYLES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600 border-gray-200",
  auto_generated: "bg-blue-100 text-blue-700 border-blue-200",
  approved: "bg-emerald-100 text-emerald-700 border-emerald-200",
  published: "bg-green-100 text-green-700 border-green-200",
  not_pushed: "bg-gray-100 text-gray-500 border-gray-200",
  pushing: "bg-amber-100 text-amber-700 border-amber-200",
  live: "bg-green-100 text-green-700 border-green-200",
  error: "bg-red-100 text-red-700 border-red-200",
  pending: "bg-yellow-100 text-yellow-700 border-yellow-200",
  success: "bg-green-100 text-green-700 border-green-200",
  FBM: "bg-indigo-100 text-indigo-700 border-indigo-200",
  FBA: "bg-purple-100 text-purple-700 border-purple-200",
  clone_best: "bg-sky-100 text-sky-700 border-sky-200",
  ai_optimize: "bg-violet-100 text-violet-700 border-violet-200",
};

const LABELS: Record<string, string> = {
  draft: "Brouillon",
  auto_generated: "Généré",
  approved: "Approuvé",
  published: "Publié",
  not_pushed: "Non poussé",
  pushing: "En cours...",
  live: "En ligne",
  error: "Erreur",
  pending: "En attente",
  success: "Succès",
  FBM: "FBM",
  FBA: "FBA",
  clone_best: "Clone",
  ai_optimize: "IA",
};

interface StatusBadgeProps {
  value: string;
  size?: "sm" | "md";
}

export default function StatusBadge({ value, size = "sm" }: StatusBadgeProps) {
  const style = STYLES[value] || "bg-gray-100 text-gray-600 border-gray-200";
  const label = LABELS[value] || value;
  const sizeClass = size === "md" ? "px-3 py-1 text-xs" : "px-2 py-0.5 text-xs";

  return (
    <span
      className={`inline-block rounded-full font-semibold border whitespace-nowrap ${style} ${sizeClass}`}
    >
      {label}
    </span>
  );
}
