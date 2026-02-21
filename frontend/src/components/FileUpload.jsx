import { useState, useRef } from 'react';
import './FileUpload.css';

export default function FileUpload({
  conversationId,
  files,
  onFilesChange,
  disabled,
  api,
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled || !conversationId) return;
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      await uploadFiles(droppedFiles);
    }
  };

  const handleFileSelect = async (e) => {
    const selected = Array.from(e.target.files);
    if (selected.length > 0) {
      await uploadFiles(selected);
    }
    // Reset input so same file can be re-selected
    e.target.value = '';
  };

  const uploadFiles = async (fileList) => {
    if (!conversationId) return;
    setIsUploading(true);
    try {
      const uploaded = await api.uploadFiles(conversationId, fileList);
      onFilesChange([...files, ...uploaded]);
    } catch (error) {
      console.error('Failed to upload files:', error);
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemove = async (fileId) => {
    if (!conversationId) return;
    try {
      await api.deleteFile(conversationId, fileId);
      onFilesChange(files.filter((f) => f.id !== fileId));
    } catch (error) {
      console.error('Failed to delete file:', error);
    }
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="file-upload">
      <label className="file-upload-label">Attached Files</label>

      <div
        className={`drop-zone ${isDragging ? 'dragging' : ''} ${disabled ? 'disabled' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
      >
        {isUploading ? (
          <span className="drop-zone-text">Uploading...</span>
        ) : (
          <span className="drop-zone-text">
            Drop files here or click to browse
          </span>
        )}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileSelect}
          style={{ display: 'none' }}
          disabled={disabled}
        />
      </div>

      {files.length > 0 && (
        <ul className="file-list">
          {files.map((f) => (
            <li key={f.id} className="file-item">
              <span className="file-icon">{f.is_image ? '🖼' : '📄'}</span>
              <span className="file-name">{f.filename}</span>
              <span className="file-size">{formatSize(f.size_bytes)}</span>
              <button
                className="file-remove"
                onClick={() => handleRemove(f.id)}
                disabled={disabled}
                title="Remove file"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
