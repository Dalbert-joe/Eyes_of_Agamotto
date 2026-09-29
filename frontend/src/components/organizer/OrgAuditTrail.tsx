import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import {
  FileCode2,
  ShieldCheck,
  Search,
  Filter,
  Download,
} from 'lucide-react';

export const OrgAuditTrail: React.FC = () => {
  const { auditLogs, setToast } = useApp();
  const [filterAction, setFilterAction] = useState<string>('all');
  const filteredLogs = auditLogs.filter(log => {
    if (filterAction === 'all') return true;
    return log.action.toLowerCase().includes(filterAction.toLowerCase()) ||
           log.actorRole.toLowerCase() === filterAction.toLowerCase();
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-heading font-bold text-neutral-900 dark:text-white">
            Audit Trail
          </h2>
          <p className="text-sm text-neutral-500 mt-0.5">
            Recorded timeline of important lifecycle mutations, scoring actions, and conflict checks.
          </p>
        </div>


      </div>

      {/* Filter Chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {['all', 'judge', 'organizer', 'system', 'conflict', 'evaluation'].map(f => (
          <button
            key={f}
            onClick={() => setFilterAction(f)}
            className={`px-3 py-1.5 rounded-md text-xs font-mono-tech uppercase font-semibold transition-colors cursor-pointer ${
              filterAction === f
                ? 'bg-neutral-900 text-white dark:bg-white dark:text-black'
                : 'bg-neutral-100 dark:bg-[#15151F] text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Audit Log Stream */}
      <div className="bg-white dark:bg-[#0E0E14] border border-neutral-200 dark:border-[#222436] rounded-md overflow-hidden shadow-sm divide-y divide-neutral-200 dark:divide-[#222436]">
        {filteredLogs.map(log => {
          return (
            <div
              key={log.id}
              className="p-4 sm:p-5 hover:bg-neutral-50/60 dark:hover:bg-[#12121A] transition-colors space-y-2"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono-tech text-xs font-bold px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300">
                    {log.action}
                  </span>
                  <span className="font-mono-tech text-xs text-neutral-400">
                    by <strong className="text-neutral-700 dark:text-neutral-200">{log.actor}</strong> ({log.actorRole})
                  </span>
                </div>

                <div className="font-mono-tech text-xs text-neutral-500">
                  {log.timestamp}
                </div>
              </div>

              <p className="text-xs text-neutral-700 dark:text-neutral-300 leading-relaxed font-sans">
                {log.details}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
