import { ChangeEvent, useEffect, useRef, useState } from "react";
import {
  downloadPdf,
  generateTailoredResume,
  SkillGap,
  SkillProject,
  TailoredResumeResponse,
  uploadResumeFile,
} from "./services/api";

export default function App() {
  const [resumeText, setResumeText] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [inferredRole, setInferredRole] = useState("Target Role");
  const [inferredIndustry, setInferredIndustry] = useState<string>("");
  const [inferredYear, setInferredYear] = useState<number | undefined>(undefined);
  const [company, setCompany] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [status, setStatus] = useState("Ready");
  const [modelName, setModelName] = useState("");

  const [truthfulAtsOutput, setTruthfulAtsOutput] = useState("");
  const [coverLetterOutput, setCoverLetterOutput] = useState("");
  const [skillSummary, setSkillSummary] = useState("");
  const [skillGaps, setSkillGaps] = useState<SkillGap[]>([]);
  const [skillProjects, setSkillProjects] = useState<SkillProject[]>([]);

  const [progress, setProgress] = useState(-1);
  const progressTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (isGenerating) {
      setProgress(0);
      const TICK_MS = 150;
      const increment = 95 / (65000 / TICK_MS);
      progressTimerRef.current = setInterval(() => {
        setProgress((p) => Math.min(p + increment, 95));
      }, TICK_MS);
      return () => {
        if (progressTimerRef.current !== null) {
          clearInterval(progressTimerRef.current);
          progressTimerRef.current = null;
        }
      };
    } else {
      setProgress((p) => (p >= 0 ? 100 : p));
      const t = setTimeout(() => setProgress(-1), 900);
      return () => clearTimeout(t);
    }
  }, [isGenerating]);

  const hasTailoredOutput = Boolean(truthfulAtsOutput);

  const getApplicantName = (resume: string): string => {
    const firstLine = resume
      .split(/\r?\n/)
      .map((line) => line.trim())
      .find((line) => line.length > 0);

    if (!firstLine) {
      return "Applicant";
    }

    const withoutPrefix = firstLine.replace(/^name\s*:\s*/i, "").trim();
    const cleaned = withoutPrefix.replace(/[^a-zA-Z\s.'-]/g, "").trim();
    return cleaned || "Applicant";
  };

  const statusTone = (() => {
    const normalized = status.toLowerCase();
    if (isGenerating || normalized.includes("generating") || normalized.includes("analyzing") || normalized.includes("running")) {
      return "working";
    }
    if (normalized.includes("complete") || normalized.includes("uploaded")) {
      return "success";
    }
    if (normalized.includes("failed") || normalized.includes("error")) {
      return "error";
    }
    return "info";
  })();

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
  const handleCompanyChange = (e: ChangeEvent<HTMLInputElement>) => setCompany(e.target.value);

  async function runPipeline() {
    if (resumeText.length < 20 || jobDescription.length < 20) {
      setStatus("Resume and JD need more detail before generation.");
      return;
    }

    if (isGenerating) {
      return;
    }

    setIsGenerating(true);
    try {
      setStatus("Running tailored resume pipeline...");
      const typedCompany = company.trim();
      const pipelineInput = {
        resume_text: resumeText,
        job_description: jobDescription,
        role: inferredRole !== "Target Role" ? inferredRole : undefined,
        industry: inferredIndustry || undefined,
        company: typedCompany || undefined,
        year: inferredYear,
        max_gap_skills: 3,
      };

      const result: TailoredResumeResponse = await generateTailoredResume(pipelineInput);
      setInferredRole(result.context.role);
      setInferredIndustry(result.context.industry ?? "");
      setInferredYear(result.context.year ?? undefined);
      if (!typedCompany && result.context.company) {
        setCompany(result.context.company);
      }
      setModelName(result.model);
      setSkillSummary(result.skill_gap_summary);
      setSkillGaps(result.skill_gaps);
      setSkillProjects(result.skill_projects);
      setCoverLetterOutput(result.cover_letter);
      setTruthfulAtsOutput(result.truthful_ats.content);
      setStatus("Generation complete.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Generation failed");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <div className="container">
      <h1>Resume Tailor + Skill Builder</h1>

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
            Company
            <input value={company} onChange={handleCompanyChange} />
          </label>
        </div>

        <p className="detected-context">
          Detected from JD: {inferredRole}
          {inferredIndustry ? ` • ${inferredIndustry}` : ""}
          {inferredYear ? ` • ${inferredYear}` : ""}
          {modelName ? ` • ${modelName}` : ""}
        </p>

        <button onClick={runPipeline} disabled={isGenerating || resumeText.length < 20 || jobDescription.length < 20}>
          {isGenerating ? "Generating..." : "Generate Tailored Resume"}
        </button>
        <p className={`status-pill status-${statusTone}`}>
          {status}
        </p>
        {progress >= 0 && (
          <div className="progress-bar-wrap">
            <div
              className="progress-bar-fill"
              style={{ width: `${Math.round(progress)}%` }}
            />
          </div>
        )}
      </section>

      <section className="card">
        <h2>Final ATS Resume</h2>
        <p className="status">Truthful ATS-optimized resume — edit freely before downloading.</p>
        <textarea value={truthfulAtsOutput} onChange={(e) => setTruthfulAtsOutput(e.target.value)} rows={16} />
        <div className="actions">
          <button
            disabled={!truthfulAtsOutput}
            onClick={() => downloadPdf(`${getApplicantName(resumeText)}_resume`, truthfulAtsOutput, "resume")}
          >
            Download PDF
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Cover Letter</h2>
        {!coverLetterOutput && <p className="status">Generated alongside the pipeline — tailored to the role and company from the JD.</p>}
        <textarea value={coverLetterOutput} onChange={(e) => setCoverLetterOutput(e.target.value)} rows={14} />
        {coverLetterOutput && (
          <div className="actions">
            <button onClick={() => downloadPdf(`${getApplicantName(resumeText)}_coverletter`, coverLetterOutput, "cover-letter")}>
              Download PDF
            </button>
          </div>
        )}
      </section>

      <section className="card">
        <h2>Skill Gaps & Bridge Project</h2>
        <p className="status">These are honest gaps — use the project below to close them for real, then add the bullets to your resume once built.</p>
        {skillSummary && <pre>{skillSummary}</pre>}
        {skillGaps.map((item) => (
          <div key={item.skill} className="gap-item">
            <strong>{item.skill}</strong>
            <p>{item.why_it_matters}</p>
            {item.additional_notes && <p><strong>Additional notes:</strong> {item.additional_notes}</p>}
            {item.free_resources.length > 0 && (
              <ul>
                {item.free_resources.map((resource) => (
                  <li key={resource}>{resource}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {!skillProjects.length && !skillSummary && (
          <p className="status">Run the pipeline to analyze gaps and generate a bridge project scoped for one day of work.</p>
        )}
        {skillProjects.map((project) => (
          <div key={project.title} className="project-item">
            <h3>{project.title}</h3>
            <p>{project.one_day_scope}</p>
            <p><strong>Skills Covered:</strong> {project.skills_covered.join(", ")}</p>
            <strong>Resume Bullets (add once built)</strong>
            <ul>
              {project.resume_bullets.map((bullet) => (
                <li key={bullet}>{bullet}</li>
              ))}
            </ul>
            <strong>Build Tasks</strong>
            <ul>
              {project.tasks.map((task) => (
                <li key={task}>{task}</li>
              ))}
            </ul>
            <strong>Acceptance Criteria</strong>
            <ul>
              {project.acceptance_criteria.map((criterion) => (
                <li key={criterion}>{criterion}</li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      {!hasTailoredOutput && (
        <section className="card">
          <h2>How This Flow Works</h2>
          <p className="status">The app analyzes the pasted JD first, finds the most important skill gaps for that target role, designs one strong project to cover as many of them as possible, then builds recruiter and ATS variants from that context.</p>
        </section>
      )}
    </div>
  );
}
