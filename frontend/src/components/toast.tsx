"use client";

import { useEffect, useState, useCallback, createContext, useContext } from "react";

type ToastType = "success" | "error" | "info";

interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
  link?: { href: string; label: string };
}

interface ToastContextType {
  toast: (message: string, type?: ToastType, link?: { href: string; label: string }) => void;
}

const ToastContext = createContext<ToastContextType>({ toast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

let nextId = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const toast = useCallback(
    (message: string, type: ToastType = "info", link?: { href: string; label: string }) => {
      const id = ++nextId;
      setItems((prev) => [...prev, { id, message, type, link }]);
      setTimeout(() => setItems((prev) => prev.filter((t) => t.id !== id)), 5000);
    },
    [],
  );

  const dismiss = (id: number) => setItems((prev) => prev.filter((t) => t.id !== id));

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm">
        {items.map((t) => (
          <ToastBubble key={t.id} item={t} onDismiss={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

const TYPE_STYLES: Record<ToastType, string> = {
  success: "bg-green-600 text-white",
  error: "bg-red-600 text-white",
  info: "bg-gray-800 text-white",
};

const TYPE_ICONS: Record<ToastType, string> = {
  success: "\u2713",
  error: "\u2717",
  info: "\u24d8",
};

function ToastBubble({ item, onDismiss }: { item: ToastItem; onDismiss: () => void }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true));
  }, []);

  return (
    <div
      className={`rounded-lg px-4 py-3 shadow-lg transition-all duration-300 flex items-start gap-3 ${
        TYPE_STYLES[item.type]
      } ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"}`}
    >
      <span className="text-lg font-bold mt-0.5 shrink-0">{TYPE_ICONS[item.type]}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{item.message}</p>
        {item.link && (
          <a
            href={item.link.href}
            className="text-xs underline opacity-80 hover:opacity-100 mt-1 inline-block"
          >
            {item.link.label} &rarr;
          </a>
        )}
      </div>
      <button onClick={onDismiss} className="text-white/60 hover:text-white text-lg leading-none">
        &times;
      </button>
    </div>
  );
}
