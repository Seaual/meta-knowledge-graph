// frontend/src/components/DragUploadZone.tsx
import { useState, useCallback, useRef } from "react";
import { Upload, Loader2 } from "lucide-react";
import { papersApi } from "../lib/api";
import { useTranslation } from "../i18n";

interface UploadedPaper {
  doi: string;
  title: string;
}

interface DragUploadZoneProps {
  onUploadSuccess: (papers: UploadedPaper[]) => void;
  onUploadError: (error: string) => void;
}

export default function DragUploadZone({
  onUploadSuccess,
  onUploadError,
}: DragUploadZoneProps) {
  const { t } = useTranslation();
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const dragCounterRef = useRef(0);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current++;
    if (e.dataTransfer.types.includes("Files")) {
      setIsDragging(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      dragCounterRef.current = 0;

      const files = Array.from(e.dataTransfer.files).filter(
        (file) => file.type === "application/pdf"
      );

      if (files.length === 0) {
        onUploadError(t.common.uploadPdfOnly);
        return;
      }

      setIsUploading(true);
      setUploadProgress(0);

      const uploadedPapers: UploadedPaper[] = [];
      const totalFiles = files.length;

      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        try {
          const res = await papersApi.upload(file);
          if (res.data?.success && res.data?.doi) {
            uploadedPapers.push({
              doi: res.data.doi,
              title: res.data.title || file.name,
            });
          }
        } catch (err: any) {
          console.error(`Upload failed for ${file.name}:`, err);
        }
        setUploadProgress(Math.round(((i + 1) / totalFiles) * 100));
      }

      setIsUploading(false);
      setUploadProgress(0);

      if (uploadedPapers.length > 0) {
        onUploadSuccess(uploadedPapers);
      } else {
        onUploadError(t.common.uploadFailed);
      }
    },
    [onUploadSuccess, onUploadError]
  );

  if (!isDragging && !isUploading) {
    return null;
  }

  return (
    <div
      className="absolute inset-0 z-50 flex items-center justify-center"
      style={{
        background: "rgba(250, 248, 245, 0.95)",
        backdropFilter: "blur(4px)",
      }}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <div
        className="w-full max-w-md mx-4 p-8 rounded-2xl text-center"
        style={{
          border: "2px dashed rgba(184, 134, 11, 0.4)",
          background: "rgba(255, 254, 249, 0.8)",
        }}
      >
        {isUploading ? (
          <>
            <Loader2
              className="w-12 h-12 mx-auto mb-4 animate-spin"
              style={{ color: "var(--color-amber)" }}
            />
            <p
              className="font-body text-sm"
              style={{ color: "var(--color-sepia)" }}
            >
              {t.common.uploading} {uploadProgress}%
            </p>
          </>
        ) : (
          <>
            <Upload
              className="w-12 h-12 mx-auto mb-4"
              style={{ color: "var(--color-amber)" }}
            />
            <p
              className="font-display text-lg mb-2"
              style={{ color: "var(--color-sepia)" }}
            >
              {t.common.dragDropPdf}
            </p>
            <p
              className="font-body text-sm"
              style={{ color: "var(--color-muted)" }}
            >
              {t.common.multiPdfSupport}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
