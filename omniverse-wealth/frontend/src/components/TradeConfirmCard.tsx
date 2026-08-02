"use client";

import { Shield, AlertTriangle, Check, X } from "lucide-react";

interface TradeConfirmProps {
  trade: {
    market: string;
    side: "buy" | "sell";
    volume: string;
    price: string;
    reasoning: string;
  };
  onConfirm: () => void;
  onCancel: () => void;
}

export default function TradeConfirmCard({ trade, onConfirm, onCancel }: TradeConfirmProps) {
  const isBuy = trade.side === "buy";
  const estimatedValue = (
    parseFloat(trade.volume) * parseFloat(trade.price.replace(/,/g, ""))
  ).toLocaleString();

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="w-full max-w-md mx-4 bg-[#111827] border border-slate-700 rounded-xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div
          className={`px-6 py-4 border-b border-slate-700 ${
            isBuy ? "bg-green-500/5" : "bg-red-500/5"
          }`}
        >
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center ${
                isBuy ? "bg-green-500/20" : "bg-red-500/20"
              }`}
            >
              <Shield
                size={20}
                className={isBuy ? "text-green-400" : "text-red-400"}
              />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">交易確認</h3>
              <p className="text-xs text-slate-400">
                提彌斯風控審查通過 — 等待用戶授權
              </p>
            </div>
          </div>
        </div>

        {/* Trade Details */}
        <div className="px-6 py-4 space-y-3">
          <DetailRow
            label="交易對"
            value={trade.market.toUpperCase().replace("TWD", "/TWD")}
          />
          <DetailRow
            label="方向"
            value={isBuy ? "買入 (Buy)" : "賣出 (Sell)"}
            valueClass={isBuy ? "text-green-400" : "text-red-400"}
          />
          <DetailRow label="數量" value={trade.volume} />
          <DetailRow label="價格" value={`${trade.price} TWD`} />
          <DetailRow
            label="預估金額"
            value={`~${estimatedValue} TWD`}
            valueClass="text-white font-bold"
          />

          {/* Reasoning */}
          <div className="mt-4 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">
              AI 建議理由
            </p>
            <p className="text-xs text-slate-300">{trade.reasoning}</p>
          </div>

          {/* Risk Warning */}
          <div className="flex items-start gap-2 p-3 bg-amber-500/5 border border-amber-500/20 rounded-lg">
            <AlertTriangle size={14} className="text-amber-400 flex-shrink-0 mt-0.5" />
            <p className="text-[11px] text-amber-300/80">
              此為真實交易操作，資金將從您的 MAX 帳戶中扣除。請確認交易內容無誤後再授權執行。
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="px-6 py-4 border-t border-slate-700 flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-slate-800 border border-slate-600 rounded-lg text-slate-300 text-sm font-medium hover:bg-slate-700 transition"
          >
            <X size={14} />
            取消
          </button>
          <button
            onClick={onConfirm}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-white text-sm font-medium transition ${
              isBuy
                ? "bg-green-600 hover:bg-green-500 shadow-lg shadow-green-500/20"
                : "bg-red-600 hover:bg-red-500 shadow-lg shadow-red-500/20"
            }`}
          >
            <Check size={14} />
            授權並下單
          </button>
        </div>
      </div>
    </div>
  );
}

function DetailRow({
  label,
  value,
  valueClass = "text-white",
}: {
  label: string;
  value: string;
  valueClass?: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-slate-500">{label}</span>
      <span className={`text-sm font-mono ${valueClass}`}>{value}</span>
    </div>
  );
}
