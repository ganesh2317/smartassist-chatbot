import {useRef,useState} from "react";

const allowed=".pdf,.docx,.txt,.md,.csv,.json";
const formatBytes=(bytes)=>bytes<1024?`${bytes} B`:bytes<1024*1024?`${(bytes/1024).toFixed(1)} KB`:`${(bytes/1024/1024).toFixed(1)} MB`;

export default function KnowledgePanel({open,documents,onUpload,onDelete,uploading,error,onClose}){
  const inputRef=useRef(null);
  const [dragging,setDragging]=useState(false);
  const choose=()=>inputRef.current?.click();
  const submitFiles=files=>{const list=Array.from(files||[]); if(list.length) onUpload(list);};
  return <aside className={`knowledge-panel ${open?"open":""}`} aria-hidden={!open}>
    <div className="knowledge-header">
      <div><h2>Knowledge</h2><p>Private files used for relevant answers.</p></div>
      <button type="button" className="icon-button" onClick={onClose} aria-label="Close knowledge panel">×</button>
    </div>
    <div
      className={`drop-zone ${dragging?"dragging":""}`}
      onDragEnter={e=>{e.preventDefault();setDragging(true)}}
      onDragOver={e=>e.preventDefault()}
      onDragLeave={e=>{e.preventDefault();setDragging(false)}}
      onDrop={e=>{e.preventDefault();setDragging(false);submitFiles(e.dataTransfer.files)}}
      onClick={choose}
      role="button"
      tabIndex={0}
      onKeyDown={e=>{if(e.key==="Enter"||e.key===" ")choose()}}
    >
      <div className="drop-icon">＋</div>
      <strong>{uploading?"Uploading…":"Drop files here"}</strong>
      <span>or click to browse</span>
      <small>PDF, DOCX, TXT, MD, CSV, JSON · up to 10 MB</small>
      <input ref={inputRef} hidden type="file" accept={allowed} multiple onChange={e=>{submitFiles(e.target.files);e.target.value=""}} disabled={uploading}/>
    </div>
    {error&&<p className="panel-error" role="alert">{error}</p>}
    <div className="knowledge-list">
      <div className="knowledge-list-title"><strong>{documents.length} file{documents.length===1?"":"s"}</strong><span>Auto-retrieved during chat</span></div>
      {documents.length===0&&<div className="knowledge-empty"><strong>No knowledge files yet</strong><p>Upload notes, reports, PDFs, or docs. SmartAssist will search them when a question is relevant.</p></div>}
      {documents.map(doc=><div className="document-item" key={doc.id}>
        <div className="doc-icon">{doc.name.split(".").pop()?.slice(0,4).toUpperCase()}</div>
        <div className="doc-meta"><strong title={doc.name}>{doc.name}</strong><span>{formatBytes(doc.size_bytes)} · {doc.chunk_count} chunks</span></div>
        <button type="button" className="delete doc-delete" onClick={()=>onDelete(doc.id,doc.name)} aria-label={`Delete ${doc.name}`}>Delete</button>
      </div>)}
    </div>
    <div className="knowledge-note"><strong>Safety:</strong> uploaded text is treated as untrusted reference data, not as executable instructions.</div>
  </aside>;
}
