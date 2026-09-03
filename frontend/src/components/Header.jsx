export default function Header({username,onLogout,onToggleHistory,historyOpen,onToggleKnowledge,knowledgeOpen,documentCount,status,aiConfigured}){
  return <header className="chat-header">
    <div className="header-left">
      <button type="button" className="menu-button" onClick={onToggleHistory} aria-expanded={historyOpen}>Chats</button>
      <img className="logo" src="/smartassist-logo.png" alt="SmartAssist"/>
      <div className="brand-copy">
        <h1>SmartAssist</h1>
        <p>AI + private knowledge <span className={`status ${status}`}>● {status==="online"?"Online":status==="offline"?"Offline":"Checking"}</span>{status==="online"&&aiConfigured===false&&<span className="ai-warning">AI key missing</span>}</p>
      </div>
    </div>
    <div className="header-actions">
      <button type="button" className={`secondary knowledge-toggle ${knowledgeOpen?"active":""}`} onClick={onToggleKnowledge} aria-expanded={knowledgeOpen}>
        Knowledge <span className="count-pill">{documentCount}</span>
      </button>
      <span className="header-user">{username}</span>
      <button type="button" className="secondary" onClick={onLogout}>Logout</button>
    </div>
  </header>;
}
