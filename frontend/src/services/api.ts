export type GenerationInput = {
  resume_text: string;
  job_description: string;
  role?: string;
  industry?: string;
  company?: string;
  year?: number;
  model?: string;
};

export type TailoredResumeInput = GenerationInput & {
  max_gap_skills?: number;
  include_cover_letter?: boolean;
};

export type JobContext = {
  role: string;
  industry?: string | null;
  company?: string | null;
  year?: number | null;
  confidence: number;
};

export type SkillGap = {
  skill: string;
  why_it_matters: string;
  additional_notes: string;
  free_resources: string[];
};

export type SkillProject = {
  title: string;
  one_day_scope: string;
  skills_covered: string[];
  tasks: string[];
  acceptance_criteria: string[];
  resume_bullet: string;
  resume_bullets: string[];
};

export type ResumeVariant = {
  content: string;
  stage: string;
  variant: string;
};

export type TailoredResumeResponse = {
  context: JobContext;
  skill_gap_summary: string;
  skill_gaps: SkillGap[];
  skill_projects: SkillProject[];
  cover_letter: string;
  truthful_rewrite: ResumeVariant;
  project_enhanced_rewrite: ResumeVariant;
  truthful_ats: ResumeVariant;
  project_enhanced_ats: ResumeVariant;
  default_final_variant: string;
  model: string;
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000/api";

async function postJson<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadResumeFile(file: File): Promise<{ resume_text: string; source_filename?: string }> {
  const data = new FormData();
  data.append("file", file);
  const res = await fetch(`${API_BASE}/resume/upload`, { method: "POST", body: data });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Upload failed: ${res.status}`);
  }
  return res.json();
}

export async function fixUploadedPdfLayout(file: File): Promise<void> {
  const data = new FormData();
  data.append("file", file);

  const res = await fetch(`${API_BASE}/resume/fix-pdf-layout`, { method: "POST", body: data });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `PDF fix failed: ${res.status}`);
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${file.name.replace(/\.pdf$/i, "")}_fixed.pdf`;
  anchor.click();
  window.URL.revokeObjectURL(url);
}

export async function generateRewrite(input: GenerationInput): Promise<string> {
  const data = await postJson<{ content: string }>("/generate/rewrite", input);
  return data.content;
}

export async function generateAts(input: GenerationInput): Promise<string> {
  const data = await postJson<{ content: string }>("/generate/ats", input);
  return data.content;
}

export async function generateTailoredResume(input: TailoredResumeInput): Promise<TailoredResumeResponse> {
  return postJson<TailoredResumeResponse>("/generate/tailored-resume", input);
}

export async function generateCoverLetter(input: GenerationInput): Promise<string> {
  const data = await postJson<{ content: string }>("/generate/cover-letter", input);
  return data.content;
}

export async function generateSkillGap(input: GenerationInput): Promise<{ summary: string; gaps: Array<{ skill: string; why_it_matters: string; additional_notes: string; free_resources: string[] }> }> {
  return postJson("/generate/skill-gap", input);
}

export async function generateSkillProjects(role: string, skills: string[]): Promise<{ projects: Array<{ title: string; one_day_scope: string; skills_covered: string[]; tasks: string[]; acceptance_criteria: string[]; resume_bullet: string; resume_bullets: string[] }> }> {
  return postJson("/generate/skill-projects", { role, skills });
}

export async function extractJobContext(jobDescription: string): Promise<JobContext> {
  return postJson<JobContext>("/extract/job-context", { job_description: jobDescription });
}

export async function downloadPdf(title: string, content: string, documentType: "resume" | "cover-letter" = "resume"): Promise<void> {
  const endpoint = documentType === "cover-letter" ? "/export/pdf/cover-letter" : "/export/pdf/resume";
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, content }),
  });
  if (!res.ok) {
    throw new Error("PDF export failed");
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${title.replace(/\s+/g, "_")}.pdf`;
  anchor.click();
  window.URL.revokeObjectURL(url);
}
