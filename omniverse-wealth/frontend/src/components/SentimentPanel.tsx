"use client";

import { useEffect, useState } from "react";

export default function SentimentPanel() {
  const [fng, setFng] = useState<{ value: number; classification: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchFng = async () => {
      try {
        const res = await fetch("https://api.alternative.me/fng/?limit=1&format=json");
        if (res.ok) {
          const data = await res.json();
          const entry = data.data?.[0];
          if (entry) {
            setFng({
              value: parseInt(entry.value),
              classification: entry.value_classification,
            });
          }
        }
      } catch {}
      setLoading(false);
    };
    fetchFng();
    const interval = setInterval(fetchFng, 60000);
    return () => clearInterval(interval);
  }, []);

  const getColor = (value: number) => {
    if (value <= 25) return "text-red-400";
    if (value <= 45) return "text-orange-400";
    if (value <= 55) return "text-yellow-400";
    if (value <= 75) return "text-green-400";
    return "text-green-300";
  };

  const getBarColor = (value: number) => {
    if (value <= 25) return "bg-red-500";
    if (value <= 45) return "bg-orange-500";
    if (value <= 55) return "bg-yellow-500";
    if (value <= 75) return "bg-green-500";
    return "bg-green-400";
  };

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1.5 border-b border-slate-800">
        <h3 className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider">
          Market Sentiment
        </h3>
      </div>
      <div className="flex-1 flex flex-col items-center justify-center px-3">
        {loading ? (
          <span className="text-xs text-slate-500">Loading...</span>
        ) : fng ? (
          <>
            {/* Value */}
            <div className={`text-2xl font-bold ${getColor(fng.value)}`}>
              {fng.value}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5 mb-2">
              {fng.classification}
            </div>

            {/* Bar */}
            <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${getBarColor(fng.value)}`}
                style={{ width: `${fng.value}%` }}
              />
            </div>
            <div className="flex justify-between w-full mt-1 text-[8px] text-slate-600">
              <span>Extreme Fear</span>
              <span>Extreme Greed</span>
            </div>
          </>
        ) : (
          <span className="text-xs text-slate-500">Unavailable</span>
        )}
      </div>
    </div>
  );
}
