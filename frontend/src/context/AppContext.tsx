import React, {createContext,useContext,useEffect,useMemo,useState} from "react";
import {UserRole,UserProfile,Project,Judge,EventConfig,AuditLog,ParticipantTeam,ParticipantUser,RubricCriterion} from "../types";
import {api,setToken} from "../lib/api";

interface AppContextType {
 currentUser:UserProfile|null; activeRole:UserRole|"guest"; currentPath:string; currentView:string; isDarkMode:boolean;
 events:EventConfig[]; activeEventId:string; activeEvent:EventConfig; eventConfig:EventConfig; projects:Project[]; judges:Judge[];
 participants:ParticipantUser[]; teams:ParticipantTeam[]; participantTeam:ParticipantTeam; auditLogs:AuditLog[];
 activeProjectId:string; activeReviewId:string; toastMessage:string|null; currentJudgeId:string;
 toggleDarkMode:()=>void; navigate:(path:string,params?:any)=>void; navigateTo:(path:string,params?:any)=>void;
 login:(email:string,passwordOrRole?:string|UserRole)=>void; register:(profile:Partial<UserProfile>&{password?:string})=>void; logout:()=>void;
 setToast:(msg:string)=>void; setActiveEventId:(id:string)=>void; setActiveProjectId:(id:string)=>void; setActiveReviewId:(id:string)=>void; setCurrentJudgeId:(id:string)=>void;
 toggleIdentityReveal:(eventId?:string)=>void; assignJudge:(projectId:string,judgeId:string)=>Promise<{success:boolean;reason?:string}>; removeJudge:(projectId:string,judgeId:string)=>void;
 autoAssignJudges:(eventId?:string)=>void; saveEvaluation:(projectId:string,judgeId:string,scores:Record<string,number>,justifications:Record<string,string>,status:"draft"|"finalized"|"locked",isReopened?:boolean)=>void;
 reopenEvaluation:(projectId:string,judgeId:string,reason:string)=>void; updateRubric:(eventId:string,newRubric:RubricCriterion[],tieBreakOrder?:string[])=>void;
 createEvent:(data:Partial<EventConfig>)=>Promise<string>; updateEvent:(eventId:string,data:Partial<EventConfig>)=>void; submitProject:(data:Partial<Project>)=>Promise<boolean>;
 updateProjectSubmission:(projectId:string,data:Partial<Project>)=>Promise<boolean>; joinEventWithCode:(code:string,accessCode?:string)=>Promise<boolean>; createTeam:(name:string,track:string,eventId:string)=>void;
 updateTeamMembers:(teamId:string,members:ParticipantTeam["members"])=>void; approveParticipant:(participantId:string)=>void;
 recalculateScores:(method?:EventConfig["normalizationMethod"],eventId?:string)=>void;
}
const AppContext=createContext<AppContextType|undefined>(undefined);

const emptyEvent:EventConfig={id:"",title:"AGAMOTTO",tagline:"Hackathon Management & Verifiable Judging Platform",description:"",eventCode:"",status:"registration",isPublic:true,registrationMode:"open",minTeamSize:1,maxTeamSize:4,editingPolicy:"allow-until-deadline",versioningEnabled:true,judgesPerProject:3,normalizationMethod:"z_score",identityRevealed:false,tracks:["General"],rubric:[]};

function mapProject(p:any):Project {
 return {...p,submittedAt:String(p.submittedAt||""),scores:(p.scores||[]).map((s:any)=>({...s,submittedAt:String(s.submittedAt||"")})),versions:p.versions||[]};
}
function alias(path:string):string {
 const aliases:Record<string,string>={
  "org-overview":"/organizer","organizer-overview":"/organizer","org-events":"/organizer/events",
  "participant-dashboard":"/participant/dashboard","participant-events":"/participant/events",
  "participant-browse":"/participant/events","participant-submit":"/participant/events/[eventId]/submit",
  "participant-team":"/participant/events/[eventId]/team","participant-results":"/participant/events/[eventId]/results",
  "judge-dashboard":"/judge/dashboard","judge-projects":"/judge/projects","judge-evaluate":"/judge/reviews/[reviewId]"
 };
 return aliases[path]||path;
}

export const AppProvider:React.FC<{children:React.ReactNode}>=({children})=>{
 const [currentUser,setCurrentUser]=useState<UserProfile|null>(null);
 const [activeRole,setActiveRole]=useState<UserRole|"guest">("guest");
 const [currentPath,setCurrentPath]=useState("/");
 const [isDarkMode,setIsDarkMode]=useState(()=>typeof window === "undefined" ? true : localStorage.getItem("agamotto_theme")!=="light");
 const [events,setEvents]=useState<EventConfig[]>([]);
 const [activeEventId,setActiveEventId]=useState("");
 const [projects,setProjects]=useState<Project[]>([]);
 const [judges,setJudges]=useState<Judge[]>([]);
 const [participants,setParticipants]=useState<ParticipantUser[]>([]);
 const [teams,setTeams]=useState<ParticipantTeam[]>([]);
 const [auditLogs,setAuditLogs]=useState<AuditLog[]>([]);
 const [activeProjectId,setActiveProjectId]=useState("");
 const [activeReviewId,setActiveReviewId]=useState("");
 const [currentJudgeId,setCurrentJudgeId]=useState("");
 const [toastMessage,setToastMessage]=useState<string|null>(null);
 const setToast=(msg:string)=>setToastMessage(msg);

 const navigate=(path:string,params?:any)=>{
   const p=alias(path); if(params?.eventId)setActiveEventId(params.eventId); if(params?.projectId)setActiveProjectId(params.projectId); if(params?.reviewId)setActiveReviewId(params.reviewId);
   setCurrentPath(p); window.scrollTo({top:0,behavior:"smooth"});
 };
 const refresh=async(eventId?:string)=>{
   try {
    const es=await api.events(); setEvents(es);
    const id=eventId||activeEventId||es[0]?.id||""; if(id)setActiveEventId(id);
    if(id){
      const [ps,ts]=await Promise.all([api.projects(id).catch(()=>[]),api.teams(id).catch(()=>[])]);
      setProjects(ps.map(mapProject)); setTeams(ts);
      if(activeRole==="organizer"){
        setJudges(await api.judges(id).catch(()=>[]));
        setParticipants(await api.participants(id).catch(()=>[]));
        setAuditLogs(await api.audit(id).catch(()=>[]));
      }
      if(activeRole==="judge" && currentUser){
        setCurrentJudgeId(currentUser.id);
        setJudges([{id:currentUser.id,name:currentUser.name,email:currentUser.email,affiliation:currentUser.affiliation||"",title:currentUser.title||"",track:currentUser.specialization||"",assignedCount:ps.length,completedCount:0,conflicts:[],scoringBias:0} as Judge]);
      }
    }
    if(activeRole==="participant"){
      const [myTeams,myProjects,published]=await Promise.all([api.myTeams().catch(()=>[]),api.myProjects().catch(()=>[]),id?api.results(id).catch(()=>[]):Promise.resolve([])]);
      setTeams(myTeams);
      const resultMap=new Map((published as any[]).map(r=>[r.projectId,r]));
      setProjects((myProjects as any[]).map(p=>mapProject({...p,...(resultMap.get(p.id)||{})})));
    }
   } catch(e:any){setToast(e.message||"Unable to load backend data");}
 };
 useEffect(()=>{api.refresh().then(r=>{setToken(r.accessToken);setCurrentUser(r.user);setCurrentJudgeId(r.user.role==="judge"?r.user.id:"");setActiveRole(r.user.role);navigate(r.user.role==="organizer"?"/organizer":r.user.role==="judge"?"/judge/dashboard":"/participant/dashboard");refresh();}).catch(()=>setToken(null));},[]);
 useEffect(()=>{document.documentElement.classList.toggle("dark",isDarkMode);document.body.classList.toggle("dark",isDarkMode);localStorage.setItem("agamotto_theme",isDarkMode?"dark":"light")},[isDarkMode]);

 const login=(email:string,passwordOrRole?:string|UserRole)=>{
   const password=typeof passwordOrRole==="string" && !["organizer","judge","participant"].includes(passwordOrRole)?passwordOrRole:"LocalDemo123!";
   api.login(email,password).then(r=>{setToken(r.accessToken);setCurrentUser(r.user);setCurrentJudgeId(r.user.role==="judge"?r.user.id:"");setActiveRole(r.user.role);navigate(r.user.role==="organizer"?"/organizer":r.user.role==="judge"?"/judge/dashboard":"/participant/dashboard");setToast("Signed in successfully.");setTimeout(()=>refresh(),0)}).catch(e=>setToast(e.message));
 };
 const register=(data:any)=>{
   api.register(data).then(r=>{setToken(r.accessToken);setCurrentUser(r.user);setCurrentJudgeId(r.user.role==="judge"?r.user.id:"");setActiveRole(r.user.role);navigate(r.user.role==="organizer"?"/organizer":r.user.role==="judge"?"/judge/dashboard":"/participant/dashboard");setToast(`Account created successfully. Welcome, ${r.user.name}`);refresh()}).catch(e=>setToast(e.message));
 };
 const logout=()=>{api.logout().catch(()=>{});setToken(null);setCurrentUser(null);setActiveRole("guest");setEvents([]);setProjects([]);setTeams([]);navigate("/");setToast("Signed out successfully.")};

 const activeEvent=useMemo(()=>events.find(e=>e.id===activeEventId)||events[0]||emptyEvent,[events,activeEventId]);
 const participantTeam=teams[0]||{id:"",eventId:activeEventId,name:"No team",inviteCode:"",track:"General",members:[]};

 const assignJudge=async(projectId:string,judgeId:string)=>{
   try {
     await api.assign(projectId,judgeId);
     setToast("Judge assigned.");
     await refresh(activeEventId);
     return {success:true};
   } catch(e:any) {
     setToast(e.message);
     return {success:false,reason:e.message};
   }
 };
 const removeJudge=(projectId:string,judgeId:string)=>{api.unassign(projectId,judgeId).then(()=>refresh(activeEventId)).catch(e=>setToast(e.message))};
 const autoAssignJudges=(eventId=activeEventId)=>{api.autoAssign(eventId).then(r=>{setToast(`Auto-assigned ${r.created} judge pairings.`);refresh(eventId)}).catch(e=>setToast(e.message))};
 const saveEvaluation=(projectId:string,_judgeId:string,scores:any,justifications:any,status:any)=>{api.saveReview({projectId,scores,justifications,status}).then(()=>{setToast(status==="draft"?"Review draft saved.":`Review ${status}.`);refresh(activeEventId)}).catch(e=>setToast(e.message))};
 const reopenEvaluation=(projectId:string,judgeId:string,reason:string)=>{api.reopenReview({projectId,judgeId,reason}).then(()=>{setToast("Review reopened.");refresh(activeEventId)}).catch(e=>setToast(e.message))};
 const updateRubric=(eventId:string,rubric:RubricCriterion[],tieBreakOrder?:string[])=>{api.updateEvent(eventId,{rubric,...(tieBreakOrder?{tieBreakOrder}: {})}).then(e=>{setEvents(v=>v.map(x=>x.id===eventId?e:x));setToast("Rubric updated.")}).catch(e=>setToast(e.message))};
 const createEvent=async(data:any)=>{
   try {
     const e=await api.createEvent(data);
     setEvents(v=>[e,...v]);
     setActiveEventId(e.id);
     setToast(`Event "${e.title}" created.`);
     return e.id;
   } catch(e:any) {
     setToast(e.message);
     throw e;
   }
 };
 const updateEvent=(id:string,data:any)=>{api.updateEvent(id,data).then(e=>{setEvents(v=>v.map(x=>x.id===id?e:x));setToast("Event updated.")}).catch(e=>setToast(e.message))};
 const submitProject=async(data:any)=>{
   try {
     const teamId=data.teamId||participantTeam.id;
     if(!teamId) throw new Error("Create or join a team before submitting a project.");
     const p=await api.createProject(activeEventId,{...data,teamId});
     setProjects(v=>[mapProject(p),...v]);
     setToast("Submission saved successfully.");
     await refresh(activeEventId);
     return true;
   } catch(e:any) {
     setToast(e.message);
     return false;
   }
 };
 const updateProjectSubmission=async(id:string,data:any)=>{
   try {
     await api.updateProject(id,{...data,summary:"Participant submission update"});
     setToast("Submission saved successfully.");
     await refresh(activeEventId);
     return true;
   } catch(e:any) {
     setToast(e.message);
     return false;
   }
 };
 const joinEventWithCode=async(code:string,accessCode?:string)=>{
   try {
     await api.joinByCode(code,accessCode);
     const es=await api.events();
     setEvents(es);
     const e=es.find(x=>x.eventCode.toUpperCase()===code.trim().toUpperCase());
     if(e){setActiveEventId(e.id);setToast(`Joined ${e.title}.`);await refresh(e.id);}
     else{setToast("Event joined successfully.");}
     return true;
   } catch(err:any) {
     setToast(err.message);
     return false;
   }
 };
 const createTeam=(name:string,track:string,eventId:string)=>{api.createTeam(eventId,{name,track}).then(t=>{setTeams(v=>[t,...v]);setToast(`Team "${name}" created.`)}).catch(e=>setToast(e.message))};
 const updateTeamMembers=(teamId:string,members:any[])=>{const additions=members.filter(m=>!teams.find(t=>t.id===teamId)?.members.some(x=>x.email===m.email)); Promise.all(additions.map(m=>api.addMember(teamId,{userId:m.id||currentUser?.id,role:m.role,isLeader:m.isLeader}))).then(()=>refresh(activeEventId)).catch(e=>setToast(e.message))};
 const approveParticipant=(id:string)=>{api.decideParticipant(activeEventId,id,"approved").then(()=>{setToast("Participant approved.");refresh(activeEventId)}).catch(e=>setToast(e.message))};
 const recalculateScores=(method:any="z_score",eventId=activeEventId)=>{api.updateEvent(eventId,{normalizationMethod:method}).then(()=>api.calculate(eventId,{override:false,reason:null})).then(()=>{setToast(`Scores recalculated using ${String(method).toUpperCase()}.`);refresh(eventId)}).catch(e=>setToast(e.message))};
 const toggleIdentityReveal=()=>{setToast("Blind judging identity protection is enforced server-side.");};

 return <AppContext.Provider value={{currentUser,activeRole,currentPath,currentView:currentPath,isDarkMode,events,activeEventId,activeEvent,eventConfig:activeEvent,projects,judges,participants,teams,participantTeam,auditLogs,activeProjectId,activeReviewId,toastMessage,currentJudgeId,toggleDarkMode:()=>setIsDarkMode(v=>!v),navigate,navigateTo:navigate,login,register,logout,setToast:setToastMessage,setActiveEventId:(id)=>{setActiveEventId(id);refresh(id)},setActiveProjectId,setActiveReviewId,setCurrentJudgeId,toggleIdentityReveal,assignJudge,removeJudge,autoAssignJudges,saveEvaluation,reopenEvaluation,updateRubric,createEvent,updateEvent,submitProject,updateProjectSubmission,joinEventWithCode,createTeam,updateTeamMembers,approveParticipant,recalculateScores}}>{children}</AppContext.Provider>
};
export const useApp=()=>{const c=useContext(AppContext);if(!c)throw new Error("useApp must be used within AppProvider");return c};
