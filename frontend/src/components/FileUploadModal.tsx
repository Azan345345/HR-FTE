import { useState } from "react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { UploadCloud, FileText, Trash2, X } from "lucide-react";

interface FileUploadModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function FileUploadModal({ open, onOpenChange }: FileUploadModalProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState([
    { name: "John_Doe_Resume_2024.pdf", size: "2.4 MB", status: "Indexed" }
  ]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    // Mock upload
    const newFile = { name: "Cover_Letter.pdf", size: "1.1 MB", status: "Indexed" };
    setFiles([...files, newFile]);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[480px] p-0 overflow-hidden border-none rounded-xl shadow-2xl">
        <div className="p-6 bg-white">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-slate-900 font-sans">Upload Documents</h3>
            <button onClick={() => onOpenChange(false)} className="text-slate-400 hover:text-slate-600 transition-colors">
              <X size={20} />
            </button>
          </div>

          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`h-[200px] border-2 border-dashed rounded-xl flex flex-col items-center justify-center transition-all ${
              isDragging
                ? "border-rose-400 bg-rose-50/30"
                : "border-slate-300 bg-slate-50/50"
            }`}
          >
            <UploadCloud size={40} className={isDragging ? "text-rose-500" : "text-slate-400"} />
            <p className="mt-3 text-sm font-medium text-slate-600 font-sans">
              Drag & drop your files here
            </p>
            <p className="mt-1 text-xs text-slate-400 font-sans">or</p>
            <button className="mt-3 px-4 py-2 bg-white border border-rose-200 text-rose-600 rounded-lg text-xs font-semibold font-sans hover:bg-rose-50 transition-colors shadow-sm">
              Browse Files
            </button>
            <p className="mt-2 text-[10px] text-slate-400 font-sans">Accepted: .pdf, .docx, .txt</p>
          </div>

          <div className="mt-6 space-y-3">
            {files.map((file, i) => (
              <div key={i} className="flex items-center gap-3 p-3 bg-slate-50 border border-slate-100 rounded-lg">
                <div className="w-8 h-8 rounded-full bg-rose-100 flex items-center justify-center flex-shrink-0">
                  <FileText size={14} className="text-rose-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 font-sans truncate">{file.name}</p>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-400 font-sans">{file.size}</span>
                    <span className="w-1 h-1 rounded-full bg-slate-300" />
                    <span className="text-[10px] text-green-600 font-medium font-sans flex items-center gap-1">
                      ✓ {file.status}
                    </span>
                  </div>
                </div>
                <button className="text-slate-400 hover:text-red-500 transition-colors">
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>

          <button 
            onClick={() => onOpenChange(false)}
            className="w-full mt-6 h-11 bg-primary text-white rounded-lg text-sm font-semibold font-sans hover:bg-rose-700 transition-colors shadow-md"
          >
            Done
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
