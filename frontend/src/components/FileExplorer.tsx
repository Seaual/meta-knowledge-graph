import { useState } from "react";
import { FileText } from "lucide-react";
import { useAgentStore } from "../stores/agentStore";

export default function FileExplorer() {
  const files = useAgentStore((s) => s.virtualFiles);
  const [selected, setSelected] = useState<string | null>(null);

  const selectedFile = files.find((f) => f.path === selected);

  if (files.length === 0) return null;

  return (
    <div className="p-4 border-t border-[#E8E4DC]">
      <h3 className="font-display text-sm font-medium mb-3 text-[#5a3e28]">
        工作区文件
      </h3>
      <div className="space-y-1">
        {files.map((file) => (
          <button
            key={file.path}
            onClick={() => setSelected(file.path)}
            className={`w-full flex items-center gap-2 px-2 py-1 rounded text-xs ${
              selected === file.path ? "bg-[#E8E4DC]" : "hover:bg-[#F5F0E8]"
            }`}
          >
            <FileText className="w-3 h-3 text-[#8b4513]" />
            <span className="truncate">{file.path.replace("/workspace/", "")}</span>
          </button>
        ))}
      </div>
      {selectedFile?.content && (
        <div className="mt-3 p-2 bg-white rounded border border-[#E8E4DC] text-xs max-h-48 overflow-y-auto">
          <pre className="whitespace-pre-wrap">{selectedFile.content}</pre>
        </div>
      )}
    </div>
  );
}
