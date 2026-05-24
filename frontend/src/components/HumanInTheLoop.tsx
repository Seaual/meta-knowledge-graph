import { AlertTriangle } from "lucide-react";
import { useAgentStore } from "../stores/agentStore";
import { agentApi } from "../lib/api/agent";

export default function HumanInTheLoop() {
  const pending = useAgentStore((s) => s.pendingApproval);
  const setPending = useAgentStore((s) => s.setPendingApproval);

  if (!pending) return null;

  const handleApprove = async (approved: boolean) => {
    await agentApi.approveAction(pending.id, approved);
    setPending(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4 shadow-xl">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="w-6 h-6 text-amber-600" />
          <h3 className="font-display text-lg text-[#2c1810]">Agent 请求确认</h3>
        </div>
        <p className="text-sm text-[#6b5d4f] mb-2">Agent 即将执行以下操作：</p>
        <div className="bg-[#F5F0E8] rounded-lg p-3 mb-4">
          <p className="font-medium text-[#2c1810]">{pending.action}</p>
          <p className="text-xs text-[#6b5d4f] mt-1">{pending.message}</p>
        </div>
        <div className="flex justify-end gap-3">
          <button
            onClick={() => handleApprove(false)}
            className="px-4 py-2 rounded-lg text-sm border border-[#E8E4DC] hover:bg-[#F5F0E8]"
          >
            取消
          </button>
          <button
            onClick={() => handleApprove(true)}
            className="px-4 py-2 rounded-lg text-sm bg-[#8b4513] text-white hover:bg-[#6b3410]"
          >
            确认执行
          </button>
        </div>
      </div>
    </div>
  );
}
