import { useRef, useState } from 'react';
import { formatBytes } from '../utils/format';

/**
 * Drag-and-drop (or click) file picker. Validation is done by the parent
 * so the same rules apply to dropped and selected files.
 */
export default function FileDropzone({ allowedTypes, maxMb, file, onFile, disabled }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const pick = (files) => {
    if (!disabled && files && files[0]) onFile(files[0]);
  };

  return (
    <div
      className={`dropzone${dragging ? ' is-dragging' : ''}${disabled ? ' is-disabled' : ''}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        pick(e.dataTransfer.files);
      }}
    >
      <input
        ref={inputRef}
        id="submission-file"
        type="file"
        className="visually-hidden"
        accept={allowedTypes.map((t) => `.${t}`).join(',')}
        disabled={disabled}
        onChange={(e) => pick(e.target.files)}
      />
      {file ? (
        <div className="dropzone__file">
          <span className="dropzone__name">{file.name}</span>
          <span className="dropzone__size">{formatBytes(file.size)}</span>
        </div>
      ) : (
        <p className="dropzone__hint">Drop your file here</p>
      )}
      <label htmlFor="submission-file" className="btn btn--ghost btn--sm">
        {file ? 'Choose a different file' : 'Choose file'}
      </label>
      <p className="dropzone__rules">
        Accepted: {allowedTypes.map((t) => `.${t}`).join(' ')} · up to {maxMb} MB
      </p>
    </div>
  );
}
