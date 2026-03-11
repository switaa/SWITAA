interface ActionBarProps {
  count: number;
  children: React.ReactNode;
  onClear: () => void;
}

export default function ActionBar({ count, children, onClear }: ActionBarProps) {
  if (count === 0) return null;

  return (
    <div className="fixed bottom-0 left-64 right-0 z-40 bg-white border-t border-gray-200 shadow-[0_-4px_12px_rgba(0,0,0,0.08)] px-6 py-3 flex items-center gap-4 animate-in slide-in-from-bottom duration-200">
      <div className="flex items-center gap-2 min-w-0">
        <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-blue-600 text-white text-xs font-bold">
          {count}
        </span>
        <span className="text-sm font-medium text-gray-700 whitespace-nowrap">
          sélectionné{count > 1 ? "s" : ""}
        </span>
      </div>
      <div className="h-6 w-px bg-gray-200" />
      <div className="flex items-center gap-3 flex-1">{children}</div>
      <button
        onClick={onClear}
        className="text-sm text-gray-500 hover:text-gray-700 transition whitespace-nowrap"
      >
        Annuler
      </button>
    </div>
  );
}
