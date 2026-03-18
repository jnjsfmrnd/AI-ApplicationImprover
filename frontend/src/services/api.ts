export type GenerationInput = {
  resume_text: string;
  job_description: string;
  role: string;
  industry: string;
  company?: string;
  year?: number;
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000/api";

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
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

export async function generateRewrite(input: GenerationInput): Promise<string> {
  const data = await postJson<{ content: string }>("/generate/rewrite", input);
  return data.content;
}

export async function generateAts(input: GenerationInput): Promise<string> {
  const data = await postJson<{ content: string }>("/generate/ats", input);
  return data.content;
}

export async function generateCoverLetter(input: GenerationInput): Promise<string> {
  const data = await postJson<{ content: string }>("/generate/cover-letter", input);
  return data.content;
}

export async function generateSkillGap(input: GenerationInput): Promise<{ summary: string; gaps: Array<{ skill: string; why_it_matters: string; free_resources: string[] }> }> {
  return postJson("/generate/skill-gap", input);
}

export async function generateSkillProjects(role: string, skills: string[]): Promise<{ projects: Array<{ title: string; one_day_scope: string; tasks: string[]; acceptance_criteria: string[]; resume_bullet: string }> }> {
  return postJson("/generate/skill-projects", { role, skills });
}

export async function downloadPdf(title: string, content: string): Promise<void> {
  const res = await fetch(`${API_BASE}/export/pdf`, {
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
