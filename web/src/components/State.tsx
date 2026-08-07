import { AlertTriangle, Database, LoaderCircle } from "lucide-react";

export function LoadingState({ label = "Reading live sources..." }: { label?: string }) { return <div className="page-state"><LoaderCircle className="spin" size={24}/><span>{label}</span></div>; }
export function EmptyState({ title, detail }: { title: string; detail: string }) { return <div className="page-state"><Database size={24}/><strong>{title}</strong><span>{detail}</span></div>; }
export function ErrorState({ detail, retry }: { detail: string; retry: () => void }) { return <div className="page-state error-state"><AlertTriangle size={24}/><strong>Live source unavailable</strong><span>{detail}</span><button className="outline-btn" onClick={retry}>Retry</button></div>; }
