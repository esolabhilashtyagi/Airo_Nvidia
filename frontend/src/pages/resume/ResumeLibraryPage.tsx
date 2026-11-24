import { useCallback, useEffect, useRef, useState } from 'react';
import { FileText, UploadCloud, RefreshCw, ArrowUpRight, CircleAlert } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { resumesApi } from '../../api/resumes';
import { EmptyState } from '../../components/common/EmptyState';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { StatusBadge } from '../../components/common/StatusBadge';
import { RequiredLabel } from '../../components/common/RequiredMark';
import type { Resume } from '../../types';

const MAX_FILE_SIZE = 15 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = ['.pdf', '.docx', '.png', '.jpg', '.jpeg'];

function formatBytes(size: number) {
  return size < 1024 * 1024 ? `${Math.max(1, Math.round(size / 1024))} KB` : `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function ResumeLibraryPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const loadResumes = useCallback(async (preserveError = false) => {
    setLoading(true);
    if (!preserveError) setError(null);
    try {
      setResumes(await resumesApi.listResumes());
    } catch (err) {
      if (!preserveError) setError(err instanceof Error ? err.message : 'Could not load your resumes.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void loadResumes(); }, [loadResumes]);

  const uploadFile = async (file?: File) => {
    if (!file) return;
    const extension = `.${file.name.split('.').pop()?.toLowerCase() || ''}`;
    if (!ACCEPTED_EXTENSIONS.includes(extension)) {
      setError('Choose a PDF, DOCX, PNG, JPG, or JPEG file. Legacy .doc files are not supported.');
      return;
    }
    if (file.size === 0) { setError('The selected file is empty.'); return; }
    if (file.size > MAX_FILE_SIZE) { setError('The file exceeds the 15 MB upload limit.'); return; }
    setUploading(true);
    setProgress(0);
    setError(null);
    try {
      const resume = await resumesApi.uploadResume(file, setProgress);
      navigate(`/resume/${resume.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed. Try again.';
      await loadResumes(true);
      setError(message);
    } finally {
      setUploading(false);
      setProgress(0);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-violet-700">Resume intelligence</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">My resumes</h1>
          <p className="mt-1 text-sm text-slate-500">Upload a resume to extract its contents and request role-aware feedback.</p>
        </div>
        <button type="button" onClick={() => void loadResumes()} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60">
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {error && <div role="alert" className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800"><CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}

      <input ref={inputRef} type="file" accept=".pdf,.docx,.png,.jpg,.jpeg" className="hidden" onChange={(event) => void uploadFile(event.target.files?.[0])} />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          const file = event.dataTransfer.files.item(0)
            ?? Array.from(event.dataTransfer.items).find((item) => item.kind === 'file')?.getAsFile();
          if (!file) { setError('The dropped item did not include a readable file. Choose the file with the upload control.'); return; }
          void uploadFile(file);
        }}
        disabled={uploading}
        className={`w-full rounded-xl border-2 border-dashed p-6 text-left transition ${dragging ? 'border-violet-500 bg-violet-50' : 'border-slate-300 bg-white hover:border-violet-400 hover:bg-violet-50/30'} disabled:cursor-wait`}
      >
        <span className="flex items-center gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gray-100 text-gray-500"><UploadCloud className="h-6 w-6" /></span>
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-semibold text-slate-900"><RequiredLabel>Resume file</RequiredLabel> · {uploading ? `Uploading resume (${progress}%)` : 'Drop a resume here or browse files'}</span>
            <span className="mt-1 block text-xs text-slate-500">PDF, DOCX, PNG, JPG, or JPEG · up to 15 MB · file contents are checked on upload</span>
            {uploading && <span className="mt-3 block h-1.5 overflow-hidden rounded-full bg-slate-200"><span className="block h-full bg-violet-600 transition-all" style={{ width: `${progress}%` }} /></span>}
          </span>
        </span>
      </button>

      <section aria-labelledby="resume-list-title" className="space-y-3">
        <h2 id="resume-list-title" className="text-base font-semibold text-slate-900">Resume history</h2>
        {loading ? <LoadingSpinner message="Loading your resume library..." /> : resumes.length === 0 ? (
          <EmptyState icon={FileText} iconClassName="!bg-gray-100 !text-gray-500" title="No resumes uploaded yet" description="Upload a PDF, DOCX, or image to begin. Extracted text will remain available if AI analysis is not configured." actionText="Choose a resume" onActionClick={() => inputRef.current?.click()} />
        ) : resumes.map((resume) => (
          <article key={resume.id} className="flex flex-wrap items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600"><FileText className="h-5 w-5" /></div>
            <div className="min-w-0 flex-1">
              <Link to={`/resume/${resume.id}`} className="truncate font-semibold text-slate-900 hover:text-violet-700">{resume.file_name}</Link>
              <p className="mt-1 text-xs text-slate-500">{formatBytes(resume.file_size_bytes)} · Uploaded {new Date(resume.created_at).toLocaleDateString()}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={resume.parsing_status} />
              <StatusBadge status={resume.analysis_status} />
              <Link to={`/resume/${resume.id}`} aria-label={`Open ${resume.file_name}`} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-violet-700"><ArrowUpRight className="h-4 w-4" /></Link>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
