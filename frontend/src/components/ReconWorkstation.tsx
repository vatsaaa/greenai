import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchReviewQueue, resolveException, ReviewItem } from '../api';
import { CheckCircle, AlertTriangle, ArrowRight, XCircle, Save } from 'lucide-react';
import { clsx } from 'clsx';

const ReconWorkstation: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // 1. Fetch Queue Data
  const { data: queue, isLoading } = useQuery({
    queryKey: ['reviewQueue'],
    queryFn: fetchReviewQueue,
  });

  // 2. Mutation for Actions (Approve/Override)
  const mutation = useMutation({
    mutationFn: resolveException,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviewQueue'] });
      setSelectedId(null); // Deselect on success
    },
  });

  if (isLoading) return <div className="p-10 text-gray-500">Loading Workstation...</div>;

  return (
    <div className="flex h-screen bg-gray-50 font-sans">
      {/* --- LEFT SIDEBAR: THE QUEUE --- */}
      <div className="w-1/3 border-r bg-white overflow-y-auto">
        <div className="p-4 border-b bg-gray-100 sticky top-0">
          <h2 className="font-bold text-gray-700">Review Queue ({queue?.length})</h2>
          <p className="text-xs text-gray-500">Items requiring human attention</p>
        </div>
        <div>
          {queue?.map((item) => (
            <div
              key={item.attribution_id}
              onClick={() => setSelectedId(item.attribution_id)}
              className={clsx(
                "p-4 border-b cursor-pointer hover:bg-blue-50 transition-colors",
                selectedId === item.attribution_id ? "bg-blue-100 border-l-4 border-l-blue-600" : ""
              )}
            >
              <div className="flex justify-between items-center mb-1">
                <span className="text-xs font-mono text-gray-500">{item.difference.field_name}</span>
                <Badge score={item.confidence_score} />
              </div>
              <div className="text-sm font-medium text-gray-800 truncate">
                 {item.difference.diff_type}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                ID: {item.source_a_ref_id.slice(0, 8)}...
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* --- RIGHT PANEL: ACTION AREA --- */}
      <div className="w-2/3 p-8 overflow-y-auto">
        {selectedId ? (
          <DetailView 
            item={queue?.find(i => i.attribution_id === selectedId)!} 
            onAction={mutation.mutate} 
            isProcessing={mutation.isPending}
          />
        ) : (
          <div className="flex h-full items-center justify-center text-gray-400">
            Select an item from the queue to begin review.
          </div>
        )}
      </div>
    </div>
  );
};

// --- Sub-Components ---

const Badge = ({ score }: { score: number }) => {
  const color = score > 0.8 ? 'text-green-600 bg-green-100' : 'text-amber-600 bg-amber-100';
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold ${color}`}>
      {(score * 100).toFixed(0)}% Conf
    </span>
  );
};

const DetailView = ({ 
  item, 
  onAction, 
  isProcessing 
}: { 
  item: ReviewItem; 
  onAction: any; 
  isProcessing: boolean 
}) => {
  const [overrideReason, setOverrideReason] = useState("");
  const [mode, setMode] = useState<'VIEW' | 'OVERRIDE'>('VIEW');

  const handleApprove = () => {
    onAction({
      attribution_id: item.attribution_id,
      action: 'APPROVE',
      actor_id: 'USER_DEMO_01' // In prod, this comes from Auth Context
    });
  };

  const handleOverride = () => {
    onAction({
      attribution_id: item.attribution_id,
      action: 'OVERRIDE',
      actor_id: 'USER_DEMO_01',
      new_reason_code: overrideReason,
      comments: "Manual override via UI"
    });
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">Difference Analysis</h1>
        <div className="flex items-center space-x-2 text-sm text-gray-500">
           <span>Ref A: {item.source_a_ref_id}</span>
           <span>•</span>
           <span>Ref B: {item.source_b_ref_id}</span>
        </div>
      </div>

      {/* Comparison Cards */}
      <div className="grid grid-cols-2 gap-4 mb-8">
        <div className="p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
          <div className="text-xs uppercase tracking-wide text-gray-400 mb-2">Source A (Master)</div>
          <div className="text-lg font-mono text-gray-800 break-all">
            {item.difference.value_a ?? <span className="text-gray-300 italic">NULL</span>}
          </div>
        </div>
        <div className="p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
          <div className="text-xs uppercase tracking-wide text-gray-400 mb-2">Source B (Target)</div>
          <div className="text-lg font-mono text-gray-800 break-all">
            {item.difference.value_b ?? <span className="text-gray-300 italic">NULL</span>}
          </div>
        </div>
      </div>

      {/* AI Prediction Box */}
      <div className="bg-slate-800 text-white p-6 rounded-lg mb-8 shadow-md">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="text-yellow-400 w-5 h-5" />
            <span className="font-semibold uppercase tracking-wider text-sm">AI Diagnosis</span>
          </div>
          <div className="text-slate-400 text-xs">Model V1.2</div>
        </div>
        
        <div className="mb-4">
          <div className="text-2xl font-light">
            {item.current_reason?.description || "Unknown Reason"}
          </div>
          <div className="text-slate-400 mt-1">Code: {item.current_reason?.code || "UNKNOWN"}</div>
        </div>

        <div className="w-full bg-slate-700 h-2 rounded-full overflow-hidden">
          <div 
            className="bg-blue-500 h-full transition-all duration-500" 
            style={{ width: `${item.confidence_score * 100}%` }} 
          />
        </div>
        <div className="text-right text-xs text-blue-300 mt-1">
          {(item.confidence_score * 100).toFixed(1)}% Confidence Score
        </div>
      </div>

      {/* Action Bar */}
      {mode === 'VIEW' ? (
        <div className="flex space-x-4">
          <button 
            onClick={handleApprove}
            disabled={isProcessing}
            className="flex-1 bg-green-600 hover:bg-green-700 text-white py-3 px-6 rounded-lg font-medium flex items-center justify-center space-x-2 shadow-lg transition-transform active:scale-95"
          >
            <CheckCircle className="w-5 h-5" />
            <span>Accept Diagnosis</span>
          </button>
          
          <button 
            onClick={() => setMode('OVERRIDE')}
            className="flex-1 bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 py-3 px-6 rounded-lg font-medium flex items-center justify-center space-x-2 transition-colors"
          >
            <XCircle className="w-5 h-5" />
            <span>Reject / Override</span>
          </button>
        </div>
      ) : (
        <div className="bg-white border border-amber-200 rounded-lg p-6 shadow-sm">
          <h3 className="font-bold text-gray-800 mb-4">Manual Override</h3>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Select New Reason Code</label>
            <select 
              className="w-full border-gray-300 rounded-md shadow-sm p-2 border"
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
            >
              <option value="">-- Select Reason --</option>
              <option value="MANUAL_ENTRY_ERR">Manual Entry Error</option>
              <option value="TIMING_LAG">Timing Lag</option>
              <option value="SYSTEM_CONVERSION">System Conversion</option>
            </select>
          </div>
          <div className="flex space-x-3">
            <button 
              onClick={handleOverride}
              disabled={!overrideReason || isProcessing}
              className="bg-amber-600 text-white px-4 py-2 rounded hover:bg-amber-700 disabled:opacity-50 flex items-center space-x-2"
            >
              <Save className="w-4 h-4" />
              <span>Confirm Override</span>
            </button>
            <button 
              onClick={() => setMode('VIEW')}
              className="text-gray-500 px-4 py-2 hover:text-gray-700"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReconWorkstation;