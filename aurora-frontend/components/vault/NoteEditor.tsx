'use client';
import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface NoteEditorProps {
  initialContent: string;
  initialFrontmatter: Record<string, unknown>;
  onSave: (content: string) => Promise<void>;
  onCancel: () => void;
}

export default function NoteEditor({ initialContent, onSave, onCancel }: NoteEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    setIsDirty(content !== initialContent);
  }, [content, initialContent]);

  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty]);

  const handleSave = async () => {
    setStatus('saving');
    try {
      await onSave(content);
      setStatus('saved');
      setIsDirty(false);
      setTimeout(() => setStatus('idle'), 2000);
    } catch (e) {
      console.error(e);
      setStatus('error');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      handleSave();
    }
  };

  return (
    <div className="note-editor">
      <div className="editor-header">
        <div className="editor-status">
          {status === 'saving' && 'Saving...'}
          {status === 'saved' && 'Saved!'}
          {status === 'error' && <span style={{color: 'red'}}>Error saving</span>}
          {status === 'idle' && isDirty && 'Unsaved changes'}
        </div>
        <div className="editor-actions">
          <button onClick={onCancel} className="btn-secondary">Cancel</button>
          <button onClick={handleSave} className="btn-primary" disabled={!isDirty || status === 'saving'}>Save</button>
        </div>
      </div>
      <div className="editor-split">
        <textarea
          className="editor-textarea"
          value={content}
          onChange={e => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          spellCheck="false"
        />
        <div className="editor-preview">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {content}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
