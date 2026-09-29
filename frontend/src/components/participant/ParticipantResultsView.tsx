import React from 'react';
import { useApp } from '../../context/AppContext';
import { Trophy } from 'lucide-react';

export const ParticipantResultsView: React.FC = () => {
  const { projects, activeEvent } = useApp();
  const published = projects.filter(p => p.rank > 0).sort((a, b) => a.rank - b.rank);

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      <div className="flex items-center justify-between pb-3 border-b border-neutral-200 dark:border-[#1E2032]">
        <div>
          <h1 className="text-3xl font-heading font-black text-neutral-900 dark:text-white">Published Result</h1>
          <p className="text-xs text-neutral-500 font-mono-tech mt-1">Only backend-published result snapshots are displayed.</p>
        </div>
        <div className="flex items-center gap-2 font-mono-tech text-xs bg-neutral-100 dark:bg-[#0C0E1A] px-3 py-1.5 border border-neutral-200 dark:border-[#1E2032]">
          <Trophy className="w-4 h-4 text-amber-400" />
          <span>{activeEvent.title}</span>
        </div>
      </div>

      {published.length === 0 ? (
        <div className="border border-neutral-200 dark:border-[#1E2032] bg-white dark:bg-[#07080E] p-8 text-sm text-neutral-500">
          Results have not been published for your project yet.
        </div>
      ) : (
        <div className="space-y-3">
          {published.map(project => (
            <div key={project.id} className="grid grid-cols-12 gap-4 px-6 py-5 border border-neutral-200 dark:border-[#1E2032] bg-white dark:bg-[#07080E]">
              <div className="col-span-2 font-mono-tech font-black text-neutral-500">#{project.rank}</div>
              <div className="col-span-6">
                <div className="font-heading font-bold text-neutral-900 dark:text-white">{project.codeName}</div>
                <div className="text-xs text-neutral-500 mt-1">{project.track}</div>
              </div>
              <div className="col-span-4 text-right">
                <div className="font-heading font-black text-xl text-[#00F0FF] dark:text-[#C6FF1A]">{project.normalizedScore.toFixed(3)}</div>
                <div className="text-[11px] font-mono-tech text-neutral-400">Final normalized score</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
