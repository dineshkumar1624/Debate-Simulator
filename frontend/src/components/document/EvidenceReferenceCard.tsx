import React from 'react';
import { ExternalLink, BookOpen, AlertTriangle, CheckCircle2, HelpCircle } from 'lucide-react';
import { EvidenceReference, EvidenceType } from '../../types/document';

interface EvidenceReferenceCardProps {
  evidence: EvidenceReference;
  onViewSource?: (pageNumber: number) => void;
  compact?: boolean;
}

const TYPE_CONFIG: Record<
  EvidenceType,
  { label: string; color: string; border: string; bg: string; icon: React.ReactNode }
> = {
  evidence: {
    label: 'DOCUMENT EVIDENCE',
    color: 'text-sky-300',
    border: 'border-sky-500/40',
    bg: 'bg-sky-500/10',
    icon: <CheckCircle2 className="w-3 h-3 text-sky-400" />,
  },
  limitation: {
    label: 'STATED LIMITATION',
    color: 'text-purple-300',
    border: 'border-purple-500/40',
    bg: 'bg-purple-500/10',
    icon: <AlertTriangle className="w-3 h-3 text-purple-400" />,
  },
  claim: {
    label: 'PRIMARY CLAIM',
    color: 'text-indigo-300',
    border: 'border-indigo-500/40',
    bg: 'bg-indigo-500/10',
    icon: <BookOpen className="w-3 h-3 text-indigo-400" />,
  },
  counterargument: {
    label: 'COUNTERARGUMENT',
    color: 'text-rose-300',
    border: 'border-rose-500/40',
    bg: 'bg-rose-500/10',
    icon: <AlertTriangle className="w-3 h-3 text-rose-400" />,
  },
  assumption: {
    label: 'ASSUMPTION',
    color: 'text-amber-300',
    border: 'border-amber-500/40',
    bg: 'bg-amber-500/10',
    icon: <HelpCircle className="w-3 h-3 text-amber-400" />,
  },
  uncertainty: {
    label: 'UNCERTAINTY',
    color: 'text-emerald-300',
    border: 'border-emerald-500/40',
    bg: 'bg-emerald-500/10',
    icon: <HelpCircle className="w-3 h-3 text-emerald-400" />,
  },
};

export const EvidenceReferenceCard: React.FC<EvidenceReferenceCardProps> = ({
  evidence,
  onViewSource,
  compact = false,
}) => {
  const conf = TYPE_CONFIG[evidence.type] || TYPE_CONFIG.evidence;

  return (
    <div
      className={`rounded-2xl border ${conf.border} ${conf.bg} ${compact ? 'p-2.5' : 'p-3.5 sm:p-4'} backdrop-blur-xl transition-all shadow-sm hover:border-white/30`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5">
          {conf.icon}
          <span className={`text-[10px] font-mono font-bold uppercase tracking-wider ${conf.color}`}>
            {conf.label}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-slate-400">
            Relevance: <strong className="text-white">{evidence.relevanceScore}%</strong>
          </span>
        </div>
      </div>

      <p className="text-xs font-mono text-slate-200 leading-relaxed italic mb-3">
        "{evidence.excerpt}"
      </p>

      <div className="flex items-center justify-between pt-2 border-t border-white/10 text-[11px] font-mono">
        <span className="text-slate-400 truncate max-w-[200px] sm:max-w-[280px]">
          📄 Page {evidence.pageNumber} • {evidence.sectionTitle}
        </span>
        {onViewSource && (
          <button
            type="button"
            onClick={() => onViewSource(evidence.pageNumber)}
            className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 transition-colors font-semibold cursor-pointer shrink-0"
          >
            <span>VIEW SOURCE</span>
            <ExternalLink className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  );
};

export default EvidenceReferenceCard;
