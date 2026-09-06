import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { Button, Card, Spinner, StatusBadge } from "../../components/ui";
import { api } from "../../lib/api-client";
import type { DocumentOut } from "../../lib/types";

interface Uploading {
  filename: string;
  progress: number;
  stage: string;
  status: string;
}

/** Poll a job until it reaches a terminal state, reporting progress. */
async function watchJob(
  jobId: string,
  onProgress: (stage: string, progress: number, status: string) => void,
): Promise<void> {
  for (;;) {
    const job = await api.getJob(jobId);
    onProgress(job.stage, job.progress, job.status);
    if (job.status === "completed" || job.status === "failed") return;
    await new Promise((r) => setTimeout(r, 700));
  }
}

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const [uploads, setUploads] = useState<Record<string, Uploading>>({});

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: api.listDocuments,
  });

  async function handleFiles(files: FileList | null) {
    if (!files) return;
    for (const file of Array.from(files)) {
      const key = `${file.name}-${Date.now()}`;
      setUploads((u) => ({
        ...u,
        [key]: { filename: file.name, progress: 0, stage: "uploading", status: "queued" },
      }));
      try {
        const res = await api.uploadDocument(file);
        if (res.job) {
          await watchJob(res.job.id, (stage, progress, status) =>
            setUploads((u) => ({ ...u, [key]: { ...u[key], stage, progress, status } })),
          );
        }
      } finally {
        setUploads((u) => {
          const next = { ...u };
          delete next[key];
          return next;
        });
        queryClient.invalidateQueries({ queryKey: ["documents"] });
      }
    }
  }

  async function remove(doc: DocumentOut) {
    await api.deleteDocument(doc.id);
    queryClient.invalidateQueries({ queryKey: ["documents"] });
  }

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-800">Documents</h1>
        <input
          ref={fileInput}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <Button onClick={() => fileInput.current?.click()}>Upload</Button>
      </div>

      {Object.entries(uploads).length > 0 && (
        <Card className="mb-4 p-4">
          <p className="mb-2 text-sm font-medium text-slate-600">Ingesting…</p>
          {Object.entries(uploads).map(([key, u]) => (
            <div key={key} className="mb-2">
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-slate-700">{u.filename}</span>
                <span className="text-slate-400">{u.stage}</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-100">
                <div
                  className="h-2 rounded-full bg-brand-500 transition-all"
                  style={{ width: `${u.progress}%` }}
                />
              </div>
            </div>
          ))}
        </Card>
      )}

      <Card>
        {isLoading ? (
          <div className="flex items-center gap-2 p-6 text-sm text-slate-500">
            <Spinner /> Loading…
          </div>
        ) : documents.length === 0 ? (
          <p className="p-6 text-sm text-slate-500">No documents yet. Upload to get started.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {documents.map((doc) => (
              <li key={doc.id} className="flex items-center justify-between px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-800">{doc.filename}</p>
                  <p className="text-xs text-slate-400">{doc.mime_type}</p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={doc.status} />
                  <Button variant="danger" onClick={() => remove(doc)}>
                    Delete
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
