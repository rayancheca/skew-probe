import { useRef, useState, type DragEvent, type ChangeEvent } from 'react';
import './FileUpload.css';

interface FileUploadProps {
  onSubmit: (file: File, columns: string, numWorkers: number) => void;
  isLoading: boolean;
  schemaColumns?: string[];
}

export function FileUpload({ onSubmit, isLoading, schemaColumns }: FileUploadProps) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [columns, setColumns] = useState('');
  const [numWorkers, setNumWorkers] = useState(8);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) setFile(selected);
  };

  const handleSubmit = () => {
    if (!file || !columns.trim()) return;
    onSubmit(file, columns.trim(), numWorkers);
  };

  const addColumn = (col: string) => {
    const current = columns.split(',').map(c => c.trim()).filter(Boolean);
    if (!current.includes(col)) {
      setColumns(current.concat(col).join(', '));
    }
  };

  return (
    <div className="upload-root">
      <div
        className={`drop-zone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && inputRef.current?.click()}
        aria-label="Upload Parquet or CSV file"
      >
        <input
          ref={inputRef}
          type="file"
          accept=".parquet,.csv"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        <div className="drop-icon">
          {file ? (
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          ) : (
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          )}
        </div>
        <p className="drop-primary">
          {file ? file.name : 'Drop Parquet or CSV file'}
        </p>
        <p className="drop-secondary">
          {file
            ? `${(file.size / 1024 / 1024).toFixed(1)} MB · Click to change`
            : 'or click to browse · .parquet, .csv'}
        </p>
      </div>

      <div className="config-panel">
        <div className="field">
          <label className="field-label" htmlFor="columns-input">
            Partition Columns
            <span className="field-hint">comma-separated</span>
          </label>
          <input
            id="columns-input"
            className="text-input"
            type="text"
            placeholder="user_id, product_id, region"
            value={columns}
            onChange={e => setColumns(e.target.value)}
          />
          {schemaColumns && schemaColumns.length > 0 && (
            <div className="column-pills">
              {schemaColumns.map(col => (
                <button
                  key={col}
                  className="column-pill"
                  onClick={() => addColumn(col)}
                  type="button"
                >
                  {col}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="field">
          <label className="field-label" htmlFor="workers-input">
            Simulated Workers
            <span className="field-hint mono">{numWorkers}</span>
          </label>
          <input
            id="workers-input"
            className="range-input"
            type="range"
            min={1}
            max={64}
            value={numWorkers}
            onChange={e => setNumWorkers(Number(e.target.value))}
          />
          <div className="range-labels">
            <span>1</span>
            <span>16</span>
            <span>32</span>
            <span>64</span>
          </div>
        </div>

        <button
          className="analyze-btn"
          onClick={handleSubmit}
          disabled={!file || !columns.trim() || isLoading}
          type="button"
        >
          {isLoading ? (
            <>
              <span className="spinner" aria-hidden="true" />
              Analyzing…
            </>
          ) : (
            <>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
              </svg>
              Profile Partitions
            </>
          )}
        </button>
      </div>
    </div>
  );
}
