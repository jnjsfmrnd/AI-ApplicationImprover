import { ChangeEvent, useMemo, useState } from "react";
import {
  GenerationInput,
  downloadPdf,
  generateAts,
  generateCoverLetter,
  generateRewrite,
  generateSkillGap,
  generateSkillProjects,
  uploadResumeFile,
} from "./services/api";

type SkillGap = { skill: string; why_it_matters: string; free_resources: string[] };
type SkillProject = {
  title: string;
  one_day_scope: string;
  tasks: string[];
  acceptance_criteria: string[];
  resume_bullet: string;
};

export default function App() {
  const [resumeText, setResumeText] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [role, setRole] = useState("AI Engineer");
  const [industry, setIndustry] = useState("Technology");
  const [company, setCompany] = useState("Target Company");
  const [year, setYear] = useState<number>(new Date().getFullYear());
  const [status, setStatus] = useState("Ready");

  const [rewriteOutput, setRewriteOutput] = useState("");
  const [atsOutput, setAtsOutput] = useState("");
  const [coverLetterOutput, setCoverLetterOutput] = useState("");
  const [skillSummary, setSkillSummary] = useState("");
  const [skillGaps, setSkillGaps] = useState<SkillGap[]>([]);
  const [skillProjects, setSkillProjects] = useState<SkillProject[]>([]);

  const input: GenerationInput = useMemo(
    () => ({
      resume_text: resumeText,
      job_description: jobDescription,
      role,
      industry,
      company,
      year,
    }),
    [resumeText, jobDescription, role, industry, company, year]
  );

  async function onUpload(file: File | null) {
    if (!file) return;
    try {
      setStatus("Uploading resume...");
      const uploaded = await uploadResumeFile(file);
      setResumeText(uploaded.resume_text);
      setStatus(`Uploaded ${uploaded.source_filename ?? "resume"}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Upload failed");
    }
  }

  const handleResumeChange = (e: ChangeEvent<HTMLTextAreaElement>) => setResumeText(e.target.value);
  const handleJobDescriptionChange = (e: ChangeEvent<HTMLTextAreaElement>) => setJobDescription(e.target.value);
  const handleRoleChange = (e: ChangeEvent<HTMLInputElement>) => setRole(e.target.value);
  const handleIndustryChange = (e: ChangeEvent<HTMLInputElement>) => setIndustry(e.target.value);
  const handleCompanyChange = (e: ChangeEvent<HTMLInputElement>) => setCompany(e.target.value);
  const handleYearChange = (e: ChangeEvent<HTMLInputElement>) =>
    setYear(Number(e.target.value) || new Date().getFullYear());

  async function runPipeline() {
    if (resumeText.length < 20 || jobDescription.length < 20) {
      setStatus("Resume and JD need more detail before generation.");
      return;
    }

    try {
      setStatus("Generating recruiter rewrite...");
      const rewrite = await generateRewrite(input);
      setRewriteOutput(rewrite);

      setStatus("Optimizing for ATS...");
      const ats = await generateAts(input);
      setAtsOutput(ats);

      setStatus("Generating cover letter...");
      const cover = await generateCoverLetter(input);
      setCoverLetterOutput(cover);

      setStatus("Running skill gap analysis...");
      const skillGap = await generateSkillGap(input);
      setSkillSummary(skillGap.summary);
      setSkillGaps(skillGap.gaps);

      if (skillGap.gaps.length > 0) {
        setStatus("Generating same-day skill projects...");
        const projects = await generateSkillProjects(
          role,
          skillGap.gaps.map((item) => item.skill)
        );
        setSkillProjects(projects.projects);
      }

      setStatus("Generation complete.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Generation failed");
    }
  }

  return (
    <div className="container">
      <h1>AI Resume Tailor + Agent Skill Builder</h1>
      <p className="status">Status: {status}</p>

      <section className="card">
        <h2>Input</h2>
        <label>
          Upload Resume (.txt for current version)
          <input
            type="file"
            accept=".txt,.pdf,.docx"
            onChange={(e: ChangeEvent<HTMLInputElement>) => onUpload(e.target.files?.[0] ?? null)}
          />
        </label>

        <label>
          Resume Text
          <textarea value={resumeText} onChange={handleResumeChange} rows={10} />
        </label>

        <label>
          Job Description
          <textarea value={jobDescription} onChange={handleJobDescriptionChange} rows={10} />
        </label>

        <div className="row">
          <label>
            Role
            <input value={role} onChange={handleRoleChange} />
          </label>
          <label>
            Industry
            <input value={industry} onChange={handleIndustryChange} />
          </label>
          <label>
            Company
            <input value={company} onChange={handleCompanyChange} />
          </label>
          <label>
            Year
            <input type="number" value={year} onChange={handleYearChange} />
          </label>
        </div>

        <button onClick={runPipeline}>Generate Outputs</button>
      </section>

      <section className="card">
        <h2>New Resume Preview</h2>
        <textarea readOnly value={rewriteOutput || atsOutput} rows={14} />
        <div className="actions">
          <button disabled={!rewriteOutput && !atsOutput} onClick={() => downloadPdf("Tailored Resume", rewriteOutput || atsOutput)}>
            Download Resume PDF
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Cover Letter Preview</h2>
        <textarea readOnly value={coverLetterOutput} rows={14} />
        <div className="actions">
          <button disabled={!coverLetterOutput} onClick={() => downloadPdf("Cover Letter", coverLetterOutput)}>
            Download Cover Letter PDF
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Skill Gap Analysis</h2>
        <pre>{skillSummary}</pre>
        {skillGaps.map((item) => (
          <div key={item.skill} className="gap-item">
            <strong>{item.skill}</strong>
            <p>{item.why_it_matters}</p>
            <ul>
              {item.free_resources.map((resource) => (
                <li key={resource}>{resource}</li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      <section className="card">
        <h2>Same-Day Skill Projects</h2>
        {skillProjects.map((project) => (
          <div key={project.title} className="project-item">
            <h3>{project.title}</h3>
            <p>{project.one_day_scope}</p>
            <p>
              <strong>Resume Bullet:</strong> {project.resume_bullet}
            </p>
          </div>
        ))}
      </section>
    </div>
  );
}
