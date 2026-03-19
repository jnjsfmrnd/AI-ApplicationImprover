import { ChangeEvent, useState } from "react";
import {
  downloadPdf,
  generateTailoredResume,
  SkillGap,
  SkillProject,
  TailoredResumeResponse,
  uploadResumeFile,
} from "./services/api";

type FinalVariantKey = "truthful_ats" | "project_enhanced_ats";

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

  const [truthfulRewriteOutput, setTruthfulRewriteOutput] = useState("");
  const [projectRewriteOutput, setProjectRewriteOutput] = useState("");
  const [truthfulAtsOutput, setTruthfulAtsOutput] = useState("");
  const [projectAtsOutput, setProjectAtsOutput] = useState("");
  const [skillSummary, setSkillSummary] = useState("");
  const [skillGaps, setSkillGaps] = useState<SkillGap[]>([]);
  const [skillProjects, setSkillProjects] = useState<SkillProject[]>([]);
  const [selectedFinalVariant, setSelectedFinalVariant] = useState<FinalVariantKey>("truthful_ats");

  const finalResumeContent = selectedFinalVariant === "project_enhanced_ats" ? projectAtsOutput : truthfulAtsOutput;
  const hasTailoredOutput = Boolean(truthfulAtsOutput || projectAtsOutput || truthfulRewriteOutput || projectRewriteOutput);

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
      setTruthfulRewriteOutput(result.truthful_rewrite.content);
      setProjectRewriteOutput(result.project_enhanced_rewrite.content);
      setTruthfulAtsOutput(result.truthful_ats.content);
      setProjectAtsOutput(result.project_enhanced_ats.content);
      setSelectedFinalVariant(
        result.default_final_variant === "project_enhanced_ats" ? "project_enhanced_ats" : "truthful_ats"
      );
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
      </section>

      <section className="card">
        <h2>Final ATS Resume</h2>
        <div className="actions">
          <button
            type="button"
            className={selectedFinalVariant === "truthful_ats" ? "button-secondary is-active" : "button-secondary"}
            onClick={() => setSelectedFinalVariant("truthful_ats")}
            disabled={!truthfulAtsOutput}
          >
            Truthful ATS
          </button>
          <button
            type="button"
            className={selectedFinalVariant === "project_enhanced_ats" ? "button-secondary is-active" : "button-secondary"}
            onClick={() => setSelectedFinalVariant("project_enhanced_ats")}
            disabled={!projectAtsOutput}
          >
            Project-Enhanced ATS
          </button>
        </div>
        <p className="status">Primary preview is ATS-safe. Switch variants depending on how aggressive you want to be.</p>
        <textarea readOnly value={finalResumeContent} rows={16} />
        <div className="actions">
          <button disabled={!finalResumeContent} onClick={() => downloadPdf("Tailored_Resume", finalResumeContent)}>
            Download Selected PDF
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Recruiter Rewrite Variants</h2>
        <label>
          Truthful Rewrite
          <textarea readOnly value={truthfulRewriteOutput} rows={12} />
        </label>
        <label>
          Project-Enhanced Rewrite
          <textarea readOnly value={projectRewriteOutput} rows={12} />
        </label>
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
        <h2>Gap-Covering Project Plan</h2>
        {!skillProjects.length && <p className="status">Run the pipeline to generate one strong project that covers the most important gaps from the pasted JD.</p>}
        {skillProjects.map((project) => (
          <div key={project.title} className="project-item">
            <h3>{project.title}</h3>
            <p>{project.one_day_scope}</p>
            <p>
              <strong>Skills Covered:</strong> {project.skills_covered.join(", ")}
            </p>
            <strong>Resume Bullets</strong>
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
