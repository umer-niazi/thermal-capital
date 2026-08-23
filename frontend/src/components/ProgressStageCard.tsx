import React from "react";
import { Check, Loader2 } from "lucide-react";

export interface ProgressStage {
  id: string;
  label: string;
  detail?: string;
  status: "completed" | "active" | "pending";
}

interface ProgressStageCardProps {
  title: string;
  subtitle?: string;
  stages: ProgressStage[];
}

export const ProgressStageCard: React.FC<ProgressStageCardProps> = ({
  title,
  subtitle,
  stages,
}) => {
  return (
    <div className="w-full max-w-md mx-auto bg-white rounded-lg border border-slate-200 shadow-sm p-6 text-left">
      <div className="flex items-center gap-3 mb-4 pb-3 border-b border-slate-100">
        <div className="w-8 h-8 rounded-full bg-brand-50 border border-brand-200 flex items-center justify-center flex-shrink-0">
          <Loader2 className="w-4 h-4 text-brand-600 animate-spin" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
          {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
        </div>
      </div>

      <div className="space-y-3">
        {stages.map((st) => {
          const isCompleted = st.status === "completed";
          const isActive = st.status === "active";
          const isPending = st.status === "pending";

          return (
            <div
              key={st.id}
              className={`flex items-start gap-3 text-xs transition-opacity duration-200 ${
                isPending ? "opacity-45" : "opacity-100"
              }`}
            >
              <div className="mt-0.5 flex-shrink-0">
                {isCompleted && (
                  <div className="w-4 h-4 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                    <Check className="w-2.5 h-2.5 stroke-[3]" />
                  </div>
                )}
                {isActive && (
                  <div className="w-4 h-4 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center">
                    <Loader2 className="w-2.5 h-2.5 animate-spin" />
                  </div>
                )}
                {isPending && (
                  <div className="w-4 h-4 rounded-full border border-slate-300 bg-slate-50 flex items-center justify-center text-[10px] text-slate-400">
                    ○
                  </div>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <span
                  className={`font-medium ${
                    isCompleted
                      ? "text-slate-800"
                      : isActive
                      ? "text-brand-900 font-semibold"
                      : "text-slate-500"
                  }`}
                >
                  {st.label}
                </span>
                {st.detail && (
                  <p className="text-[11px] text-slate-400 truncate">{st.detail}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
