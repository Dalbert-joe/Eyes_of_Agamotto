import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { Button } from '../common/Button';
import {
  Trophy,
  FileCode2,
  Calendar,
  Users,
  Award,
  Layers,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Plus,
  CheckCircle2,
  Lock,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  Tag
} from 'lucide-react';

export const ParticipantDashboardView: React.FC = () => {
  const { currentUser, activeEvent, projects, teams, navigate, setToast } = useApp();

  // 4 Accordion / expandable sections state (default all open or toggled)
  const [openSections, setOpenSections] = useState<{ [key: string]: boolean }>({
    enrolled: true,
    projects: true,
    achievements: true,
    skillset: true
  });

  const toggleSection = (section: string) => {
    setOpenSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Current user's project and team
  const myProject = projects[0];
  const myTeam = teams[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-neutral-200 dark:border-[#1E2032]">
        <div>
          <h1 className="text-3xl font-heading font-black text-neutral-900 dark:text-white">
            Dashboard
          </h1>
          <p className="text-xs text-neutral-500 font-mono-tech mt-1">
            Overview of your enrolled competitions, submitted projects, achievements, and technical skillset.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate('/participant/events')}
            icon={<Plus className="w-3.5 h-3.5" />}
          >
            Explore Competitions
          </Button>
        </div>
      </div>

      {/* 4 EXPANDABLE SECTIONS */}
      <div className="space-y-4">
        {/* SECTION 1: ENROLLED COMPETITIONS */}
        <div className="rounded-[8px] border border-neutral-200 dark:border-[#1E2032] bg-white dark:bg-[#06070E] overflow-hidden shadow-xs transition-all">
          <button
            onClick={() => toggleSection('enrolled')}
            className="w-full p-4 sm:p-5 flex items-center justify-between text-left hover:bg-neutral-50 dark:hover:bg-[#0A0C16] transition-colors cursor-pointer select-none"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-[6px] bg-[#00F0FF]/15 text-black dark:text-[#00F0FF] flex items-center justify-center font-bold">
                <Calendar className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-base sm:text-lg font-heading font-black text-neutral-900 dark:text-white tracking-wide">
                  ENROLLED COMPETITIONS
                </h3>
                <span className="text-xs font-mono-tech text-neutral-500">
                  1 Active Tournament · 2 Upcoming
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 text-neutral-400">
              <span className="text-xs font-mono-tech hidden sm:inline">
                {openSections.enrolled ? 'Collapse' : 'Expand'}
              </span>
              {openSections.enrolled ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
            </div>
          </button>

          {openSections.enrolled && (
            <div className="p-5 pt-0 border-t border-neutral-100 dark:border-[#141524] space-y-4 mt-2">
              {/* Active Enrolled Event */}
              <div className="p-4 rounded-[6px] border border-neutral-200 dark:border-[#1C1E30] bg-neutral-50 dark:bg-[#0A0C16] space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono-tech font-bold bg-[#00F0FF] text-black">
                        ACTIVE · ENROLLED
                      </span>
                      <span className="text-xs font-mono-tech text-neutral-500">
                        Code: {activeEvent.eventCode}
                      </span>
                    </div>
                    <h4 className="text-lg font-heading font-bold text-neutral-900 dark:text-white mt-1">
                      {activeEvent.title}
                    </h4>
                    <p className="text-xs text-neutral-500 font-sans mt-0.5">
                      {activeEvent.tagline}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => navigate('/participant/events/[eventId]/team', { eventId: activeEvent.id })}
                      icon={<Users className="w-3.5 h-3.5" />}
                    >
                      Manage Squad
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate('/participant/events/[eventId]/submission', { eventId: activeEvent.id })}
                      icon={<FileCode2 className="w-3.5 h-3.5" />}
                    >
                      Project Submission
                    </Button>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-neutral-200 dark:border-neutral-800 text-xs font-mono-tech">
                  <div>
                    <span className="text-neutral-500 block text-[10px]">PRIZE POOL</span>
                    <span className="font-bold text-neutral-900 dark:text-white">{activeEvent.prizes}</span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block text-[10px]">EVALUATION WINDOW</span>
                    <span className="font-bold text-neutral-900 dark:text-white">{activeEvent.startDate} — {activeEvent.endDate}</span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block text-[10px]">MY SQUAD</span>
                    <span className="font-bold text-[#00F0FF]">{myTeam?.name || 'No team yet'} ({myTeam?.members.length || 0} members)</span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block text-[10px]">DOUBLE-BLIND POLICY</span>
                    <span className="font-bold text-emerald-500 flex items-center gap-1">
                      <Lock className="w-3 h-3" /> Shield Active
                    </span>
                  </div>
                </div>
              </div>

              {/* Other Open Events to Explore */}
              <div className="flex items-center justify-between p-3 rounded-[6px] bg-neutral-100/60 dark:bg-[#0B0D18] text-xs font-mono-tech">
                <span className="text-neutral-600 dark:text-neutral-400">
                  Ready to compete in more categories? 2 other open tournaments available.
                </span>
                <button
                  onClick={() => navigate('/participant/events')}
                  className="text-[#00F0FF] dark:text-[#C6FF1A] font-bold hover:underline cursor-pointer"
                >
                  Explore All Competitions →
                </button>
              </div>
            </div>
          )}
        </div>

        {/* SECTION 2: PROJECTS SUBMITTED */}
        <div className="rounded-[8px] border border-neutral-200 dark:border-[#1E2032] bg-white dark:bg-[#06070E] overflow-hidden shadow-xs transition-all">
          <button
            onClick={() => toggleSection('projects')}
            className="w-full p-4 sm:p-5 flex items-center justify-between text-left hover:bg-neutral-50 dark:hover:bg-[#0A0C16] transition-colors cursor-pointer select-none"
          >
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-[6px] bg-[#C6FF1A]/15 text-black dark:text-[#C6FF1A] flex items-center justify-center font-bold">
                <FileCode2 className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-base sm:text-lg font-heading font-black text-neutral-900 dark:text-white tracking-wide">
                  PROJECTS SUBMITTED
                </h3>
                <span className="text-xs font-mono-tech text-neutral-500">
                  {projects.length} Project{projects.length === 1 ? "" : "s"} Submitted
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 text-neutral-400">
              <span className="text-xs font-mono-tech hidden sm:inline">
                {openSections.projects ? 'Collapse' : 'Expand'}
              </span>
              {openSections.projects ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
            </div>
          </button>

          {openSections.projects && (
            <div className="p-5 pt-0 border-t border-neutral-100 dark:border-[#141524] space-y-4 mt-2">
              <div className="p-4 rounded-[6px] border border-neutral-200 dark:border-[#1C1E30] bg-neutral-50 dark:bg-[#0A0C16] space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono-tech text-xs font-bold text-amber-500">
                        {myProject?.id || "—"} (BLIND CODENAME: {myProject?.codeName || "No project submitted"})
                      </span>
                      <span className="text-neutral-400">·</span>
                      <span className="font-mono-tech text-xs text-neutral-500">
                        Track: {myProject?.track || "—"}
                      </span>
                    </div>
                    <h4 className="text-lg font-heading font-black text-neutral-900 dark:text-white mt-1">
                      {myProject?.title || ""}
                    </h4>
                    <p className="text-xs text-neutral-600 dark:text-neutral-400 line-clamp-2 mt-0.5">
                      {myProject?.tagline || myProject?.problem || ""}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigate('/participant/events/[eventId]/submission', { eventId: activeEvent.id })}
                    >
                      Edit Submission
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => navigate('/participant/events/[eventId]/results', { eventId: activeEvent.id })}
                      icon={<Trophy className="w-3.5 h-3.5" />}
                    >
                      View Live Standing
                    </Button>
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-neutral-200 dark:border-neutral-800 text-xs font-mono-tech">
                  <div>
                    <span className="text-neutral-500 block text-[10px]">SUBMISSION STATE</span>
                    <span className="font-bold text-emerald-500 uppercase">
                      {myProject?.status?.toUpperCase() || "NOT SUBMITTED"}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block text-[10px]">EVALUATORS COMPLETED</span>
                    <span className="font-bold text-neutral-900 dark:text-white">
                      {myProject?.scores?.filter(s => s.status === "finalized" || s.status === "locked").length || 0} / {activeEvent.judgesPerProject} Panels Scored
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block text-[10px]">REPOSITORY</span>
                    <span className="font-bold text-[#00F0FF] truncate block">
                      {myProject?.githubUrl || "—"}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block text-[10px]">NORMALIZED SCORE</span>
                    <span className="font-bold text-[#C6FF1A]">
                      {(myProject?.normalizedScore || 0).toFixed(1)} / 100
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* SECTION 3: RECORDED STATUS */}
        <div className="rounded-[8px] border border-neutral-200 dark:border-[#1E2032] bg-white dark:bg-[#06070E] overflow-hidden shadow-xs">
          <div className="p-5">
            <h3 className="text-base sm:text-lg font-heading font-black text-neutral-900 dark:text-white">RECORDED STATUS</h3>
            <p className="text-xs text-neutral-500 mt-1">Only persisted event and submission state is shown here.</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
              <div className="border border-neutral-200 dark:border-neutral-800 p-3"><span className="text-[10px] text-neutral-400 block">TEAM MEMBERS</span><strong>{myTeam?.members.length || 0}</strong></div>
              <div className="border border-neutral-200 dark:border-neutral-800 p-3"><span className="text-[10px] text-neutral-400 block">PROJECT</span><strong>{myProject ? 'SUBMITTED' : 'NOT SUBMITTED'}</strong></div>
              <div className="border border-neutral-200 dark:border-neutral-800 p-3"><span className="text-[10px] text-neutral-400 block">VERSION</span><strong>{myProject?.versions?.length || 0}</strong></div>
              <div className="border border-neutral-200 dark:border-neutral-800 p-3"><span className="text-[10px] text-neutral-400 block">RESULT</span><strong>{myProject?.rank ? `#${myProject.rank}` : 'PENDING'}</strong></div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};
